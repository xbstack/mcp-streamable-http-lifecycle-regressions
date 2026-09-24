"""Host-side control for modelcontextprotocol/python-sdk#3494.

The upstream reproduction is strongest in a Linux container constrained to one CPU.
This script intentionally runs the same repeated-server pattern on the current host
and reports the result without treating a negative host result as a refutation.
"""

import importlib.metadata
import platform

import anyio
import httpx
import uvicorn
from fastmcp import FastMCP

mcp = FastMCP("repro")


@mcp.tool()
def echo(message: str) -> str:
    return message


INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "xbstack-repro", "version": "1"},
    },
}
HEADERS = {"Accept": "application/json, text/event-stream"}


async def one_attempt() -> str | None:
    config = uvicorn.Config(
        mcp.http_app(transport="streamable-http"),
        host="127.0.0.1",
        port=0,
        log_level="error",
    )
    server = uvicorn.Server(config)
    async with anyio.create_task_group() as tg:
        tg.start_soon(server.serve)
        with anyio.fail_after(10):
            while not server.started:
                await anyio.sleep(0.05)
        port = server.servers[0].sockets[0].getsockname()[1]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"http://127.0.0.1:{port}/mcp",
                    json=INIT,
                    headers=HEADERS,
                )
                response.raise_for_status()
        except (httpx.HTTPError, RuntimeError) as error:
            return f"{type(error).__name__}: {error}"
        finally:
            server.should_exit = True
    return None


async def main() -> None:
    print("platform:", platform.platform())
    print("python:", platform.python_version())
    for package in ("fastmcp", "mcp", "uvicorn", "httpx", "anyio"):
        try:
            print(f"{package}:", importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            pass

    failures = 0
    attempts = 20
    for attempt in range(attempts):
        error = await one_attempt()
        if error is not None:
            failures += 1
            print(f"attempt {attempt}: {error}")
    print(f"RESULT: {failures}/{attempts} initialize POSTs failed")
    if failures == 0:
        print("BOUNDARY: not reproduced on this unconstrained macOS host; upstream Linux 1-CPU stress condition was not available")
    else:
        print("BOUNDARY: reproduced on this host; compare failure shape with upstream before generalizing")


anyio.run(main)
