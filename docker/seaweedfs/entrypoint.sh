#!/bin/sh
# S3 자격 증명을 환경변수에서 받아 설정 파일을 만든 뒤 SeaweedFS를 단일 노드(master+volume+filer+s3)로 띄운다.
# 볼륨 하나는 최대 1GB. 기본 볼륨 수 상한(8)은 버킷 하나를 만들 때 모두 예약돼 버리므로
# 상한을 64로 올린다 (랜딩 존 최대 약 64GB). 볼륨은 데이터가 쌓일 때만 디스크를 쓴다.
set -eu
cat > /tmp/s3.json <<JSON
{
  "identities": [
    {
      "name": "platform",
      "credentials": [{"accessKey": "${S3_ACCESS_KEY}", "secretKey": "${S3_SECRET_KEY}"}],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    }
  ]
}
JSON
exec weed server \
  -dir=/data \
  -ip=seaweedfs -ip.bind=0.0.0.0 \
  -master.volumeSizeLimitMB=1024 \
  -volume.max=64 \
  -s3 -s3.port=8333 -s3.config=/tmp/s3.json
