"""Direct reproduction for modelcontextprotocol/python-sdk#3503 on MCP 2.2.0."""

import asyncio
import importlib.metadata
import platform

import uvicorn
from mcp import Client
from mcp.server.mcpserver import MCPServer


seen_get_headers: list[dict[str, str]] = []

server = MCPServer(name="probe", version="0.1.0")


@server.tool()
def echo(text: str) -> str:
    return text


class TakeTheClientAtItsWord:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "GET":
            headers = {
                key.decode("latin1").lower(): value.decode("latin1")
                for key, value in scope.get("headers", [])
            }
            seen_get_headers.append(headers)
            body = b'{"jsonrpc":"2.0"}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


async def main() -> None:
    print("platform:", platform.platform())
    print("python:", platform.python_version())
    for package in ("mcp", "uvicorn", "httpx2", "httpcore2", "anyio"):
        try:
            print(f"{package}:", importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            pass

    app = TakeTheClientAtItsWord(server.streamable_http_app())
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error")
    http_server = uvicorn.Server(config)
    server_task = asyncio.create_task(http_server.serve())
    try:
        for _ in range(200):
            if http_server.started:
                break
            await asyncio.sleep(0.05)
        if not http_server.started:
            raise RuntimeError("uvicorn did not start")

        port = http_server.servers[0].sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{port}/mcp"
        async with Client(url, mode="legacy") as client:
            result = await client.call_tool("echo", {"text": "hi"})
            text = result.content[0].text
            print("tools/call result:", text)
            await asyncio.sleep(1.0)

        if not seen_get_headers:
            raise AssertionError("legacy client never opened standalone GET stream")

        headers = seen_get_headers[0]
        print("GET accept:", headers.get("accept"))
        print("GET content-type:", headers.get("content-type"))
        assert "application/json" in headers.get("accept", "")
        assert "text/event-stream" in headers.get("accept", "")
        assert headers.get("content-type") == "application/json"
        assert text == "hi"
        print("RESULT: reproduced — GET offers application/json while the standalone channel is SSE-only, and Content-Type is sent on a bodyless GET")
        print("BOUNDARY: the wrapper deliberately returns JSON for GET to exercise the client's advertised representation; a compliant MCP server should return SSE or 405")
    finally:
        http_server.should_exit = True
        await server_task


asyncio.run(main())
