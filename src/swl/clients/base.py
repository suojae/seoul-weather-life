from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from swl.sources import Source


@dataclass
class Page:
    """API 응답 한 페이지. body는 랜딩 존에 그대로 저장하고, rows는 적재에 쓴다."""

    number: int
    body: bytes
    rows: list[dict]
    total: int


class Client(Protocol):
    def fetch_source(self, source: Source, target: date) -> Iterator[Page]:
        """source의 target 날짜 데이터를 페이지 단위로 돌려준다. 공개 전이면 DataNotReady."""
        ...
