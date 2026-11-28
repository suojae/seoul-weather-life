FROM apache/airflow:3.4.0
# 공식 이미지에 celery·postgres·amazon 프로바이더가 포함돼 있다. 추가 의존성만 설치한다.
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

# dbt는 Airflow와 의존성이 충돌하지 않도록 별도 가상환경에 둔다 (Cosmos 권장 방식).
RUN python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir "dbt-core~=1.12.7" "dbt-postgres==1.11.0"
