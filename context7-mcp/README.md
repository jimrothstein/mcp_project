# context7-mcp

Learning project: a Python MCP **client** that connects to Context7's **local**
MCP server. Goal is to learn how MCP works — the client side, over stdio.

The Context7 MCP server itself is a Node.js package (`@upstash/context7-mcp`).
There is no Python server; the Python learning here is the MCP client code that
spawns it and speaks the MCP JSON-RPC protocol over stdin/stdout — the same
thing opencode/Claude/Cursor do for any "local" MCP server.

## How it works

`client.py` uses the official `mcp` Python SDK:

- `StdioServerParameters` — how to spawn the server (`npx -y @upstash/context7-mcp`)
- `stdio_client(...)` — launches the subprocess and bridges `(read, write)` streams
- `ClientSession(read, write)` — the MCP client: `initialize()`, `list_tools()`, `call_tool()`

## Run

Requires Node.js >= 18 (for `npx`) and uv.

```sh
uv run python client.py                      # connect + list tools
uv run python client.py resolve Flask "Flask routing setup"   # two-step docs fetch
uv run python client.py call resolve-library-id '{"libraryName":"Flask","query":"routing"}'
uv run python client.py call query-docs '{"libraryId":"/pallets/flask","query":"routing"}'
```

No API key is needed for anonymous use (rate-limited). To pass one, add
`"--api-key", "ctx7sk_..."` to `ARGS` in `client.py` or set the
`CONTEXT7_API_KEY` env var.