import asyncio
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def test_stdio_entrypoints_tools_and_mock_remote(tmp_path):
    calls = []
    rows = [dict(id="15012896", title="[TEST] 전국주차장정보표준데이터", rank=1)]
    remote_tools = ("search", "show", "fields", "get_preview", "record")
    key = "fixture-private-key"
    secret = "fixture-private-cookie"

    class Catalog(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_error(405)

        def do_POST(self):
            message = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append((message, dict(self.headers)))
            if "id" not in message:
                self.send_response(202)
                self.end_headers()
                return
            method = message["method"]
            if method == "initialize":
                result = dict(protocolVersion=message["params"]["protocolVersion"],
                              capabilities={"tools": {}}, serverInfo={"name": "[TEST] catalog", "version": "1"})
            elif method == "tools/list":
                result = {"tools": [dict(name=name, inputSchema={"type": "object"}) for name in remote_tools]}
            else:
                assert method == "tools/call", "[TEST] unexpected catalog method"
                name, args = message["params"]["name"], message["params"]["arguments"]
                if name in ("search", "fields"):
                    payload = rows
                elif name == "show":
                    payload = dict(id=args["dataset_id"], columns=[{"name": "위도"}])
                elif name == "get_preview":
                    payload = dict(data={"columns": ["위도"], "rows": [[37.5]]})
                else:
                    assert name == "record", "[TEST] unexpected catalog tool"
                    payload = dict(id=args["dataset_id"], dtype="FILE", access_kind="LINK",
                                   external_url="https://provider.invalid/data")
                    if args["dataset_id"] == "api":
                        payload.update(dtype="API", access_kind="OPEN_API", examples=[{"url": "https://api.invalid/"}],
                                       page_url="https://portal.invalid/api")
                error = args.get("query") == "[TEST] remote failure"
                result = dict(content=[dict(type="text", text=secret if error else json.dumps(payload))], isError=error)
            body = json.dumps(dict(jsonrpc="2.0", id=message["id"], result=result)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    catalog = ThreadingHTTPServer(("127.0.0.1", 0), Catalog)
    worker = Thread(target=catalog.serve_forever, daemon=True)
    worker.start()
    env = dict(DATAGOKR_REMOTE_URL=f"http://127.0.0.1:{catalog.server_port}/mcp",
               DATAGOKR_API_KEY=key, DATAGOKR_SESSION_FILE=str(tmp_path / "missing-session.json"),
               DATAGOKR_DOWNLOAD_DIR=str(tmp_path / "downloads"))
    commands = [(str(Path(sys.executable).with_name("datagokr-mcp")), []),
                (sys.executable, ["-m", "datagokr.mcp"])]
    expected = {"search", "show", "fields", "preview", "fetch", "get", "apply", "download", "login_status"}

    async def scenario():
        for index, (command, arguments) in enumerate(commands):
            log = tmp_path / f"stdio-{index}.log"
            transport = StdioTransport(command=command, args=arguments, cwd=str(tmp_path),
                                       env=env, keep_alive=False, log_file=log)
            async with Client(transport, timeout=15, init_timeout=15) as client:
                tools = {tool.name: tool for tool in await client.list_tools()}
                assert set(tools) == expected
                for name, tool in tools.items():
                    assert re.search("[가-힣]", tool.description) and re.search("[A-Za-z]{3}", tool.description)
                    assert not {"api_key", "cookie", "remote_url"} & tool.inputSchema["properties"].keys()
                    assert tool.annotations.readOnlyHint == (name not in {"apply", "get", "download"})
                assert tools["get"].annotations.destructiveHint and tools["download"].annotations.destructiveHint
                assert tools["search"].inputSchema["required"] == ["query"]
                assert tools["apply"].inputSchema["properties"]["ids"]["type"] == "array"
                assert (await client.call_tool("search", dict(query="전국 주차장", n=3, dtype="FILE",
                                                              org="서울", fields=["위도"]))).data == rows
                if index == 0:
                    assert (await client.call_tool("show", {"dataset_id": "15012896"})).data["columns"] == [{"name": "위도"}]
                    assert (await client.call_tool("fields", dict(names=["위도", "경도"], n=2))).data == rows
                    assert (await client.call_tool("preview", dict(dataset_id="15012896", n=2))).data["data"]["rows"] == [[37.5]]
                    assert (await client.call_tool("fetch", dict(dataset_id="api", n=2))).data["request_templates"] == [{"url": "https://api.invalid/"}]
                    assert (await client.call_tool("get", dict(dataset_id="link", no_apply=True, probe=True))).data["url"] == "https://provider.invalid/data"
                    assert (await client.call_tool("download", dict(dataset_id="link", probe=True))).data == [{"url": "https://provider.invalid/data"}]
                    application = (await client.call_tool("apply", dict(ids=["15012896"], purpose="[TEST] 분석"))).data
                    assert application[0]["status"] == "manual" and "datagokr login" in application[0]["reason"]
                    status = (await client.call_tool("login_status")).data
                    assert status["authenticated"] is False and "datagokr login" in status["message"]
                    for args in ({"query": [secret]}, {"query": "[TEST] remote failure"}):
                        result = await client.call_tool("search", args, raise_on_error=False)
                        rendered = result.content[0].text
                        assert result.is_error and "Request failed" in rendered
                        assert secret not in rendered and key not in rendered
            assert transport._connect_task is None
            assert secret not in log.read_text() and key not in log.read_text()

    try:
        asyncio.run(scenario())
    finally:
        catalog.shutdown()
        catalog.server_close()
        worker.join(timeout=5)
    requests = [message["params"] for message, _ in calls if message["method"] == "tools/call"]
    assert next(item["arguments"] for item in requests if item["name"] == "search") == dict(
        query="전국 주차장", n=3, dtype="FILE", org="서울", fields=["위도"])
    assert next(item["arguments"] for item in requests if item["name"] == "fields") == dict(
        names=["위도", "경도"], n=2, dtype=None, org=None)
    assert next(item["arguments"] for item in requests if item["name"] == "get_preview") == dict(dataset_id="15012896", n=2)
    connections = []
    for message, headers in calls:
        if message["method"] == "initialize":
            connections.append([])
        connections[-1].append((message, {name.lower(): value for name, value in headers.items()}))
    for connection in connections:
        tool = next(message["params"]["name"] for message, _ in connection if message["method"] == "tools/call")
        # Preview credentials also accompany that connection's MCP handshake.
        for message, headers in connection:
            assert headers.get("x-datagokr-key") == (key if tool == "get_preview" else None)
            assert "cookie" not in headers
            assert key not in json.dumps(message) and secret not in json.dumps(message)
    assert not (tmp_path / "downloads").exists()
