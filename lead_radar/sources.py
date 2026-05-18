from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

import httpx

from lead_radar.models import RawPost, TopicConfig
from lead_radar.reddit import RedditClient


class SourceAdapter(Protocol):
    """Fetch normalized public discussion posts for one topic."""

    def search_topic(self, topic: TopicConfig) -> list[RawPost]: ...


class HackerNewsClient:
    """Hacker News adapter backed by Algolia's public search API."""

    api_base = "https://hn.algolia.com/api/v1"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def search_topic(self, topic: TopicConfig) -> list[RawPost]:
        if not topic.sources.hacker_news or not topic.sources.hacker_news.enabled:
            return []

        since = datetime.now(timezone.utc) - timedelta(hours=topic.lookback_hours)
        since_timestamp = int(since.timestamp())
        seen: set[str] = set()
        posts: list[RawPost] = []

        for keyword in topic.keywords:
            for post in self.search(
                query=keyword,
                tags=topic.sources.hacker_news.tags,
                numeric_filters=f"created_at_i>{since_timestamp}",
                limit=topic.max_posts_per_source,
            ):
                if post.source_id in seen:
                    continue
                seen.add(post.source_id)
                posts.append(post)

        return posts

    def search(
        self,
        *,
        query: str,
        tags: str = "story,comment",
        numeric_filters: str | None = None,
        limit: int = 25,
    ) -> list[RawPost]:
        params: dict[str, str | int] = {
            "query": query,
            "tags": tags,
            "hitsPerPage": min(limit, 100),
        }
        if numeric_filters:
            params["numericFilters"] = numeric_filters

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.api_base}/search_by_date", params=params)
            response.raise_for_status()
            payload = response.json()

        hits = payload.get("hits", [])
        if not isinstance(hits, list):
            return []

        posts: list[RawPost] = []
        for hit in hits:
            post = self._hit_to_post(hit)
            if post:
                posts.append(post)
        return posts

    def _hit_to_post(self, hit: dict) -> RawPost | None:
        object_id = hit.get("objectID")
        if not object_id:
            return None

        title = hit.get("title") or hit.get("story_title") or hit.get("comment_text") or ""
        body = hit.get("comment_text") or hit.get("story_text") or ""
        points = int(hit.get("points") or 0)
        comments = int(hit.get("num_comments") or 0)
        created_at = hit.get("created_at") or hit.get("created_at_i") or 0
        item_url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
        community = "hacker_news"
        if hit.get("_tags"):
            community = "hacker_news:" + ",".join(str(tag) for tag in hit.get("_tags", [])[:3])

        return RawPost(
            source="hacker_news",
            source_id=str(object_id),
            url=item_url,
            title=strip_html(title),
            body=strip_html(body),
            author=hit.get("author"),
            community=community,
            created_at=created_at,
            upvotes=points,
            num_comments=comments,
            raw=hit,
        )


def fetch_topic_posts(topic: TopicConfig) -> list[RawPost]:
    """Fetch posts from every configured source for a topic."""

    posts: list[RawPost] = []
    for adapter in build_source_adapters(topic):
        posts.extend(adapter.search_topic(topic))
    return deduplicate_posts(posts)


def build_source_adapters(topic: TopicConfig) -> list[SourceAdapter]:
    adapters: list[SourceAdapter] = []
    if topic.sources.reddit:
        adapters.append(RedditClient())
    if topic.sources.hacker_news and topic.sources.hacker_news.enabled:
        adapters.append(HackerNewsClient())
    return adapters


def deduplicate_posts(posts: list[RawPost]) -> list[RawPost]:
    seen: set[tuple[str, str]] = set()
    unique: list[RawPost] = []
    for post in posts:
        key = (post.source, post.source_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(post)
    return unique


def strip_html(value: str) -> str:
    return (
        value.replace("<p>", "\n")
        .replace("</p>", "\n")
        .replace("<pre>", "\n")
        .replace("</pre>", "\n")
        .replace("<code>", "`")
        .replace("</code>", "`")
        .replace("&#x27;", "'")
        .replace("&quot;", '"')
        .replace("&amp;", "&")
        .strip()
    )
