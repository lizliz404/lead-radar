from datetime import datetime, timezone

from lead_radar.models import RawPost, TopicConfig
from lead_radar.sources import HackerNewsClient, deduplicate_posts, strip_html


def test_hacker_news_hit_to_post_normalizes_algolia_hit() -> None:
    client = HackerNewsClient()
    post = client._hit_to_post(
        {
            "objectID": "123",
            "title": "Need automation help",
            "comment_text": "Manual work is <p>too much</p> &amp; expensive",
            "author": "pg",
            "created_at": "2026-05-17T00:00:00Z",
            "points": 42,
            "num_comments": 7,
            "_tags": ["story", "author_pg"],
        }
    )

    assert post is not None
    assert post.source == "hacker_news"
    assert post.source_id == "123"
    assert post.community == "hacker_news:story,author_pg"
    assert post.url == "https://news.ycombinator.com/item?id=123"
    assert post.upvotes == 42
    assert post.num_comments == 7
    assert "Manual work" in post.body


def test_hacker_news_search_topic_skips_when_disabled() -> None:
    topic = TopicConfig(
        name="disabled_hn",
        sources={"hacker_news": {"enabled": False}},
        keywords=["automation"],
    )

    assert HackerNewsClient().search_topic(topic) == []


def test_deduplicate_posts_uses_source_and_source_id() -> None:
    created_at = datetime.now(timezone.utc)
    posts = [
        {
            "source": "reddit",
            "source_id": "1",
            "url": "https://reddit.test/1",
            "title": "same id different source",
            "created_at": created_at,
        },
        {
            "source": "hacker_news",
            "source_id": "1",
            "url": "https://news.ycombinator.com/item?id=1",
            "title": "same id different source",
            "created_at": created_at,
        },
        {
            "source": "hacker_news",
            "source_id": "1",
            "url": "https://news.ycombinator.com/item?id=1",
            "title": "duplicate",
            "created_at": created_at,
        },
    ]

    unique = deduplicate_posts([RawPost.model_validate(item) for item in posts])

    assert [(post.source, post.source_id) for post in unique] == [("reddit", "1"), ("hacker_news", "1")]


def test_strip_html_handles_common_algolia_entities() -> None:
    assert strip_html("A &amp; B &quot;C&#x27;s&quot;<p>next</p>") == 'A & B "C\'s"\nnext'
