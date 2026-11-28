"""기상청 지상(종관, ASOS) 시간자료 조회서비스 (공공데이터포털).

    GET https://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList
        ?serviceKey=..&dataType=JSON&dataCd=ASOS&dateCd=HR
        &stnIds=108&startDt=YYYYMMDD&startHh=00&endDt=YYYYMMDD&endHh=23&numOfRows=..&pageNo=..

요청 한 번에 관측소 하나만 받을 수 있어 sources.yml의 stations마다 요청한다.
전날 자료까지만 제공되며, 당일 이후를 요청하면 resultCode 99("전날 자료까지 제공됩니다")가 온다.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date

import httpx

from swl.clients.base import Page
from swl.errors import DataNotReady, SourceError
from swl.sources import Source

BASE_URL = "https://apis.data.go.kr/1360000/AsosHourlyInfoService"
PAGE_SIZE = 999

_OK = "00"
_NO_DATA = "03"  # NODATA_ERROR


class AsosHourlyClient:
    def __init__(self, key: str, http: httpx.Client | None = None, page_size: int = PAGE_SIZE):
        if not key:
            raise SourceError("KMA_SERVICE_KEY is empty")
        self.key = key
        self.http = http or httpx.Client(timeout=30)
        self.page_size = page_size

    def fetch_source(self, source: Source, target: date) -> Iterator[Page]:
        stations = source.params.get("stations") or []
        if not stations:
            raise SourceError(f"{source.name}: params.stations is empty")
        number = 1
        for station in stations:
            for page in self.fetch_station(source.service, int(station), target, start_number=number):
                yield page
                number = page.number + 1

    def fetch_station(self, service: str, station: int, target: date, start_number: int = 1) -> Iterator[Page]:
        day = target.strftime("%Y%m%d")
        page_no, total = 1, None
        while total is None or (page_no - 1) * self.page_size < total:
            resp = self.http.get(
                f"{BASE_URL}/{service}",
                params={
                    "serviceKey": self.key,
                    "dataType": "JSON",
                    "dataCd": "ASOS",
                    "dateCd": "HR",
                    "stnIds": station,
                    "startDt": day,
                    "startHh": "00",
                    "endDt": day,
                    "endHh": "23",
                    "numOfRows": self.page_size,
                    "pageNo": page_no,
                },
            )
            resp.raise_for_status()
            rows, total = self._parse(service, station, resp)
            yield Page(number=start_number + page_no - 1, body=resp.content, rows=rows, total=total)
            if not rows:
                return
            page_no += 1

    @staticmethod
    def rows_from_body(body: bytes) -> list[dict]:
        return _items(json.loads(body)["response"].get("body", {}))

    @staticmethod
    def _parse(service: str, station: int, resp: httpx.Response) -> tuple[list[dict], int]:
        try:
            data = resp.json()
        except ValueError as exc:
            # 인증키 오류 등은 XML(OpenAPI_ServiceResponse)로 온다
            raise SourceError(f"{service} stn={station}: non-JSON response: {resp.text[:200]}") from exc

        header = data["response"]["header"]
        code, msg = header.get("resultCode"), header.get("resultMsg", "")
        if code == _NO_DATA or (code == "99" and "전날" in msg):
            raise DataNotReady(f"{service} stn={station}: {code} {msg}")
        if code != _OK:
            raise SourceError(f"{service} stn={station}: {code} {msg}")
        body = data["response"].get("body", {})
        return _items(body), int(body.get("totalCount", 0))


def _items(body: dict) -> list[dict]:
    # 결과가 없으면 items가 빈 문자열로 오기도 한다
    items = body.get("items") or {}
    item = items.get("item", []) if isinstance(items, dict) else []
    return item if isinstance(item, list) else [item]
