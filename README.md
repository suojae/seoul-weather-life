# seoul-weather-life

비가 오면 서울 사람들은 어떻게 움직이고, 어디에 머무나? 날씨와 서울의 이동·인구 데이터를 매일 모아 날씨가 일상에 주는 영향을 보여 주는 데이터 마트.

- [아키텍처](docs/architecture.md) — 전체 구조, 스택 선택 이유, 데이터 소스, DAG, 버스 매트릭스
- [로드맵](docs/roadmap.md) — 1단계 로컬 플랫폼 → 2단계 데이터 확장 → 3단계 Kubernetes

## 로컬 실행

사전 준비: [OrbStack](https://orbstack.dev) (`brew install --cask orbstack` 후 앱을 한 번 실행)

```bash
make init   # .env 생성 (비밀값 자동 생성, 외부 API 키는 직접 채운다)
make up     # 전체 스택 빌드·기동
make ps     # 상태 확인 — 모두 healthy면 준비 완료
make smoke  # 연결 점검 DAG 실행 (worker → SeaweedFS · 웨어하우스)
make test   # 단위 테스트 (uv 필요)
make backfill src=seoul_subway_daily from=2026-11-01 to=2026-11-28  # to는 마지막 실행일 + 1
```

| 서비스 | 주소 | 로그인 |
|---|---|---|
| Airflow | http://localhost:8080 | `.env`의 `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD` |
| Flower (Celery) | http://localhost:5555 | — |
| Metabase | http://localhost:3000 | 첫 접속 시 계정 생성 |
| SeaweedFS S3 | http://localhost:8333 | `.env`의 `S3_ACCESS_KEY` / `S3_SECRET_KEY` |
| 웨어하우스 | `localhost:5433` / DB `warehouse` | `.env`의 `WAREHOUSE_USER` / `WAREHOUSE_PASSWORD` |

Metabase에서 웨어하우스를 연결할 때는 호스트 `postgres-warehouse`, 포트 `5432`, 읽기 전용 계정 `bi_reader`를 쓴다.

## 데이터 출처

| 소스 | 제공처 | 용도 | 라이선스 |
|---|---|---|---|
| 종관기상관측 ASOS · 방재기상관측 AWS | 기상청 | 날씨 | 확인 필요 |
| 대기오염 측정 | 에어코리아 | 대기질 | 확인 필요 |
| 따릉이 이용 · 대여소 현황 | 서울 열린데이터광장 | 이동 | 확인 필요 |
| 지하철 역별·시간대별 승하차 | 서울 열린데이터광장 | 이동 | 확인 필요 |
| 서울 생활인구 · 실시간 도시데이터 | 서울 열린데이터광장 | 인구 | 확인 필요 |
| 행정동 경계 · 특일정보 | 행정안전부 · 한국천문연구원 | 기준 정보 | 확인 필요 |

코드는 [MIT](LICENSE). 데이터는 각 소스의 이용 조건을 따른다.
