#!/bin/bash
# 웨어하우스 최초 기동 시 1회 실행: 확장, 레이어 스키마, BI 읽기 전용 계정
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS raw;      -- API 응답을 거의 그대로
CREATE SCHEMA IF NOT EXISTS staging;  -- 타입·단위·시간대 정리 (view)
CREATE SCHEMA IF NOT EXISTS core;     -- 공통 차원 + 주제별 팩트
CREATE SCHEMA IF NOT EXISTS marts;    -- 분석·대시보드용

CREATE ROLE bi_reader LOGIN PASSWORD '${BI_READER_PASSWORD}';
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO bi_reader;
GRANT USAGE ON SCHEMA core, marts TO bi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA core, marts TO bi_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA core, marts
  GRANT SELECT ON TABLES TO bi_reader;
SQL
