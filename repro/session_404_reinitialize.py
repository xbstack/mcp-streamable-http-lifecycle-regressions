"""Deterministic reproduction for modelcontextprotocol/python-sdk#3556.

This probe exercises the legacy Streamable HTTP client's 404 handling directly.
It seeds a stale Mcp-Session-Id, sends two ordinary JSON-RPC requests through a
fake HTTP client that returns 404, then verifies:

1. the client surfaces "Session terminated";
2. the stale session id is retained;
3. no InitializeRequest is generated automatically;
4. the same stale id is sent again on the second request.

The test is intentionally transport-level: it avoids external networking and
server process timing, so the result isolates the exact recovery contract in
the SDK client.
"""

from __future__ import annotations

import importlib.metadata
import platform
from contextlib import asynccontextmanager

import anyio

from mcp.client.streamable_http import RequestContext, StreamableHTTPTransport
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage, JSONRPCRequest


class FakeResponse:
    status_code = 404
    next_request = None
    headers: dict[str, str] = {}

    def __init__(self, request=None) -> None:
        self.request = request

    async def aread(self) -> bytes:
        return b""

    async def aclose(self) -> None:
        return None


class Always404Client:
    max_redirects = 20

    def __init__(self) -> None:
        self.requests: list[dict] = []

    def _record(self, method: str, url: str, json=None, headers=None) -> dict:
        request = {
            "method": method,
            "url": url,
            "json": json,
            "headers": dict(headers or {}),
        }
        self.requests.append(request)
        return request

    @asynccontextmanager
    async def stream(self, method: str, url: str, *, json=None, headers=None):
        request = self._record(method, url, json=json, headers=headers)
        yield FakeResponse(request=request)

    def build_request(self, method: str, url: str, **kwargs):
        return self._record(
            method,
            url,
            json=kwargs.get("json"),
            headers=kwargs.get("headers"),
        )

    async def send(self, request, *, stream: bool, follow_redirects: bool):
        return FakeResponse(request=request)


def request_message(request_id: int) -> SessionMessage:
    request = JSONRPCRequest(
        jsonrpc="2.0",
        id=request_id,
        method="tools/list",
        params={},
    )
    if isinstance(JSONRPCMessage, type):
        return SessionMessage(JSONRPCMessage(request))
    return SessionMessage(request)


async def run_once(
    transport: StreamableHTTPTransport,
    client: Always404Client,
    request_id: int,
):
    send_stream, receive_stream = anyio.create_memory_object_stream(1)
    try:
        ctx = RequestContext(
            client=client,
            session_id=transport.session_id,
            session_message=request_message(request_id),
            metadata=None,
            read_stream_writer=send_stream,
        )
        await transport._handle_post_request(ctx)
        message = await receive_stream.receive()
        return message
    finally:
        await send_stream.aclose()
        await receive_stream.aclose()


async def main() -> None:
    print("platform:", platform.platform())
    print("python:", platform.python_version())
    print("mcp:", importlib.metadata.version("mcp"))

    transport = StreamableHTTPTransport("http://example.invalid/mcp")
    transport.session_id = "stale-session-xbstack"
    client = Always404Client()

    first = await run_once(transport, client, 1)
    session_after_first = transport.session_id
    second = await run_once(transport, client, 2)
    session_after_second = transport.session_id

    first_dump = first.message.model_dump(mode="json", by_alias=True, exclude_none=True)
    second_dump = second.message.model_dump(mode="json", by_alias=True, exclude_none=True)

    methods = [
        item["json"].get("method")
        for item in client.requests
        if isinstance(item.get("json"), dict)
    ]
    session_headers = [
        item["headers"].get("mcp-session-id")
        or item["headers"].get("Mcp-Session-Id")
        for item in client.requests
    ]

    print("first response:", first_dump)
    print("second response:", second_dump)
    print("session after first 404:", session_after_first)
    print("session after second 404:", session_after_second)
    print("outbound methods:", methods)
    print("outbound session ids:", session_headers)

    first_error = first_dump.get("error", {})
    second_error = second_dump.get("error", {})

    reproduced = (
        first_error.get("message") == "Session terminated"
        and second_error.get("message") == "Session terminated"
        and session_after_first == "stale-session-xbstack"
        and session_after_second == "stale-session-xbstack"
        and methods == ["tools/list", "tools/list"]
        and session_headers == ["stale-session-xbstack", "stale-session-xbstack"]
        and "initialize" not in methods
    )

    if not reproduced:
        print("RESULT: NOT_REPRODUCED")
        raise SystemExit(1)

    print(
        "RESULT: REPRODUCED — two 404 responses produced Session terminated, "
        "the stale session id remained installed and was reused, and no "
        "InitializeRequest was emitted"
    )


if __name__ == "__main__":
    anyio.run(main)
