from datetime import datetime, timezone

from lead_radar.llm import LLMReportGenerator, SUMMARY_REPORT_ORIGINAL_REQUEST
from lead_radar.models import LeadSignal, RawPost


def make_signal() -> LeadSignal:
    return LeadSignal(
        post=RawPost(
            source="reddit",
            source_id="abc",
            url="https://example.com/abc",
            title="Need an n8n workflow for invoice approvals",
            body="We have budget and want someone to build this workflow for our team.",
            community="n8n",
            created_at=datetime.now(timezone.utc),
            upvotes=12,
            num_comments=4,
        ),
        score=18,
        buying_intent="strong",
        confidence=0.9,
        evidence=["budget", "build this workflow"],
        pain_summary="Invoice approval process is manual and needs automation.",
        recommended_action="Offer a paid n8n workflow implementation call.",
        tags=["buying_intent"],
    )


def test_summary_report_payload_uses_n8n_strategy_prompt() -> None:
    generator = LLMReportGenerator(api_key="key", base_url="https://llm.example/v1", model="model")

    payload = generator._build_payload([make_signal()])

    messages = payload["messages"]
    assert "顶尖的战略分析师" in messages[0]["content"]
    assert "战略行动建议 (Strategic Recommendations)" in messages[0]["content"]
    assert SUMMARY_REPORT_ORIGINAL_REQUEST in messages[1]["content"]
    assert "Need an n8n workflow for invoice approvals" in messages[1]["content"]
    assert "Offer a paid n8n workflow implementation call." in messages[1]["content"]
