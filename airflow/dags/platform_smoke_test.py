"""플랫폼 연결 점검 DAG.

scheduler → Redis → Celery worker 경로로 태스크가 실행되는지, worker가 랜딩 존(SeaweedFS)과
웨어하우스(Postgres + PostGIS)에 닿는지 확인한다. 수동으로만 실행한다.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from airflow.sdk import dag, task


@dag(schedule=None, catchup=False, tags=["platform"])
def platform_smoke_test():
    @task
    def write_to_landing() -> str:
        from airflow.providers.amazon.aws.hooks.s3 import S3Hook

        hook = S3Hook(aws_conn_id="landing")
        key = "_smoke/hello.json"
        body = json.dumps({"checked_at": datetime.now(timezone.utc).isoformat()})
        hook.load_string(body, key=key, bucket_name="landing", replace=True)
        assert hook.check_for_key(key, bucket_name="landing")
        return key

    @task
    def query_warehouse() -> dict:
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook(postgres_conn_id="warehouse")
        postgis = hook.get_first("SELECT postgis_lib_version()")[0]
        schemas = [
            r[0]
            for r in hook.get_records(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name IN ('raw', 'staging', 'core', 'marts') ORDER BY 1"
            )
        ]
        assert schemas == ["core", "marts", "raw", "staging"], schemas
        return {"postgis": postgis, "schemas": schemas}

    @task
    def report(key: str, warehouse: dict) -> None:
        print(f"landing: s3://landing/{key} OK")
        print(f"warehouse: PostGIS {warehouse['postgis']}, schemas {warehouse['schemas']} OK")

    report(write_to_landing(), query_warehouse())


platform_smoke_test()
