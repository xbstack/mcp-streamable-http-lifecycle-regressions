# MCP TypeScript SDK connection-lifecycle regression reproductions (XBSTACK)

**Independent tests run on macOS / Node v22.18.0, 2026-11-23.** Two distinct upstream failure modes; this is a minimal reproducible engineering artifact, not a new website article or a claim about all future SDK versions.

## Install isolated dependencies

```sh
npm install --ignore-scripts --no-audit --no-fund
node sse-repro.mjs
node stdio-repro.mjs
node stdio-cleanup-workaround.mjs
```

Pinned top-level packages: `@modelcontextprotocol/sdk@1.32.2`, `@modelcontextprotocol/client@2.4.0`, `@modelcontextprotocol/server@2.4.0`. Only local closed ports and local stdio child-process servers; no external MCP calls, credentials, payments or real tools.

## Verified results

- [typescript-sdk #3193](https://github.com/modelcontextprotocol/typescript-sdk/issues/3193): initial `Client.connect()` to an unreachable `127.0.0.1` legacy SSE endpoint rejects with `ECONNREFUSED`; the tested transport generated **2 additional errors in the next 7 seconds** and required explicit `await transport.close()` to stop. **This does not establish the same behavior in modern Streamable HTTP.**
- [typescript-sdk #3194](https://github.com/modelcontextprotocol/typescript-sdk/issues/3194): a local stdio server returned unsupported `protocolVersion: 1999-01-01`. `Client.connect()` rejected while the old transport remained attached; immediate reuse of the same `Client` with a new healthy stdio process rejected with `Connection closed`.
- **Tested workaround on the ordinary exiting-child branch, not all timing cases:** attach an `onclose` promise *before* `connect()`, wait for it after failure only when `client.transport === failedTransport`, then retry. On client 2.4.0 / Node 22.18.0, `stdio-cleanup-workaround.mjs` observed `closed: true` and `retry: resolved`, with `listTools() = {tools:[]}`. Credit for the approach belongs to the [original Issue reporter](https://github.com/modelcontextprotocol/typescript-sdk/issues/3194#issuecomment-6961113358). We have **not tested a child that ignores EOF/SIGTERM or delayed SIGKILL callbacks**; that case may require deeper protocol-identity fencing.

## Evidence boundary

Do not copy a proposed epoch-fence wrapper from the comment thread without reproducing it: the reporter already found one publicly proposed implementation ineffective on 1.32.2 and 2.4.0. Avoid claiming that an upstream fix has shipped unless its release and tests are verified.

Related XBSTACK article, updated with these cases:
- [English MCP deployment/lifecycle guide](https://www.xbstack.com/en/ai/mcp-streamable-http-deployment/?utm_source=github&utm_medium=referral&utm_campaign=mcp_ts_transport_lifecycle&utm_content=repro_readme)
- [中文 MCP 部署与生命周期](https://www.xbstack.com/ai/mcp-streamable-http-deployment/?utm_source=github&utm_medium=referral&utm_campaign=mcp_ts_transport_lifecycle&utm_content=repro_readme_zh)

License: MIT (repository root).
