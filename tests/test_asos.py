from datetime import date

import httpx
import pytest

from swl.clients.asos import AsosHourlyClient
from swl.errors import DataNotReady, SourceError
from swl.sources import Source

DAY = date(2026, 11, 26)


def _source(stations=(108,)):
    return Source(
        name="kma_asos_hourly",
        description="",
        client="kma_asos_hourly",
        service="getWthrDataList",
        lag_days=1,
        schedule="0 7 * * *",
        raw_table="raw.kma_asos_hourly",
        params={"stations": list(stations)},
    )


def _resp(code="00", msg="NORMAL_SERVICE", items=None, total=None):
    body = {}
    if items is not None:
        body = {"items": {"item": items} if items else "", "totalCount": len(items) if total is None else total}
    return {"response": {"header": {"resultCode": code, "resultMsg": msg}, "body": body}}


def _client(handler, page_size=999):
    return AsosHourlyClient("KEY", http=httpx.Client(transport=httpx.MockTransport(handler)), page_size=page_size)


def test_one_request_per_station_with_day_range():
    seen = []

    def handler(request):
        p = request.url.params
        seen.append((p["stnIds"], p["startDt"], p["startHh"], p["endDt"], p["endHh"], p["dataType"]))
        items = [{"stnId": p["stnIds"], "tm": f"2026-11-26 {h:02d}:00"} for h in range(24)]
        return httpx.Response(200, json=_resp(items=items))

    pages = list(_client(handler).fetch_source(_source(stations=(108, 119)), DAY))

    assert seen == [("108", "20261126", "00", "20261126", "23", "JSON"), ("119", "20261126", "00", "20261126", "23", "JSON")]
    assert [p.number for p in pages] == [1, 2]  # 관측소가 달라도 페이지 번호는 이어진다
    assert sum(len(p.rows) for p in pages) == 48
    assert AsosHourlyClient.rows_from_body(pages[1].body)[0]["stnId"] == "119"


def test_paginates_within_station():
    def handler(request):
        page = int(request.url.params["pageNo"])
        rows = [{"i": i} for i in range((page - 1) * 10, min(page * 10, 24))]
        return httpx.Response(200, json=_resp(items=rows, total=24))

    pages = list(_client(handler, page_size=10).fetch_source(_source(), DAY))
    assert [len(p.rows) for p in pages] == [10, 10, 4]


@pytest.mark.parametrize(
    "code,msg",
    [("99", "전날 자료까지 제공됩니다. 날짜 범위를 확인해주세요."), ("03", "NODATA_ERROR")],
)
def test_not_published_yet(code, msg):
    with pytest.raises(DataNotReady):
        list(_client(lambda r: httpx.Response(200, json=_resp(code, msg))).fetch_source(_source(), DAY))


def test_other_error_codes_raise_source_error():
    with pytest.raises(SourceError) as exc:
        list(_client(lambda r: httpx.Response(200, json=_resp("10", "INVALID_REQUEST_PARAMETER_ERROR"))).fetch_source(_source(), DAY))
    assert not isinstance(exc.value, DataNotReady)


def test_xml_auth_error_raises():
    xml = "<OpenAPI_ServiceResponse><cmmMsgHeader><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg></cmmMsgHeader></OpenAPI_ServiceResponse>"
    with pytest.raises(SourceError):
        list(_client(lambda r: httpx.Response(200, text=xml)).fetch_source(_source(), DAY))


def test_empty_items_string_is_no_rows():
    assert AsosHourlyClient.rows_from_body(b'{"response": {"body": {"items": "", "totalCount": 0}}}') == []


def test_single_item_dict_is_wrapped():
    body = b'{"response": {"body": {"items": {"item": {"tm": "x"}}, "totalCount": 1}}}'
    assert AsosHourlyClient.rows_from_body(body) == [{"tm": "x"}]


def test_requires_stations():
    with pytest.raises(SourceError):
        list(_client(lambda r: httpx.Response(200)).fetch_source(_source(stations=()), DAY))
