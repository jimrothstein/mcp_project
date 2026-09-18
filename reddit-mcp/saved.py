#!/usr/bin/env python3
"""List, search, and manage your saved Reddit posts via PRAW.

Credentials: create a script app at https://www.reddit.com/prefs/apps and
provide them via environment variables or a .env file:
    REDDIT_CLIENT_ID=...
    REDDIT_CLIENT_SECRET=...
    REDDIT_USERNAME=...
    REDDIT_PASSWORD=...
    REDDIT_USER_AGENT=myscript/0.1 by yourusername

Usage:
    python saved.py list [--keyword mcp] [--limit 100] [--json]
    python saved.py delete KEYWORD [--yes]
    python saved.py delete-ids ID1 ID2 ... [--yes]
"""

import argparse
import json
import os

import praw
from dotenv import load_dotenv

load_dotenv()


def get_reddit():
    return praw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID"),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
        username=os.environ.get("REDDIT_USERNAME"),
        password=os.environ.get("REDDIT_PASSWORD"),
        user_agent=os.environ.get(
            "REDDIT_USER_AGENT", "saved.py by %s" % os.environ.get("REDDIT_USERNAME", "unknown")
        ),
    )


def iter_saved_posts(reddit, keyword=None, limit=None):
    """Yield saved submissions (skipping saved comments), optional keyword filter."""
    for item in reddit.user.me().saved(limit=limit):
        post = item if isinstance(item, praw.models.Submission) else item.submission
        haystack = " ".join(
            [post.title or "", post.selftext or "", str(post.subreddit or "")]
        ).lower()
        if keyword is None or keyword.lower() in haystack:
            yield post


def to_dict(post):
    return {
        "id": post.id,
        "title": post.title,
        "subreddit": str(post.subreddit),
        "url": post.url,
        "permalink": post.permalink,
        "created_utc": post.created_utc,
    }


def cmd_list(args):
    reddit = get_reddit()
    posts = list(iter_saved_posts(reddit, keyword=args.keyword, limit=args.limit))
    if args.json:
        print(json.dumps([to_dict(p) for p in posts], indent=2))
        return
    for i, p in enumerate(posts, 1):
        print(f"{i:4}. [{p.subreddit}] {p.title}\n      {p.url}")
    print(f"\n{len(posts)} saved post(s)")


def cmd_delete(args):
    reddit = get_reddit()
    targets = list(iter_saved_posts(reddit, keyword=args.keyword))
    if not targets:
        print("Nothing matched.")
        return
    for p in targets:
        print(f"[{p.subreddit}] {p.title}\n    {p.url}")
    if not args.yes:
        confirm = input(f"Unsaved {len(targets)} post(s)? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return
    for p in targets:
        p.unsave()
    print(f"Unsaved {len(targets)} post(s).")


def cmd_delete_ids(args):
    reddit = get_reddit()
    for pid in args.ids:
        sub = reddit.submission(id=pid)
        sub.unsave()
        print(f"Unsaved {pid}: {sub.title}")
    print(f"Unsaved {len(args.ids)} post(s).")


def main():
    parser = argparse.ArgumentParser(description="Manage saved Reddit posts.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list saved posts")
    p_list.add_argument("--keyword", help="only posts whose text mentions this keyword")
    p_list.add_argument("--limit", type=int, help="max posts to scan (default: all)")
    p_list.add_argument("--json", action="store_true", help="output as JSON")
    p_list.set_defaults(func=cmd_list)

    p_del = sub.add_parser("delete", help="unsave posts matching a keyword")
    p_del.add_argument("keyword", help="keyword matching posts to unsave")
    p_del.add_argument("--yes", action="store_true", help="skip confirmation")
    p_del.set_defaults(func=cmd_delete)

    p_delids = sub.add_parser("delete-ids", help="unsave specific posts by id")
    p_delids.add_argument("ids", nargs="+", help="post ids (t3_ prefix optional)")
    p_delids.add_argument("--yes", action="store_true", help="skip confirmation")
    p_delids.set_defaults(func=cmd_delete_ids)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()