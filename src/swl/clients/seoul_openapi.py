"""서울 열린데이터광장 OpenAPI 클라이언트.

모든 서비스가 같은 형식을 쓴다:
    http://openapi.seoul.go.kr:8088/{KEY}/json/{SERVICE}/{START}/{END}/{추가 파라미터...}

한 번에 최대 1,000건까지 받을 수 있어 페이지를 나눠 요청한다. 인증키로 `sample`을 쓰면
한 번에 5건까지만 허용되므로, 첫 5건만 받아 개발·테스트용으로 쓴다.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date

import httpx

from swl.clients.base import Page
from swl.errors import DataNotReady, SourceError
from swl.sources import Source

BASE_URL = "http://openapi.seoul.go.kr:8088"
PAGE_SIZE = 1000
SAMPLE_KEY = "sample"
SAMPLE_MAX_ROWS = 5

_NO_DATA = "INFO-200"
_OK = "INFO-000"


class SeoulOpenApiClient:
    def __init__(self, key: str, http: httpx.Client | None = None, page_size: int = PAGE_SIZE):
        if not key:
            raise SourceError("SEOUL_OPENDATA_KEY is empty (use 'sample' for development)")
        self.key = key
        self.http = http or httpx.Client(timeout=30)
        self.page_size = SAMPLE_MAX_ROWS if key == SAMPLE_KEY else page_size

    def fetch_source(self, source: Source, target: date) -> Iterator[Page]:
        return self.fetch(source.service, source.render_path_params(target))

    def fetch(self, service: str, path_params: list[str]) -> Iterator[Page]:
        start, number, total = 1, 1, None
        while total is None or start <= total:
            end = start + self.page_size - 1
            url = "/".join([BASE_URL, self.key, "json", service, str(start), str(end), *path_params])
            resp = self.http.get(url)
            resp.raise_for_status()
            rows, total_now = self._parse(service, resp)
            total = total_now if total is None else total
            yield Page(number=number, body=resp.content, rows=rows, total=total)
            if self.key == SAMPLE_KEY or not rows:
                return
            start, number = end + 1, number + 1

    @staticmethod
    def rows_from_body(body: bytes) -> list[dict]:
        """랜딩 존에 저장해 둔 원본 페이지에서 레코드를 꺼낸다 (적재 단계용)."""
        data = json.loads(body)
        return next(iter(data.values())).get("row", [])

    @staticmethod
    def _parse(service: str, resp: httpx.Response) -> tuple[list[dict], int]:
        try:
            data = resp.json()
        except ValueError as exc:
            # 오류는 XML로 오기도 한다 (예: sample 키로 5건 초과 요청)
            raise SourceError(f"{service}: non-JSON response: {resp.text[:200]}") from exc

        # 정상 응답은 {"<루트 이름>": {...}}, 오류는 {"RESULT": {...}} 형태다.
        # 루트 이름은 서비스명과 다를 수 있다 (tbCycleRentUseDayInfo → cycleRentUseDayInfo).
        body = data if "RESULT" in data else next(iter(data.values()))
        result = body.get("RESULT", {})
        code = result.get("CODE")
        if code == _NO_DATA:
            raise DataNotReady(f"{service}: {result.get('MESSAGE')}")
        if code != _OK:
            raise SourceError(f"{service}: {code} {result.get('MESSAGE')}")
        return body.get("row", []), int(body["list_total_count"])
