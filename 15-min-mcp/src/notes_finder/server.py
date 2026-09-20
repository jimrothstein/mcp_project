import os
from pathlib import Path

from fastmcp import FastMCP

NOTES_DIR = Path(os.environ.get("NOTES_DIR", Path.home() / "notes"))

mcp = FastMCP("15-min-mcp", version="0.1.0")

MAX_RESULTS = 10
SNIPPET_CHARS = 200


@mcp.tool()
def search_notes(query: str) -> str:
    """Search local markdown notes for a case-insensitive keyword.

    Returns the matching note filenames with a short snippet from each.
    Notes are expected to be *.md files inside the notes directory.
    """
    query = query.lower()
    if not NOTES_DIR.is_dir():
        return f"Notes directory not found: {NOTES_DIR}"

    results = []
    for f in sorted(NOTES_DIR.glob("*.md")):
        content = f.read_text(errors="replace")
        if query in content.lower():
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if query in line.lower():
                    results.append(f"**{f.name}**\n{line[:SNIPPET_CHARS]}")
                    break
    if not results:
        return f"No notes found matching '{query}'"
    total = len(results)
    if total > MAX_RESULTS:
        results = results[:MAX_RESULTS]
        results.append(f"\n... and {total - MAX_RESULTS} more matches")
    return "\n\n".join(results)