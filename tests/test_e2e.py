"""Opt-in, credential-free checks against the public catalog and portal."""

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from datagokr.constants import DEFAULT_REMOTE_URL


@pytest.mark.skipif(os.environ.get("DATAGOKR_LIVE_TEST") != "1",
                    reason="[TEST] set DATAGOKR_LIVE_TEST=1 for live E2E")
def test_live_cli_and_stdio(tmp_path):
    endpoint = urlsplit(DEFAULT_REMOTE_URL)
    health_url = f"{endpoint.scheme}://{endpoint.netloc}/health"
    try:
        health = requests.get(health_url, timeout=15)
    except (requests.ConnectionError, requests.Timeout):
        pytest.skip("[TEST] public server network unavailable")
    assert health.status_code == 200, "[TEST] public server health failed"
    assert health.json()["status"] == "ok", "[TEST] public server is degraded"
    print("[TEST] live health status=ok")

    settings = dict(DATAGOKR_REMOTE_URL=DEFAULT_REMOTE_URL, DATAGOKR_API_KEY="",
                    DATAGOKR_SESSION_FILE=str(tmp_path / "session.json"),
                    DATAGOKR_DOWNLOAD_DIR=str(tmp_path / "downloads"))
    binary_dir = Path(sys.executable).parent

    def cli(*args):
        result = subprocess.run([str(binary_dir / "datagokr"), *args], cwd=tmp_path,
                                env=dict(os.environ, **settings), capture_output=True,
                                text=True, timeout=180)
        assert result.returncode == 0, "[TEST] live CLI request failed"
        return result.stdout

    search = cli("search", "전국 주차장")
    ids = re.findall(r"^\d+\. (\d+) \[", search, re.M)
    assert ids, "[TEST] live CLI search returned no datasets"
    print(f"[TEST] live CLI search results={len(ids)} first_id={ids[0]}")
    data = json.loads(cli("get", "15012896"))
    assert data["id"] == "15012896" and data["access_kind"] == "STD_FILE"
    columns, rows = data["data"]["columns"], data["data"]["rows"]
    assert columns and 1 <= len(rows) <= 5, "[TEST] live standard data has no first rows"
    assert all(len(row) == len(columns) for row in rows)
    assert data["total"] >= len(rows)
    print(f"[TEST] live CLI get id=15012896 rows={len(rows)} columns={len(columns)} total={data['total']}")

    async def scenario():
        transport = StdioTransport(command=str(binary_dir / "datagokr-mcp"), args=[],
                                   cwd=str(tmp_path), env=settings, keep_alive=False,
                                   log_file=tmp_path / "stdio.log")
        async with Client(transport, timeout=180, init_timeout=30) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert names == {"search", "show", "fields", "preview", "fetch", "get",
                             "apply", "download", "login_status"}
            found = (await client.call_tool("search", {"query": "전국 주차장"})).data
            assert isinstance(found, list) and found, "[TEST] live MCP search returned no datasets"
            assert all(row.get("id") and row.get("title") for row in found)
            print(f"[TEST] live MCP stdio tools={len(names)} search_results={len(found)} first_id={found[0]['id']}")
        assert transport._connect_task is None, "[TEST] stdio transport did not close"

    asyncio.run(scenario())
    assert not (tmp_path / "session.json").exists()
    assert not (tmp_path / "downloads").exists()
    print("[TEST] live E2E complete; no session or download files created")
