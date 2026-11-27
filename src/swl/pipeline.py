"""수집(extract)과 적재(load) 두 단계. DAG은 이 함수들을 호출하기만 한다.

    extract: 소스 API → 랜딩 존 dt 파티션 (원본 그대로)
    load:    랜딩 존 dt 파티션 → 웨어하우스 raw 테이블

두 단계를 나눠 두면 파싱이나 적재를 고쳤을 때 API를 다시 부르지 않고 load만 다시 돌릴 수 있다.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from swl import landing, loaders
from swl.clients import SeoulOpenApiClient
from swl.sources import Source


@dataclass(frozen=True)
class ClientSpec:
    make: Callable[[], object]  # .fetch(service, path_params) -> Iterator[Page]
    parse_rows: Callable[[bytes], list[dict]]


CLIENTS: dict[str, ClientSpec] = {
    "seoul_openapi": ClientSpec(
        make=lambda: SeoulOpenApiClient(os.environ.get("SEOUL_OPENDATA_KEY", "")),
        parse_rows=SeoulOpenApiClient.rows_from_body,
    ),
}


def extract(source: Source, target: date, s3, client=None) -> list[str]:
    client = client or CLIENTS[source.client].make()
    pages = client.fetch(source.service, source.render_path_params(target))
    return landing.write_partition(s3, source.name, target, pages)


def load(source: Source, target: date, s3, conn) -> int:
    objects = landing.read_partition(s3, source.name, target)
    return loaders.load_partition(conn, source, target, objects, CLIENTS[source.client].parse_rows)
