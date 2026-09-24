# Version matrix

| Check | Environment | Version | Result |
| --- | --- | --- | --- |
| #3494 repeated fresh server initialize | macOS 26.6.2 arm64, unconstrained host | Python 3.13.15; FastMCP 4.0.3; mcp 2.2.0; uvicorn 0.52.4; httpx 0.28.1; anyio 4.14.2 | **17/20 failed** with incomplete ASGI response / RemoteProtocolError |
| #3503 standalone GET Accept / Content-Type | macOS 26.6.2 arm64 | Python 3.14.7; mcp 2.2.0; uvicorn 0.52.4; httpx2 2.13.1 | **reproduced**; GET advertises JSON+SSE and sends application/json Content-Type, while tool call still succeeds |

## Scope

- #3494: XBSTACK did not run the upstream Linux `--cpus=1` container because Docker is unavailable locally. The same reported failure shape nevertheless reproduced on the host after repeated fresh servers.
- #3503: the test server intentionally honors the client's JSON offer on GET. This is a diagnostic probe of the client contract; a compliant MCP server should return SSE or 405.
