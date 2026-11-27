"""랜딩 존(S3 호환 오브젝트 스토리지)에 API 응답 원본을 저장한다.

객체 키: {source}/dt={YYYY-MM-DD}/page-{n:05d}.json

같은 날짜를 다시 수집하면 해당 dt 프리픽스를 먼저 비우고 새로 쓴다. 그래서 재실행해도
이전 실행의 페이지가 섞여 남지 않는다 (페이지 수가 줄어든 경우 포함).
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator
from datetime import date

BUCKET = "landing"


def partition_prefix(source: str, target: date) -> str:
    return f"{source}/dt={target.isoformat()}/"


def page_key(source: str, target: date, number: int) -> str:
    return f"{partition_prefix(source, target)}page-{number:05d}.json"


def list_keys(s3, prefix: str, bucket: str = BUCKET) -> list[str]:
    keys: list[str] = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return sorted(keys)


def clear_partition(s3, source: str, target: date, bucket: str = BUCKET) -> int:
    keys = list_keys(s3, partition_prefix(source, target), bucket)
    for i in range(0, len(keys), 1000):  # delete_objects는 한 번에 1,000개까지
        batch = [{"Key": k} for k in keys[i : i + 1000]]
        s3.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
    return len(keys)


def write_partition(s3, source: str, target: date, pages: Iterable, bucket: str = BUCKET) -> list[str]:
    """pages(각각 .number, .body)를 dt 파티션에 쓴다. 쓴 객체 키 목록을 돌려준다.

    첫 페이지를 받은 뒤에 기존 파티션을 지운다. 데이터가 아직 공개되지 않아 첫 요청부터
    실패하면(DataNotReady) 이전에 받아 둔 원본이 그대로 남는다.
    """
    pages = iter(pages)
    first = next(pages, None)
    clear_partition(s3, source, target, bucket)
    written = []
    for page in itertools.chain([first] if first else [], pages):
        key = page_key(source, target, page.number)
        s3.put_object(Bucket=bucket, Key=key, Body=page.body, ContentType="application/json")
        written.append(key)
    return written


def read_partition(s3, source: str, target: date, bucket: str = BUCKET) -> Iterator[tuple[str, bytes]]:
    for key in list_keys(s3, partition_prefix(source, target), bucket):
        yield key, s3.get_object(Bucket=bucket, Key=key)["Body"].read()
