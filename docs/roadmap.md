# 로드맵

세 단계로 나눈다. 앞 단계가 끝나야 다음 단계의 연습이 의미를 가진다.
설계 근거는 [architecture.md](architecture.md) 참고.

```mermaid
flowchart LR
    P1["1단계<br/>로컬 플랫폼 + 핵심 파이프라인"] --> P2["2단계<br/>데이터 확장 + 운영 고도화"] --> P3["3단계<br/>Kubernetes 마이그레이션"]
```

## 1단계 — 로컬 플랫폼과 핵심 파이프라인

Docker Compose 위에 전체 스택을 띄우고, 날씨 → 이동 → 영향 마트까지 한 줄을 끝까지 관통시킨다.
worker는 상시 띄워 둔다 (유휴 worker는 수백 MB 수준).

| 주차 | 할 일 | 완료 기준 |
|---|---|---|
| 1 | OrbStack 설치, `docker-compose.yml` (Airflow 3 · Celery · Redis · Postgres ×2 · SeaweedFS · Metabase) | `make up` 한 번으로 모든 컨테이너 healthy, Airflow UI·Flower·Metabase 접속 |
| 2 | 수집기: ASOS · 따릉이 이용 건수 · 지하철 일별 승하차. 랜딩 존 → raw 적재, `daily_batch` DAG | 지난 30일 backfill이 중복 없이 성공 |
| 3 | dbt staging · core: `dim_date`(공휴일), `dim_dong`(PostGIS), `fct_weather_hourly`, `fct_bike_rides_daily`, `fct_subway_ridership` + 테스트 | `dbt build` 통과, 테스트 실패 시 marts 미갱신 |
| 4 | `mart_weather_impact`(평소 대비 증감), Metabase 대시보드, `transform` DAG(Asset 트리거) | "비 온 날 따릉이 −X%, 지하철 +Y%"가 대시보드에 보인다 |

## 2단계 — 데이터 확장과 운영 고도화

소스마다 새로운 데이터 엔지니어링 패턴을 하나씩 연습한다.

| 추가 | 연습하는 패턴 |
|---|---|
| DAG 팩토리 + `sources.yml` | 소스 추가 = 설정 한 줄 + 클라이언트 하나 |
| AWS 관측 (기상청 API허브) | 고정폭 텍스트 파싱, 데이터 양 증가에 따른 파티셔닝·incremental |
| 에어코리아 대기질 | 다른 기관 키 매핑, 날씨 유형 "미세먼지 나쁨" |
| 서울 생활인구 | 공개 지연이 긴 소스, 늦게 도착하는 데이터 |
| 따릉이 거치 현황 · 실시간 도시데이터 | 10분 스냅샷 append (`realtime_poll`) |
| 대여소·역 마스터 | SCD Type 2 |
| GitHub Actions CI | ruff · sqlfluff · pytest · `dbt build --target ci` |
| 실패 알림 · SLA | Slack/Discord 웹훅, source freshness 경보 |
| (선택) 전력 수요 등 영향 데이터 | 도메인 간 조인 |

## 3단계 — Kubernetes 마이그레이션

같은 DAG·같은 코드를 그대로 두고 실행 인프라만 바꾼다.

- OrbStack 내장 Kubernetes에 Airflow 공식 Helm 차트로 배포
- **KEDA**로 Redis 큐 길이를 보고 Celery worker를 0 ↔ N개로 자동 조절 — 상시 서버는 scheduler·api-server만, worker는 작업이 있을 때만 뜬다
- 비교 실험: KubernetesExecutor(태스크마다 Pod)와 Celery + KEDA의 차이
- 완료 기준: 작업이 없는 시간대에 worker Pod 0개, 05시 배치에 자동으로 뜨고 끝나면 내려간다
