from datetime import date
from pathlib import Path

import pytest

from swl.sources import Source, load_sources

ROOT = Path(__file__).resolve().parent.parent


def test_repo_sources_yml_is_valid():
    sources = load_sources(ROOT / "sources.yml")
    assert {"seoul_subway_daily", "seoul_bike_rent_daily"} <= set(sources)
    for s in sources.values():
        assert s.raw_table.startswith("raw.")


def test_target_date_subtracts_lag():
    s = load_sources(ROOT / "sources.yml")["seoul_subway_daily"]
    assert s.target_date(date(2026, 11, 27)) == date(2026, 11, 24)
    assert s.render_path_params(date(2026, 11, 24)) == ["20261124"]


@pytest.mark.parametrize("table", ["staging.x", "raw.x; DROP TABLE y", "raw.X", "x"])
def test_rejects_unsafe_raw_table(table):
    with pytest.raises(ValueError):
        Source(name="s", description="", client="c", service="v", lag_days=0, schedule="@daily", raw_table=table)
