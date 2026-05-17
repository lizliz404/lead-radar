from datetime import datetime, timezone

from lead_radar.llm import LLMReportGenerator, summary_report_original_request
from lead_radar.models import LeadSignal, RawPost, RedditSourceConfig, TopicConfig


def make_topic() -> TopicConfig:
    return TopicConfig(
        name="shopify_inventory",
        description="Find demand for inventory forecasting tools among Shopify sellers.",
        sources={"reddit": RedditSourceConfig(subreddits=["shopify", "ecommerce"])},
        keywords=["inventory forecasting", "reorder points", "stockouts"],
        include_phrases=["willing to pay", "manual spreadsheet"],
        exclude_phrases=["course", "affiliate"],
    )


def make_signal() -> LeadSignal:
    return LeadSignal(
        post=RawPost(
            source="reddit",
            source_id="abc",
            url="https://example.com/abc",
            title="Need an inventory forecasting workflow for Shopify",
            body="We have budget and want something that tells us when to reorder.",
            author="example_user",
            community="shopify",
            created_at=datetime.now(timezone.utc),
            upvotes=12,
            num_comments=4,
        ),
        score=18,
        signal_strength="strong",
        confidence=0.9,
        evidence=["budget", "when to reorder"],
        pain_summary="Inventory reorder planning is manual and needs automation.",
        recommended_action="Validate willingness to pay for reorder planning.",
        tags=["buying_intent"],
    )


def test_summary_report_payload_uses_active_topic_request() -> None:
    generator = LLMReportGenerator(api_key="key", base_url="https://llm.example/v1", model="model")
    topic = make_topic()

    payload = generator._build_payload([make_signal()], topic)

    messages = payload["messages"]
    topic_request = summary_report_original_request(topic)
    assert "top-tier strategic analyst" in messages[0]["content"]
    assert "Strategic Recommendations" in messages[0]["content"]
    assert topic_request in messages[1]["content"]
    assert "shopify_inventory" in messages[1]["content"]
    assert "inventory forecasting" in messages[1]["content"]
    assert "n8n workflow creation" not in messages[1]["content"]
    assert "Need an inventory forecasting workflow for Shopify" in messages[1]["content"]
    assert "Validate willingness to pay for reorder planning." in messages[1]["content"]
