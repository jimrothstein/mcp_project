# hf-mcp

Learning project: a Python MCP **client** that connects to Hugging Face's
**remote** MCP server over the streamable HTTP transport — the same transport
opencode uses for a `"type": "remote"` MCP server.

Hugging Face hosts the server; there is no Python server here. The Python code
is the MCP client that speaks the MCP JSON-RPC protocol to
<https://huggingface.co/mcp>, authenticating with a Hugging Face access token.

## How it works

`hf_client.py` uses the official `mcp` Python SDK (v2):

- `httpx2.AsyncClient(headers={"Authorization": "Bearer <token>"}, ...)` — carries
  auth (and timeouts) for every request
- `streamable_http_client(url, http_client=http)` — opens the streamable HTTP
  transport and yields `(read, write)` streams
- `ClientSession(read, write)` — the MCP client: `initialize()`, `list_tools()`,
  `call_tool()`

The token is read from the `HF_TOKEN` environment variable — the same value
opencode injects via its `{env:HF_TOKEN}` substitution for the `huggingface`
remote server in `~/dotfiles/opencode/opencode.jsonc`.

## Tools exposed by the server

`hf_whoami`, `hub_repo_search`, `hub_repo_details`, `hf_fs` (extra tools can be
enabled on <https://huggingface.co/settings/mcp>).

## Run

Requires `uv`. `HF_TOKEN` must be set (create one at
<https://huggingface.co/settings/tokens>).

```sh
uv run python hf_client.py                                   # connect + list tools
uv run python hf_client.py whoami                            # call hf_whoami
uv run python hf_client.py call hub_repo_search '{"query":"qwen","limit":2}'
```
