"""변환 DAG: raw 테이블이 모두 갱신되면 dbt로 staging → core → marts를 만든다.

    source_freshness  raw가 너무 오래되지 않았는지 검사 (dbt source freshness)
    dbt               Cosmos가 dbt 모델·테스트를 각각 Airflow 태스크로 펼친다

시간 스케줄이 없다. sources.yml의 모든 raw Asset이 마지막 실행 이후 갱신되면 실행된다.
dbt는 Airflow와 분리된 가상환경(DBT_EXECUTABLE)에서 돌고, 태스크는 Celery `dbt` 큐로 간다.
"""

from __future__ import annotations

import os

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import Asset, dag
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig

from swl.sources import load_sources

DBT_DIR = "/opt/airflow/dbt"
DBT = os.environ.get("DBT_EXECUTABLE", "dbt")
SOURCES = load_sources(os.environ.get("SWL_SOURCES", "/opt/airflow/sources.yml"))

profile_config = ProfileConfig(
    profile_name="seoul_weather_life",
    target_name="prod",
    profiles_yml_filepath=f"{DBT_DIR}/profiles.yml",
)


@dag(
    dag_id="transform",
    description="raw 갱신 시 dbt build (staging → core → marts)",
    schedule=[Asset(name=s.raw_table, uri=s.raw_asset_uri) for s in SOURCES.values()],
    start_date=pendulum.datetime(2026, 11, 1, tz="Asia/Seoul"),
    catchup=False,
    max_active_runs=1,
    tags=["dbt"],
    default_args={"queue": "dbt", "retries": 1},
)
def transform():
    freshness = BashOperator(
        task_id="source_freshness",
        bash_command=f"{DBT} source freshness --project-dir {DBT_DIR} --profiles-dir {DBT_DIR} --target prod",
    )

    dbt = DbtTaskGroup(
        group_id="dbt",
        project_config=ProjectConfig(DBT_DIR),
        profile_config=profile_config,
        execution_config=ExecutionConfig(dbt_executable_path=DBT),
        operator_args={"queue": "dbt", "install_deps": False},
    )

    freshness >> dbt


transform()
