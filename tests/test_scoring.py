from datetime import datetime, timezone

from lead_radar.models import RawPost, SourcesConfig, RedditSourceConfig, TopicConfig
from lead_radar.scoring import score_post, score_posts


def make_topic() -> TopicConfig:
    return TopicConfig(
        name="test",
        sources=SourcesConfig(reddit=RedditSourceConfig(subreddits=["n8n"])),
        keywords=["need automation", "n8n"],
        include_phrases=["willing to pay", "looking for help"],
        exclude_phrases=["course", "affiliate"],
        output_top_n=5,
    )


def test_strong_buying_signal_scores_high() -> None:
    topic = make_topic()
    post = RawPost(
        source="reddit",
        source_id="1",
        url="https://example.com/1",
        title="Need automation help with n8n",
        body="I am willing to pay someone to automate this manual process.",
        community="n8n",
        created_at=datetime.now(timezone.utc),
        upvotes=10,
        num_comments=5,
    )

    signal = score_post(post, topic)

    assert signal.score > 10
    assert signal.buying_intent == "strong"
    assert "buying_intent" in signal.tags


def test_excluded_promotional_post_is_penalized() -> None:
    topic = make_topic()
    post = RawPost(
        source="reddit",
        source_id="2",
        url="https://example.com/2",
        title="My n8n course",
        body="Affiliate course for automation.",
        community="n8n",
        created_at=datetime.now(timezone.utc),
        upvotes=100,
        num_comments=20,
    )

    signals = score_posts([post], topic)

    assert signals == [] or signals[0].score < 5
