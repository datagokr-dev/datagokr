"""Synchronous wrappers for the read-only remote MCP contract."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from datagokr.config import load


class RemoteError(RuntimeError):
    """A remote failure without response bodies, request URLs or credentials."""


def _http_error(error):
    # Transport failures may be wrapped by the client's background task group.
    pending, seen = [error], set()
    while pending:
        item = pending.pop()
        if item is None or id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, httpx.HTTPStatusError):
            return item
        pending.extend(getattr(item, "exceptions", ()))
        pending.extend((item.__cause__, item.__context__))
    return None


def _retry_after(response):
    value = response.headers.get("Retry-After", "1")
    try:
        return max(0, int(value))
    except ValueError:
        try:
            return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 1


async def _call(tool, arguments, settings):
    headers = ({"X-DataGoKr-Key": settings.api_key}
               if tool == "get_preview" and settings.api_key else {})
    for attempt in range(2):
        try:
            transport = StreamableHttpTransport(settings.remote_url, headers=headers)
            async with Client(transport, timeout=90) as client:
                result = await client.call_tool(tool, arguments)
            if result.data is not None:
                return result.data
            # Older MCP servers may only return JSON in text content.
            return json.loads("".join(block.text for block in result.content if block.type == "text"))
        except Exception as exc:
            http_error = _http_error(exc)
            status = http_error.response.status_code if http_error else None
            if status == 429 and attempt == 0:
                await asyncio.sleep(_retry_after(http_error.response))
                continue
            detail = f" (HTTP {status})" if status else ""
            raise RemoteError(f"Remote MCP request failed{detail}; please retry later") from None


def call(tool, arguments=None, *, api_key=None, remote_url=None):
    """Call a public tool; only get_preview receives the configured API key.

    A worker thread keeps this synchronous API usable from notebooks and
    other callers that already have an asyncio event loop.
    """
    settings = load(api_key=api_key, remote_url=remote_url)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call(tool, arguments or {}, settings))
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(_call(tool, arguments or {}, settings))).result()


def search(query, n=10, dtype=None, org=None, fields=None, *, remote_url=None) -> dict:
    """Return {summary, results}, with one representative per candidate topic."""
    return call("search", dict(query=query, n=n, dtype=dtype, org=org, fields=list(fields or [])),
                remote_url=remote_url)


def show(dataset_id, *, remote_url=None):
    return call("show", {"dataset_id": str(dataset_id)}, remote_url=remote_url)


def record(dataset_id, *, remote_url=None):
    return call("record", {"dataset_id": str(dataset_id)}, remote_url=remote_url)


def fields(names, n=10, dtype=None, org=None, *, remote_url=None) -> dict:
    """Return {summary, results} for datasets matching every requested column."""
    return call("fields", dict(names=list(names), n=n, dtype=dtype, org=org), remote_url=remote_url)


def preview(dataset_id, n=5, *, api_key=None, remote_url=None):
    return call("get_preview", dict(dataset_id=str(dataset_id), n=n),
                api_key=api_key, remote_url=remote_url)


def download_url(dataset_id, *, remote_url=None):
    return call("download_url", {"dataset_id": str(dataset_id)}, remote_url=remote_url)
