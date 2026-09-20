#!/usr/bin/env python3

from fastmcp import FastMCP
from pathlib import Path

mcp = FastMCP("Local Notes Search")

NOTES_DIR = Path.home() / "notes"

@mcp.tool()
def search_notes(query: str) -> str:
    """Search through local notes files for a keyword."""
    results = []
    for f in NOTES_DIR.glob("*.md"):
        content = f.read_text()
        if query.lower() in content.lower():
            results.append(f"**{f.name}**\n{content[:200]}")
    if not results:
        return f"No notes found matching '{query}'"
    return "\n\n".join(results)
