from functools import cache
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from mcp.server import MCPServer

BASE = Path(__file__).parent
TOKEN = BASE / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

mcp = MCPServer("gmail-organizer")

@cache
def gmail():
    if not TOKEN.exists():
        raise RuntimeError(
            "token.json not found. Run `auth_gmail.py` in the gmail-mcp "
            "project to authorize Gmail, then restart opencode."
        )
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as exc:
            raise RuntimeError(
                "Gmail token refresh failed. Run `auth_gmail.py` in the "
                f"gmail-mcp project to re-authorize. ({exc})"
            ) from None
        TOKEN.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

@mcp.tool()
def search_messages(query: str, max_results: int = 20) -> list[dict[str, Any]]:
    """Search Gmail. This tool makes no changes."""
    service = gmail()
    response = service.users().messages().list(
        userId="me", q=query, maxResults=min(max_results, 100)
    ).execute()

    ids = [item["id"] for item in response.get("messages", [])]
    if not ids:
        return []

    batch = service.new_batch_http_request()
    fetched: dict[str, dict[str, Any]] = {}
    def callback(request_id, resp, exception):
        if exception is None:
            fetched[resp["id"]] = resp
    for mid in ids:
        batch.add(
            service.users().messages().get(
                userId="me",
                id=mid,
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ),
            callback=callback,
        )
    batch.execute()

    results = []
    for mid in ids:
        message = fetched.get(mid)
        if message is None:
            continue
        headers = {
            h["name"].lower(): h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }
        results.append({
            "id": message["id"],
            "thread_id": message["threadId"],
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "labels": message.get("labelIds", []),
            "snippet": message.get("snippet", ""),
        })
    return results

@mcp.tool()
def list_labels() -> list[dict[str, str]]:
    """List Gmail labels. This tool makes no changes."""
    service = gmail()
    labels = service.users().labels().list(userId="me").execute()
    return [
        {"id": label["id"], "name": label["name"]}
        for label in labels.get("labels", [])
    ]

if __name__ == "__main__":
    mcp.run()
