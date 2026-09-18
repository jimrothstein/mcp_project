#!/usr/bin/env python3
"""List and search your saved Reddit posts via your private saved-links RSS feed.

No Reddit API app or registration needed. Get the feed URL from
reddit.com/prefs/feeds/ -> "your saved links". Treat that URL like a password.

Provide it via an env var or .env file:
    REDDIT_SAVED_RSS_URL=https://www.reddit.com/user/NAME/saved.rss?feed=TOKEN&user=NAME

Read-only: the RSS feed cannot unsave/delete posts (~100 most recent items only).

Usage:
    python saved.py list [--keyword mcp] [--limit 100] [--json]
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request

import feedparser
from dotenv import load_dotenv

load_dotenv()

SUBRE_SRC = re.compile(r"reddit\.com/r/([\w]+)/comments/([\w]+)")
SUBRE_ID = re.compile(r"post/([\w]+)")


def fetch_entries(feed_url):
    req = urllib.request.Request(feed_url, headers={"User-Agent": "saved.py/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return feedparser.parse(resp.read()).entries


def parse_entry(entry):
    title = getattr(entry, "title", "")
    link = getattr(entry, "link", "")
    html = " ".join(getattr(c, "value", "") for c in getattr(entry, "content", []))
    m = SUBRE_SRC.search(link) or SUBRE_SRC.search(html)
    subreddit = m.group(1) if m else ""
    m2 = SUBRE_SRC.search(link) or SUBRE_SRC.search(html)
    post_id = m2.group(2) if m2 else (SUBRE_ID.search(getattr(entry, "id", "")) or [None, ""])[1]
    published = (
        entry.published_parsed if getattr(entry, "published_parsed", None) else None
    ) or (entry.updated_parsed if getattr(entry, "updated_parsed", None) else None)
    return {
        "id": post_id,
        "title": title,
        "subreddit": subreddit,
        "url": link,
        "published_utc": time.mktime(published) if published else None,
    }


def load_posts():
    feed_url = os.environ.get("REDDIT_SAVED_RSS_URL")
    if not feed_url:
        print("Error: set REDDIT_SAVED_RSS_URL (from reddit.com/prefs/feeds/).", file=sys.stderr)
        raise SystemExit(1)
    if not feed_url.startswith("https://www.reddit.com"):
        print("Error: feed URL must be a reddit.com address.", file=sys.stderr)
        raise SystemExit(1)
    posts = [parse_entry(e) for e in fetch_entries(feed_url)]
    posts.sort(key=lambda p: p["published_utc"] or 0, reverse=True)
    return posts


def cmd_list(args):
    posts = load_posts()
    if args.keyword:
        kw = args.keyword.lower()
        posts = [
            p
            for p in posts
            if kw in " ".join([p["title"], p["subreddit"]]).lower()
        ]
    if args.limit:
        posts = posts[: args.limit]
    if args.json:
        print(json.dumps(posts, indent=2))
        return
    for i, p in enumerate(posts, 1):
        extra = f" [{p['id']}]" if p["id"] else ""
        print(f"{i:4}. [{p['subreddit']}] {p['title']}{extra}\n      {p['url']}")
    print(f"\n{len(posts)} saved post(s)")


def main():
    parser = argparse.ArgumentParser(description="List/search saved Reddit posts (RSS).")
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