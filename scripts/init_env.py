"""`.env.example`을 `.env`로 복사하고 CHANGE_ME 자리에 무작위 비밀값을 채운다. 이미 .env가 있으면 건드리지 않는다."""

import base64
import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
src, dst = root / ".env.example", root / ".env"

if dst.exists():
    sys.exit(".env already exists — leaving it untouched")

lines = []
for line in src.read_text().splitlines():
    key, sep, value = line.partition("=")
    if sep and value == "CHANGE_ME":
        if key == "AIRFLOW_FERNET_KEY":
            value = base64.urlsafe_b64encode(os.urandom(32)).decode()
        else:
            value = secrets.token_urlsafe(24)
    lines.append(f"{key}{sep}{value}" if sep else line)

dst.write_text("\n".join(lines) + "\n")
dst.chmod(0o600)
print(f"created {dst.relative_to(root)}")
