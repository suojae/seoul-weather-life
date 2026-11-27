from datetime import date

import pytest

from swl import landing, loaders, pipeline
from swl.clients.seoul_openapi import Page
from swl.errors import DataNotReady
from swl.sources import Source

SOURCE = Source(
    name="demo",
    description="",
    client="seoul_openapi",
    service="SVC",
    lag_days=1,
    schedule="0 7 * * *",
    raw_table="raw.demo",
    path_params=("{date:%Y%m%d}",),
)
DAY = date(2026, 11, 20)


class FakeS3:
    """boto3 S3 클라이언트에서 쓰는 메서드만 흉내 낸다."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body, **_):
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        body = self.objects[Key]
        return {"Body": type("B", (), {"read": lambda self: body})()}

    def delete_objects(self, Bucket, Delete):
        for obj in Delete["Objects"]:
            self.objects.pop(obj["Key"], None)

    def get_paginator(self, _):
        s3 = self

        class P:
            def paginate(self, Bucket, Prefix):
                keys = [k for k in s3.objects if k.startswith(Prefix)]
                yield {"Contents": [{"Key": k} for k in keys]} if keys else {}

        return P()


class FakeClient:
    def __init__(self, n_pages, rows_per_page=2, fail=None):
        self.n_pages, self.rows_per_page, self.fail = n_pages, rows_per_page, fail

    def fetch_source(self, source, target):
        assert source.render_path_params(target) == ["20261120"]
        if self.fail:
            raise self.fail
        for n in range(1, self.n_pages + 1):
            rows = [{"page": n, "i": i} for i in range(self.rows_per_page)]
            yield Page(number=n, body=_body(rows), rows=rows, total=self.n_pages * self.rows_per_page)


def _body(rows):
    import json

    return json.dumps({"root": {"row": rows}}).encode()


class FakeConn:
    """DELETE → INSERT 순서와 커밋 여부를 기록하는 DB-API 연결."""

    def __init__(self, fail_on_insert=False):
        self.statements, self.inserted, self.committed, self.rolled_back = [], [], False, False
        self.fail_on_insert = fail_on_insert

    def cursor(self):
        conn = self

        class Cur:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params=None):
                conn.statements.append(" ".join(sql.split())[:30])

            def executemany(self, sql, rows):
                if conn.fail_on_insert:
                    raise RuntimeError("boom")
                conn.statements.append("INSERT")
                conn.inserted.extend(rows)

        return Cur()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_extract_writes_pages_under_dt_partition():
    s3 = FakeS3()
    keys = pipeline.extract(SOURCE, DAY, s3, client=FakeClient(n_pages=2))
    assert keys == ["demo/dt=2026-11-20/page-00001.json", "demo/dt=2026-11-20/page-00002.json"]


def test_rerun_replaces_partition_without_leftovers():
    s3 = FakeS3()
    pipeline.extract(SOURCE, DAY, s3, client=FakeClient(n_pages=3))
    pipeline.extract(SOURCE, DAY, s3, client=FakeClient(n_pages=1))
    assert landing.list_keys(s3, "demo/") == ["demo/dt=2026-11-20/page-00001.json"]


def test_not_ready_keeps_previous_landing_data():
    s3 = FakeS3()
    pipeline.extract(SOURCE, DAY, s3, client=FakeClient(n_pages=2))
    with pytest.raises(DataNotReady):
        pipeline.extract(SOURCE, DAY, s3, client=FakeClient(n_pages=0, fail=DataNotReady("not yet")))
    assert len(landing.list_keys(s3, "demo/")) == 2


def test_load_deletes_partition_then_inserts_in_one_transaction():
    s3 = FakeS3()
    pipeline.extract(SOURCE, DAY, s3, client=FakeClient(n_pages=2, rows_per_page=3))
    conn = FakeConn()
    rows = pipeline.load(SOURCE, DAY, s3, conn)

    assert rows == 6
    assert conn.statements[0].startswith("SELECT pg_advisory_xact_lock")  # 동시 적재 직렬화
    writes = [s for s in conn.statements if s.startswith(("DELETE", "INSERT"))]
    assert writes[0].startswith("DELETE FROM raw.demo WHERE dt") and writes[1:] == ["INSERT"]
    assert conn.committed and not conn.rolled_back
    assert {r[0] for r in conn.inserted} == {DAY}
    assert conn.inserted[0][2] == "demo/dt=2026-11-20/page-00001.json"


def test_load_rolls_back_on_failure():
    s3 = FakeS3()
    pipeline.extract(SOURCE, DAY, s3, client=FakeClient(n_pages=1))
    conn = FakeConn(fail_on_insert=True)
    with pytest.raises(RuntimeError):
        pipeline.load(SOURCE, DAY, s3, conn)
    assert conn.rolled_back and not conn.committed


def test_insert_is_batched():
    batches = []

    class Cur:
        def executemany(self, sql, rows):
            batches.append(len(rows))

    rows = [(DAY, "{}", "k")] * (loaders.INSERT_BATCH + 1)
    for i in range(0, len(rows), loaders.INSERT_BATCH):
        loaders._insert(Cur(), "raw.demo", rows[i : i + loaders.INSERT_BATCH])
    assert batches == [loaders.INSERT_BATCH, 1]
