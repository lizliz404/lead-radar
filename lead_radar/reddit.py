from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx

from lead_radar.models import RawPost, TopicConfig


class RedditClient:
    """Minimal Reddit OAuth client for read-only search.

    This client intentionally stays small. It is enough for MVP validation and keeps the
    data-source boundary explicit so we can replace it with PRAW or another adapter later.
    """

    token_url = "https://www.reddit.com/api/v1/access_token"
    api_base = "https://oauth.reddit.com"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.getenv("REDDIT_USER_AGENT") or "lead-radar/0.1"
        self.timeout = timeout
        self._access_token: str | None = None

    def _require_credentials(self) -> None:
        missing = [
            key
            for key, value in {
                "REDDIT_CLIENT_ID": self.client_id,
                "REDDIT_CLIENT_SECRET": self.client_secret,
            }.items()
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Missing Reddit credentials: {joined}. Use --mock for local testing.")

    def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        self._require_credentials()
        assert self.client_id is not None
        assert self.client_secret is not None

        with httpx.Client(timeout=self.timeout, headers={"User-Agent": self.user_agent}) as client:
            response = client.post(
                self.token_url,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
            )
            response.raise_for_status()
            payload = response.json()

        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Reddit OAuth response did not include access_token")

        self._access_token = token
        return token

    def search_topic(self, topic: TopicConfig) -> list[RawPost]:
        if not topic.sources.reddit:
            return []

        since = datetime.now(timezone.utc) - timedelta(hours=topic.lookback_hours)
        seen: set[str] = set()
        posts: list[RawPost] = []

        for subreddit in topic.sources.reddit.subreddits:
            for keyword in topic.keywords:
                for post in self.search_subreddit(
                    subreddit=subreddit,
                    query=keyword,
                    limit=topic.max_posts_per_source,
                ):
                    if post.source_id in seen:
                        continue
                    if post.created_at < since:
                        continue
                    seen.add(post.source_id)
                    posts.append(post)

        return posts

    def search_subreddit(self, subreddit: str, query: str, limit: int = 25) -> list[RawPost]:
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent,
        }
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "new",
            "t": "week",
            "limit": min(limit, 100),
        }

        url = f"{self.api_base}/r/{subreddit}/search"
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        children = payload.get("data", {}).get("children", [])
        posts: list[RawPost] = []
        for child in children:
            data = child.get("data", {})
            permalink = data.get("permalink") or ""
            full_url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink
            source_id = data.get("id") or data.get("name")
            if not source_id:
                continue
            posts.append(
                RawPost(
                    source="reddit",
                    source_id=str(source_id),
                    url=full_url,
                    title=data.get("title") or "",
                    body=data.get("selftext") or "",
                    author=data.get("author"),
                    community=data.get("subreddit") or subreddit,
                    created_at=float(data.get("created_utc") or 0),
                    upvotes=int(data.get("ups") or data.get("score") or 0),
                    num_comments=int(data.get("num_comments") or 0),
                    raw=data,
                )
            )
        return posts
