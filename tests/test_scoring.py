from datetime import datetime, timezone

from lead_radar.models import RawPost, SourcesConfig, RedditSourceConfig, TopicConfig
from lead_radar.scoring import score_post, score_posts


def make_topic() -> TopicConfig:
    return TopicConfig(
        name="test",
        sources=SourcesConfig(reddit=RedditSourceConfig(subreddits=["automation"])),
        keywords=["need automation", "workflow"],
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
        title="Need automation help with onboarding workflow",
        body="I am willing to pay someone to automate this manual process.",
        community="automation",
        created_at=datetime.now(timezone.utc),
        upvotes=10,
        num_comments=5,
    )

    signal = score_post(post, topic)

    assert signal.score > 10
    assert signal.signal_strength == "strong"
    assert signal.buying_intent == "strong"
    assert "buying_intent" in signal.tags


def test_excluded_promotional_post_is_penalized() -> None:
    topic = make_topic()
    post = RawPost(
        source="reddit",
        source_id="2",
        url="https://example.com/2",
        title="My automation course",
        body="Affiliate course for automation.",
        community="automation",
        created_at=datetime.now(timezone.utc),
        upvotes=100,
        num_comments=20,
    )

    signals = score_posts([post], topic)

    assert signals == [] or signals[0].score < 5


def test_idea_profile_scores_idea_signals_without_buying_language() -> None:
    topic = TopicConfig(
        name="idea_test",
        intent_profile="idea",
        keywords=["is there a tool"],
        include_phrases=["i wish there was"],
        output_top_n=5,
    )
    post = RawPost(
        source="reddit",
        source_id="3",
        url="https://example.com/3",
        title="Is there a tool for messy client handoff notes?",
        body="I wish there was something less manual. Current tools are frustrating and limited.",
        community="SaaS",
        created_at=datetime.now(timezone.utc),
        upvotes=3,
        num_comments=2,
    )

    signal = score_post(post, topic)

    assert signal.score > 8
    assert signal.signal_strength == "strong"
    assert "idea_signal" in signal.tags
    assert "7-day validation test" in signal.recommended_action
