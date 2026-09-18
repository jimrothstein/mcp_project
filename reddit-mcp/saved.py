#!/usr/bin/env python3
"""List and search your saved Reddit posts via your private saved feed (JSON).

No Reddit API app or registration needed. In reddit.com/prefs/feeds/, the
"Saved Links" row has both RSS and JSON buttons; either link works because
they carry the same private feed token. This script uses the JSON variant
(richer fields, no XML parsing).

Provide the link via env var or .env file:
    REDDIT_SAVED_RSS_URL=https://www.reddit.com/user/NAME/saved.rss?feed=TOKEN&user=NAME
    (or REDDIT_SAVED_JSON_URL=.../saved.json?feed=TOKEN&user=NAME)

Treat the feed URL like a password.

Read-only: feeds cannot unsave/delete (~25-100 most recent items only).

Usage:
    python saved.py list [--keyword mcp] [--limit 100] [--json]
"""

import argparse
import datetime
import json
import os
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv()

FEED_KEYS = ("id", "title", "subreddit", "url", "permalink", "created_utc")


def feed_url():
    url = os.environ.get("REDDIT_SAVED_JSON_URL") or os.environ.get("REDDIT_SAVED_RSS_URL")
    if not url:
        print("Error: set REDDIT_SAVED_RSS_URL (from reddit.com/prefs/feeds/).", file=sys.stderr)
        raise SystemExit(1)
    if not url.startswith("https://www.reddit.com"):
        print("Error: feed URL must be a reddit.com address.", file=sys.stderr)
        raise SystemExit(1)
    return url.replace(".rss?", ".json?")


def request_headers():
    headers = {"User-Agent": "saved.py/0.1", "Accept": "application/json"}
    session = os.environ.get("REDDIT_SESSION_COOKIE")
    if session:
        headers["Cookie"] = "reddit_session=%s" % session
    return headers


def fetch_posts():
    req = urllib.request.Request(feed_url(), headers=request_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    children = payload.get("data", {}).get("children", [])
    posts = []
    for child in children:
        if child.get("kind") != "t3":
            continue
        data = child.get("data", {})
        posts.append({k: data.get(k) for k in FEED_KEYS})
    posts.sort(key=lambda p: p.get("created_utc") or 0, reverse=True)
    return posts


def cmd_list(args):
    posts = fetch_posts()
    if args.keyword:
        kw = args.keyword.lower()
        posts = [p for p in posts if kw in " ".join(
            [str(p.get("title", "")), str(p.get("subreddit", ""))]
        ).lower()]
    if args.limit:
        posts = posts[: args.limit]
    if args.json:
        print(json.dumps(posts, indent=2))
        return
    for i, p in enumerate(posts, 1):
        permalink = "https://www.reddit.com" + p["permalink"] if p["permalink"].startswith("/") else p["permalink"]
        when = datetime.datetime.fromtimestamp(p["created_utc"]).strftime("%Y-%m-%d") if p["created_utc"] else "?"
        print(f"{i:4}. [{p['subreddit']}] {p['title']}")
        print(f"      saved {when}  (id {p['id']})")
        print(f"      {permalink}")
        if p["url"]:
            print(f"      content: {p['url']}")
    print(f"\n{len(posts)} saved post(s)")


def main():
    parser = argparse.ArgumentParser(description="List/search saved Reddit posts (JSON feed).")
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list", help="list saved posts")
    p_list.add_argument("--keyword", help="only posts whose title/subreddit mentions this keyword")
    p_list.add_argument("--limit", type=int, help="max posts to show (default: all)")
    p_list.add_argument("--json", action="store_true", help="output as JSON")
    p_list.set_defaults(func=cmd_list)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()