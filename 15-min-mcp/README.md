# 15-min-mcp

An MCP server that searches local markdown notes (`*.md`).

Built with [FastMCP](https://github.com/jlowin/fastmcp) (Python).

## Tools

- `search_notes(query)` — case-insensitive keyword search over notes; returns matching filenames with a snippet of the first matching line.

## Notes location

Notes are read from `~/code/docs/tech_notes/` by default. Override with the `NOTES_DIR` environment variable:

```bash
NOTES_DIR=/path/to/notes 15-min-mcp
```

## Run

```bash
uv run 15-min-mcp          # via console script
uv run python server.py    # or via the root wrapper
```

Test interactively with the MCP Inspector:

```bash
uvx mcp dev server.py
```