## simple mcp server;  deploy to posit connect

import os
from urllib.parse import urlparse

from fastmcp import FastMCP

mcp = FastMCP("Hello MCP")


@mcp.tool()
def hello() -> str:
    """Return a simple greeting."""
    return "Hello"


allowed_hosts = []
connect_server = os.environ.get("CONNECT_SERVER", "")

if connect_server:
    parsed = urlparse(connect_server)
    host = parsed.hostname or (
        (parsed.netloc or parsed.path).rstrip("/").split(":")[0]
    )
    if host:
        allowed_hosts.append(host)

app = mcp.http_app(
    stateless_http=True,
    json_response=True,
    host_origin_protection=True,
    allowed_hosts=allowed_hosts,
)