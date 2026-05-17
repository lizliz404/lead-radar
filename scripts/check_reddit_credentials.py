#!/usr/bin/env python3
"""Minimal Reddit API credential check.

Run this after filling in .env to verify Reddit OAuth works before running
a full scan. It requests a token and does one lightweight search.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    load_dotenv()

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    missing = []
    if not client_id:
        missing.append("REDDIT_CLIENT_ID")
    if not client_secret:
        missing.append("REDDIT_CLIENT_SECRET")
    if not user_agent:
        missing.append("REDDIT_USER_AGENT")

    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your Reddit app credentials.")
        return 1

    from lead_radar.reddit import RedditClient

    print(f"Client ID: {client_id[:4]}...")
    print(f"User agent: {user_agent}")
    print("Requesting access token...")

    client = RedditClient(client_id=client_id, client_secret=client_secret, user_agent=user_agent)

    try:
        token = client.get_access_token()
        print(f"Token received: {token[:8]}...")
    except Exception as exc:
        print(f"Failed to get token: {exc}")
        return 1

    print("Running test search in r/shopify for 'inventory'...")
    try:
        posts = client.search_subreddit("shopify", "inventory", limit=3)
        print(f"Found {len(posts)} post(s)")
        for p in posts:
            print(f"  - [{p.community}] {p.title[:60]}...")
        return 0
    except Exception as exc:
        print(f"Search failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
