# MCP Streamable HTTP lifecycle regression checks

XBSTACK local verification for three MCP Python SDK transport/lifecycle issues:

- modelcontextprotocol/python-sdk#3494: Streamable HTTP SSE response can terminate before the final ASGI body chunk under repeated server restarts / contention.
- modelcontextprotocol/python-sdk#3503: legacy standalone GET advertises `application/json, text/event-stream` even though the client reads it only as SSE; bodyless GET/DELETE also inherit `Content-Type: application/json`.
- modelcontextprotocol/python-sdk#3556: a request carrying a stale `Mcp-Session-Id` receives HTTP 404, but the client returns `Session terminated`, retains the stale session id, and does not automatically initialize a new session.

These fixtures do not create a new XBSTACK article. They are versioned evidence for the existing MCP Streamable HTTP deployment guide.

## XBSTACK results

Tested on macOS 26.6.2 arm64.

| Issue | Environment | Result |
| --- | --- | --- |
| #3494 | Python 3.13.15, FastMCP 4.0.3, mcp 2.2.0, uvicorn 0.52.4, httpx 0.28.1, anyio 4.14.2 | **reproduced: 17/20** fresh-server initialize POSTs failed with `ASGI callable returned without completing response` and `RemoteProtocolError: peer closed connection without sending complete message body` |
| #3503 | Python 3.14.7, mcp 2.2.0, uvicorn 0.52.4, httpx2 2.13.1 | **reproduced:** legacy standalone GET sent `Accept: application/json, text/event-stream` plus `Content-Type: application/json`; the wrapper returned JSON, the GET stream disconnected/retried, while `tools/call` still returned `hi` |
| #3556 | Python 3.11.15, mcp 1.28.1 | **reproduced:** two simulated stale-session 404 responses both produced `Session terminated`; the transport kept `stale-session-xbstack`, sent it again, and emitted no `initialize` |
| #3556 | Python 3.14.7, mcp 2.2.0 | **reproduced:** same transport-level result on the current 2.x line; stale id remained installed across two 404s and no `initialize` was emitted |

For #3494, Docker is not installed in this workspace, so XBSTACK did not reproduce the upstream Linux `--cpus=1` container condition. The important result is narrower: the same failure shape reproduced on an unconstrained macOS arm64 host after repeated fresh uvicorn server starts.

For #3503, the wrapper deliberately returns JSON for GET to exercise a representation the client advertised. A compliant MCP server should return SSE or 405, so the supported conclusion is about the client's request headers and silent channel loss—not that compliant servers normally return JSON.

For #3556, the fixture deliberately isolates the client's 404 recovery branch with a deterministic fake HTTP client. It proves that the tested SDK versions retain and reuse the stale session id and do not issue a replacement `InitializeRequest` on that branch. It does not claim to reproduce every proxy, deploy, idle-timeout, or server-restart timing condition.

## Run

```bash
uv run --python 3.13 --with "fastmcp==4.0.3" --with "uvicorn==0.52.4" --with "httpx==0.28.1" --with "anyio==4.14.2" python repro/asgi_incomplete_response.py
uv run --python 3.14 --with "mcp==2.2.0" --with "uvicorn==0.52.4" python repro/client_get_accept_mismatch.py
uv run --python 3.11 --with "mcp==1.28.1" python repro/session_404_reinitialize.py
uv run --python 3.14 --with "mcp==2.2.0" python repro/session_404_reinitialize.py
```

Outputs are captured under `logs/`.

## References

- https://github.com/modelcontextprotocol/python-sdk/issues/3494
- https://github.com/modelcontextprotocol/python-sdk/issues/3503
- https://github.com/modelcontextprotocol/python-sdk/issues/3556
- https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/streamable_http.py
- https://github.com/modelcontextprotocol/python-sdk/blob/main/tests/shared/test_streamable_http.py

## Related XBSTACK guide

- English: https://www.xbstack.com/en/ai/mcp-streamable-http-deployment/?utm_source=github&utm_medium=referral&utm_campaign=mcp_streamable_http_lifecycle&utm_content=repository_readme&ref=github
- Chinese: https://www.xbstack.com/ai/mcp-streamable-http-deployment/?utm_source=github&utm_medium=referral&utm_campaign=mcp_streamable_http_lifecycle&utm_content=repository_readme_zh&ref=github

## License

MIT
