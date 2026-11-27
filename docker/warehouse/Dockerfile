# postgis/postgis 공식 이미지는 amd64 전용이라 Apple Silicon에서는 에뮬레이션으로 돈다.
# 공식 postgres 이미지(arm64 지원)에 PGDG 패키지로 PostGIS만 얹는다.
FROM postgres:17-bookworm
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-17-postgis-3 \
 && rm -rf /var/lib/apt/lists/*
