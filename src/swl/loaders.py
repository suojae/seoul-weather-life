"""랜딩 존의 원본을 웨어하우스 raw 스키마에 적재한다.

raw 테이블은 소스마다 하나이고, 레코드 한 건을 JSONB 한 행으로 그대로 담는다.
타입 변환·컬럼 이름 정리는 dbt staging에서 한다 (ELT).

적재는 dt 파티션 단위로 "지우고 다시 넣기"를 한 트랜잭션 안에서 한다.
같은 날짜를 몇 번 다시 적재해도 결과가 같다 (멱등).

DB-API 2.0 연결이면 무엇이든 받는다 (psycopg2, psycopg 3).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from datetime import date

from swl.sources import Source

INSERT_BATCH = 1000


def lock_table(cur, table: str) -> None:
    """같은 raw 테이블에 대한 적재를 트랜잭션 단위로 직렬화한다.

    backfill은 여러 날짜를 동시에 적재한다. 동시에 CREATE TABLE IF NOT EXISTS를 실행하면
    Postgres가 pg_type 중복 키 오류를 낸다. 커밋·롤백 시 자동으로 풀린다.
    """
    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (table,))


def ensure_raw_table(cur, table: str) -> None:
    index = table.split(".", 1)[1] + "_dt_idx"
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            dt          date        NOT NULL,
            record      jsonb       NOT NULL,
            landing_key text        NOT NULL,
            loaded_at   timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    cur.execute(f"CREATE INDEX IF NOT EXISTS {index} ON {table} (dt)")


def load_partition(
    conn,
    source: Source,
    target: date,
    objects: Iterable[tuple[str, bytes]],
    parse_rows: Callable[[bytes], list[dict]],
) -> int:
    """objects(랜딩 키, 원본 바이트)를 파싱해 raw 테이블의 target 파티션을 교체한다. 적재 행 수를 돌려준다."""
    table = source.raw_table  # Source에서 raw.<name> 형식을 검증했다
    loaded = 0
    try:
        with conn.cursor() as cur:
            lock_table(cur, table)
            ensure_raw_table(cur, table)
            cur.execute(f"DELETE FROM {table} WHERE dt = %s", (target,))
            batch: list[tuple] = []
            for key, body in objects:
                for row in parse_rows(body):
                    batch.append((target, json.dumps(row, ensure_ascii=False), key))
                    if len(batch) >= INSERT_BATCH:
                        loaded += _insert(cur, table, batch)
                        batch = []
            loaded += _insert(cur, table, batch)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return loaded


def _insert(cur, table: str, batch: list[tuple]) -> int:
    if batch:
        cur.executemany(
            f"INSERT INTO {table} (dt, record, landing_key) VALUES (%s, %s::jsonb, %s)", batch
        )
    return len(batch)
