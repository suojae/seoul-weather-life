#!/bin/sh
# S3 자격 증명을 환경변수에서 받아 설정 파일을 만든 뒤 SeaweedFS를 단일 노드(master+volume+filer+s3)로 띄운다.
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
  -s3 -s3.port=8333 -s3.config=/tmp/s3.json
