import json

import httpx
import pytest

from swl.clients.seoul_openapi import SeoulOpenApiClient
from swl.errors import DataNotReady, SourceError


def _ok(root: str, total: int, start: int, end: int) -> dict:
    rows = [{"N": i} for i in range(start, min(end, total) + 1)]
    return {root: {"list_total_count": total, "RESULT": {"CODE": "INFO-000"}, "row": rows}}


def _client(handler, key="KEY", page_size=1000):
    return SeoulOpenApiClient(key, http=httpx.Client(transport=httpx.MockTransport(handler)), page_size=page_size)


def test_paginates_until_total():
    seen = []

    def handler(request):
        parts = request.url.path.strip("/").split("/")  # KEY/json/SVC/start/end/param
        start, end = int(parts[3]), int(parts[4])
        seen.append((start, end, parts[5]))
        return httpx.Response(200, json=_ok("svcRoot", 2500, start, end))

    pages = list(_client(handler).fetch("SVC", ["20261120"]))

    assert seen == [(1, 1000, "20261120"), (1001, 2000, "20261120"), (2001, 3000, "20261120")]
    assert [p.number for p in pages] == [1, 2, 3]
    assert sum(len(p.rows) for p in pages) == 2500


def test_root_name_can_differ_from_service():
    body = _ok("cycleRentUseDayInfo", 1, 1, 1)
    pages = list(_client(lambda r: httpx.Response(200, json=body)).fetch("tbCycleRentUseDayInfo", []))
    assert pages[0].rows == [{"N": 1}]
    assert SeoulOpenApiClient.rows_from_body(pages[0].body) == [{"N": 1}]


def test_no_data_means_not_ready():
    body = {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}
    with pytest.raises(DataNotReady):
        list(_client(lambda r: httpx.Response(200, json=body)).fetch("SVC", []))


def test_error_code_raises():
    body = {"RESULT": {"CODE": "ERROR-500", "MESSAGE": "서버 오류"}}
    with pytest.raises(SourceError) as exc:
        list(_client(lambda r: httpx.Response(200, json=body)).fetch("SVC", []))
    assert not isinstance(exc.value, DataNotReady)


def test_xml_error_raises():
    xml = "<RESULT><CODE>ERROR-335</CODE></RESULT>"
    with pytest.raises(SourceError):
        list(_client(lambda r: httpx.Response(200, text=xml)).fetch("SVC", []))


def test_sample_key_requests_five_rows_once():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=_ok("root", 600, 1, 5))

    pages = list(_client(handler, key="sample").fetch("SVC", []))
    assert len(calls) == 1 and "/1/5" in calls[0]
    assert len(pages[0].rows) == 5


def test_empty_key_rejected():
    with pytest.raises(SourceError):
        SeoulOpenApiClient("")
