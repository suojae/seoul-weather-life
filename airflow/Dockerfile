FROM apache/airflow:3.4.0
# 공식 이미지에 celery·postgres·amazon 프로바이더가 포함돼 있다. 추가 의존성만 설치한다.
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt
