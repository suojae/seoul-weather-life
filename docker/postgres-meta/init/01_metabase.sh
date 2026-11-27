#!/bin/bash
# Metabase 앱 DB (대시보드·질문 정의 저장). Airflow 메타 DB와 같은 서버, 다른 데이터베이스.
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE metabase LOGIN PASSWORD '${METABASE_DB_PASSWORD}';
CREATE DATABASE metabase OWNER metabase;
SQL
