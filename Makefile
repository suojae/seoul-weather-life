.PHONY: init up down ps logs smoke test backfill dbt-dev dbt clean

init:            ## .env 생성 (비밀값 자동 생성)
	python3 scripts/init_env.py

up:              ## 전체 스택 빌드 후 기동
	docker compose up -d --build

down:            ## 컨테이너 중지 (데이터 볼륨은 유지)
	docker compose down

ps:              ## 컨테이너 상태
	docker compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'

logs:            ## 로그 따라가기 (예: make logs s=airflow-worker)
	docker compose logs -f $(s)

smoke:           ## 플랫폼 연결 점검 DAG 실행
	docker compose exec airflow-apiserver airflow dags unpause platform_smoke_test
	docker compose exec airflow-apiserver airflow dags trigger platform_smoke_test

test:            ## 단위 테스트 (Docker 불필요)
	uv run pytest -q

backfill:        ## 수집 backfill (예: make backfill src=seoul_subway_daily from=2026-11-01 to=2026-11-27)
	docker compose exec airflow-apiserver airflow dags unpause ingest__$(src)
	docker compose exec airflow-apiserver airflow backfill create --dag-id ingest__$(src) --from-date $(from) --to-date $(to)

dbt-dev:         ## dbt를 dev 타깃(dev_* 스키마)으로 빌드·테스트 (예: make dbt-dev args="--select staging")
	docker compose exec -w /opt/airflow/dbt airflow-worker sh -c '$$DBT_EXECUTABLE build --profiles-dir . --target dev $(args)'

dbt:             ## 임의의 dbt 명령 (예: make dbt cmd="ls --resource-type model")
	docker compose exec -w /opt/airflow/dbt airflow-worker sh -c '$$DBT_EXECUTABLE $(cmd) --profiles-dir .'

clean:           ## 컨테이너와 데이터 볼륨까지 삭제 (되돌릴 수 없음)
	@read -p "모든 데이터 볼륨을 삭제합니다. 계속할까요? [y/N] " ans && [ "$$ans" = y ]
	docker compose down -v
