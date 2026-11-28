"""DAG 팩토리: sources.yml의 소스마다 `ingest__<이름>` DAG을 만든다.

    extract  소스 API → 랜딩 존 (SeaweedFS)  dt 파티션 교체
    load     랜딩 존 → 웨어하우스 raw 테이블  dt 파티션 교체, raw Asset 갱신

수집 대상 날짜 = 실행 기준 시각(KST 날짜) − lag_days.
지난 기간은 `airflow backfill create`로 채운다. 두 단계 모두 멱등이라 다시 돌려도 중복되지 않는다.
로직은 src/swl 패키지에 있고, 여기서는 연결만 넘긴다.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pendulum
from airflow.sdk import Asset, dag, task, get_current_context

from swl import pipeline
from swl.errors import DataNotReady
from swl.sources import Source, load_sources

KST = pendulum.timezone("Asia/Seoul")
SOURCES = load_sources(os.environ.get("SWL_SOURCES", "/opt/airflow/sources.yml"))


def _run_date() -> date:
    ctx = get_current_context()
    # 수동 실행은 logical_date가 없을 수 있다 (Airflow 3). 그때는 실행 요청 시각을 쓴다.
    when = ctx.get("logical_date") or ctx["dag_run"].run_after
    return pendulum.instance(when).in_timezone(KST).date()


def _raw_asset(source: Source) -> Asset:
    return Asset(name=source.raw_table, uri=source.raw_asset_uri)


def build_dag(source: Source):
    @dag(
        dag_id=f"ingest__{source.name}",
        description=source.description,
        schedule=source.schedule,
        start_date=pendulum.datetime(2026, 11, 1, tz=KST),
        catchup=False,
        max_active_runs=3,
        tags=["ingest", source.client],
        default_args={"retries": 3, "retry_delay": timedelta(hours=1)},
    )
    def ingest():
        @task
        def extract() -> str:
            from airflow.providers.amazon.aws.hooks.s3 import S3Hook

            target = source.target_date(_run_date())
            s3 = S3Hook(aws_conn_id="landing").get_conn()
            try:
                keys = pipeline.extract(source, target, s3)
            except DataNotReady as exc:
                # 아직 공개 전: 실패로 끝내 retry_delay 뒤에 다시 시도하게 한다
                raise RuntimeError(f"{target} not published yet ({exc}); will retry") from exc
            print(f"{source.name} {target}: {len(keys)} page(s) → s3://landing/{source.name}/dt={target}/")
            return target.isoformat()

        @task(outlets=[_raw_asset(source)])
        def load(target_iso: str) -> int:
            from airflow.providers.amazon.aws.hooks.s3 import S3Hook
            from airflow.providers.postgres.hooks.postgres import PostgresHook

            target = date.fromisoformat(target_iso)
            s3 = S3Hook(aws_conn_id="landing").get_conn()
            conn = PostgresHook(postgres_conn_id="warehouse").get_conn()
            try:
                rows = pipeline.load(source, target, s3, conn)
            finally:
                conn.close()
            print(f"{source.name} {target}: {rows} row(s) → {source.raw_table}")
            return rows

        load(extract())

    return ingest()


for _source in SOURCES.values():
    globals()[f"ingest__{_source.name}"] = build_dag(_source)
