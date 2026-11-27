"""sources.yml을 읽어 수집 소스 정의를 만든다."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

_RAW_TABLE = re.compile(r"^raw\.[a-z_][a-z0-9_]*$")
_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class Source:
    name: str
    description: str
    client: str
    service: str
    lag_days: int
    schedule: str
    raw_table: str
    path_params: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not _NAME.match(self.name):
            raise ValueError(f"invalid source name: {self.name!r}")
        # raw_table은 SQL에 식별자로 들어가므로 형식을 강제한다
        if not _RAW_TABLE.match(self.raw_table):
            raise ValueError(f"{self.name}: raw_table must look like raw.<name>, got {self.raw_table!r}")
        if self.lag_days < 0:
            raise ValueError(f"{self.name}: lag_days must be >= 0")

    def target_date(self, run_date: date) -> date:
        """실행일에서 공개 지연만큼 뺀 수집 대상 날짜."""
        return run_date - timedelta(days=self.lag_days)

    def render_path_params(self, target: date) -> list[str]:
        return [p.format(date=target) for p in self.path_params]


def load_sources(path: str | Path) -> dict[str, Source]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    sources = {}
    for name, spec in (data.get("sources") or {}).items():
        spec = dict(spec)
        spec["path_params"] = tuple(spec.get("path_params", ()))
        sources[name] = Source(name=name, **spec)
    return sources
