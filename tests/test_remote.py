import asyncio
import json
import traceback
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

import datagokr
from datagokr import remote
from datagokr.config import KEYS


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


def fake_client(monkeypatch, effects):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.call_tool.side_effect = effects
    factory = Mock(return_value=client)
    monkeypatch.setattr(remote, "Client", factory)
    return factory, client


def http_error(status, retry_after="3"):
    request = httpx.Request("POST", "https://remote.invalid/mcp")
    response = httpx.Response(status, headers={"Retry-After": retry_after}, request=request)
    return httpx.HTTPStatusError("fixture-sensitive-error", request=request, response=response)


def test_public_routes_and_preview_key_isolation(monkeypatch):
    monkeypatch.setenv("DATAGOKR_API_KEY", "fixture-environment")
    payload = {"id": "15012896"}
    factory, client = fake_client(monkeypatch, [SimpleNamespace(data=payload)] * 8)
    routes = [
        (lambda: datagokr.search("주차장", 3, "FILE", "서울", ("위도",)), "search",
         dict(query="주차장", n=3, dtype="FILE", org="서울", fields=["위도"])),
        (lambda: datagokr.show(15012896), "show", {"dataset_id": "15012896"}),
        (lambda: remote.record(15012896), "record", {"dataset_id": "15012896"}),
        (lambda: datagokr.fields(("위도", "경도"), 2, "FILE", "서울"), "fields",
         dict(names=["위도", "경도"], n=2, dtype="FILE", org="서울")),
        (lambda: remote.download_url(15012896), "download_url", {"dataset_id": "15012896"}),
        (lambda: datagokr.preview(15012896, 2), "get_preview", dict(dataset_id="15012896", n=2)),
    ]
    for invoke, tool, arguments in routes:
        assert invoke() == payload
        client.call_tool.assert_awaited_with(tool, arguments)
        transport = factory.call_args.args[0]
        assert transport.headers == ({"X-DataGoKr-Key": "fixture-environment"} if tool == "get_preview" else {})
        assert "fixture-environment" not in repr(client.call_tool.call_args)
    datagokr.preview("1", api_key="fixture-argument", remote_url="https://override.invalid/mcp")
    transport = factory.call_args.args[0]
    assert transport.headers == {"X-DataGoKr-Key": "fixture-argument"}
    assert transport.url == "https://override.invalid/mcp"
    datagokr.preview("1", api_key="")
    assert factory.call_args.args[0].headers == {}


def test_real_fastmcp_http_protocol_and_sync_call_in_running_loop(monkeypatch):
    calls = []
    payload = [{"id": "15012896", "title": "전국주차장정보표준데이터"}]
    sleep = AsyncMock()
    monkeypatch.setattr(remote.asyncio, "sleep", sleep)

    def respond(request):
        message = json.loads(request.content)
        calls.append(message)
        method = message["method"]
        if "id" not in message:
            return httpx.Response(202)
        if method == "initialize":
            result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "fixture", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": [{"name": "search", "inputSchema": {"type": "object"},
                "outputSchema": {"type": "object", "x-fastmcp-wrap-result": True,
                    "properties": {"result": {"type": "array", "items": {"type": "object"}}},
                    "required": ["result"]}}]}
        else:
            assert method == "tools/call"
            if sum(row["method"] == method for row in calls) == 1:
                return httpx.Response(429, headers={"Retry-After": "4"})
            result = {"content": [{"type": "text", "text": json.dumps(payload)}],
                      "structuredContent": {"result": payload}, "isError": False}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": message["id"], "result": result})

    transport_type = remote.StreamableHttpTransport

    def transport(url, headers):
        return transport_type(url, headers=headers, httpx_client_factory=lambda **kwargs:
                              httpx.AsyncClient(transport=httpx.MockTransport(respond), **kwargs))

    monkeypatch.setattr(remote, "StreamableHttpTransport", transport)

    async def scenario():
        # Calls the synchronous API directly while an event loop is already running.
        return datagokr.search("전국 주차장", remote_url="https://fixture.invalid/mcp")

    assert asyncio.run(scenario()) == payload
    request = next(row for row in calls if row["method"] == "tools/call")
    assert request["params"]["name"] == "search"
    assert request["params"]["arguments"]["query"] == "전국 주차장"
    sleep.assert_awaited_once_with(4)
    assert sum(row["method"] == "tools/call" for row in calls) == 2


def test_429_waits_and_retries_once_including_wrapped_connect_error(monkeypatch):
    error = RuntimeError("connection failed")
    error.__cause__ = ExceptionGroup("transport", [http_error(429, "7")])
    factory, client = fake_client(monkeypatch, [SimpleNamespace(data=[])])
    client.__aenter__.side_effect = [error, client]
    sleep = AsyncMock()
    monkeypatch.setattr(remote.asyncio, "sleep", sleep)
    assert remote.search("주차장") == []
    sleep.assert_awaited_once_with(7)
    assert factory.call_count == 2
    assert client.call_tool.await_count == 1


def test_retry_limit_other_errors_and_secret_free_traceback(monkeypatch, capsys, caplog):
    sleep = AsyncMock()
    monkeypatch.setattr(remote.asyncio, "sleep", sleep)
    key = "fixture-sensitive-key"
    for status, expected_calls in ((429, 2), (503, 1)):
        factory, client = fake_client(monkeypatch, [http_error(status)] * 2)
        with pytest.raises(remote.RemoteError, match=f"HTTP {status}") as error:
            remote.preview("1", api_key=key)
        assert client.call_tool.await_count == expected_calls
        rendered = "".join(traceback.format_exception(error.value))
        assert "fixture-sensitive-error" not in rendered
        assert "fixture-sensitive-key" not in rendered
        assert "fixture-sensitive" not in caplog.text
        assert "fixture-sensitive" not in capsys.readouterr().err
    sleep.assert_awaited_once_with(3)


def test_text_result_fallback_and_retry_after_http_date(monkeypatch):
    future = datetime.now(timezone.utc) + timedelta(seconds=60)
    delay = remote._retry_after(http_error(429, format_datetime(future, usegmt=True)).response)
    assert 58 <= delay <= 60
    assert remote._retry_after(http_error(429, "invalid").response) == 1
    assert remote._retry_after(http_error(429, "-1").response) == 0
    fake_client(monkeypatch, [SimpleNamespace(data=None,
        content=[SimpleNamespace(type="text", text='{"id":"15012896"}')])])
    assert remote.record("15012896") == {"id": "15012896"}
