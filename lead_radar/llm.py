from __future__ import annotations

import json
import os
from typing import Any

import httpx

from lead_radar.models import LeadSignal, TopicConfig


def llm_is_configured() -> bool:
    return all(
        os.getenv(key)
        for key in ["LEAD_RADAR_LLM_API_KEY", "LEAD_RADAR_LLM_BASE_URL", "LEAD_RADAR_LLM_MODEL"]
    )


SUMMARY_REPORT_ORIGINAL_REQUEST = (
    "Find whether users have demand for n8n workflow creation. Prioritize real business "
    "implementation scenarios, preferably with clear willingness to pay."
)

SUMMARY_REPORT_SYSTEM_PROMPT = """You are a top-tier strategic analyst writing executive decision summaries.

Your task is to synthesize a comprehensive, data-driven summary report from independent post analysis records. Stay tightly aligned with the user's original request. The report must extract insights and provide clear action guidance.

The report must strictly include the following six sections and end with a short note:

0. **Relevance Assessment:**
   Assess the overall relevance between the data and the user's request, with a one-sentence reason.

1. **Overall Trends:**
   Summarize recurring themes or patterns across the analyses.

2. **Key Insights:**
   Extract the most valuable or unexpected findings and explain the strategic implication.

3. **Common Pain Points:**
   Aggregate the most frequent or intense user problems and difficulties.

4. **Opportunities:**
   Consolidate commercial opportunities, product improvements, or unmet needs found in the analyses.

5. **Sentiment Analysis:**
   Summarize the overall sentiment across posts and the main reasons behind it.

6. **Strategic Recommendations:**
   Provide 2-3 specific, actionable strategic recommendations directly tied to the insights, opportunities, and pain points. The recommendations must directly answer the user's original goal.

---
**Note: Report Limitations**
* End the report with one sentence explaining the limitations of this analysis.

Core requirements:
Goal-Oriented: Every analysis and recommendation must serve the user's original request. Do not include greetings, prefaces, executive-address labels, or conversational text outside the report.
Clarity and Efficiency: Reduce comprehension cost. Use direct, concise, durable language and clean formatting with sections and bullets where useful. Avoid empty adjectives and redundant wording.
Data Fidelity: Rely strictly on the provided analysis records. Do not add external information or unsupported assumptions.
Honesty and Transparency: If data is missing, irrelevant, or insufficient to support a conclusion, say so explicitly. Do not invent conclusions to fill a section.
Strategic Altitude: Ensure conclusions and recommendations have strategic value rather than merely listing information."""


class LLMReranker:
    """OpenAI-compatible LLM reranker for the rule-scored candidate set."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("LEAD_RADAR_LLM_API_KEY")
        self.base_url = (base_url or os.getenv("LEAD_RADAR_LLM_BASE_URL") or "").rstrip("/")
        self.model = model or os.getenv("LEAD_RADAR_LLM_MODEL")
        self.timeout = timeout

    def rerank(self, signals: list[LeadSignal], topic: TopicConfig) -> list[LeadSignal]:
        if not signals:
            return []
        if not self.api_key:
            raise RuntimeError("Missing LEAD_RADAR_LLM_API_KEY")
        if not self.base_url:
            raise RuntimeError("Missing LEAD_RADAR_LLM_BASE_URL")
        if not self.model:
            raise RuntimeError("Missing LEAD_RADAR_LLM_MODEL")

        payload = self._build_payload(signals, topic)
        response_text = self._call(payload)
        ranked_ids = self._parse_ranked_ids(response_text)

        by_id = {self._signal_id(signal): signal for signal in signals}
        reranked = [by_id[item] for item in ranked_ids if item in by_id]
        if not reranked:
            raise RuntimeError("LLM rerank returned no matching candidate ids")

        for signal in reranked:
            if "llm_reranked" not in signal.tags:
                signal.tags.append("llm_reranked")
        return reranked[: topic.output_top_n]

    def _build_payload(self, signals: list[LeadSignal], topic: TopicConfig) -> dict[str, Any]:
        candidates = []
        for signal in signals:
            post = signal.post
            candidates.append(
                {
                    "id": self._signal_id(signal),
                    "rule_score": signal.score,
                    "buying_intent": signal.buying_intent,
                    "community": post.community,
                    "title": post.title,
                    "body_excerpt": post.body[:1200],
                    "evidence": signal.evidence,
                    "url": post.url,
                }
            )

        system = (
            "You are a strict lead-quality reranker. Keep only posts that are likely to represent "
            "real pain, buying intent, outsourcing intent, or actionable product/service demand. "
            "Return compact JSON only."
        )
        user = {
            "topic": topic.name,
            "topic_description": topic.description,
            "instruction": (
                "Rank the best candidates. Drop obvious noise, ads, tutorials, generic discussion, "
                "and posts without a concrete problem. Return JSON with key ranked_ids, an array of ids."
            ),
            "candidates": candidates,
        }
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

    def _call(self, payload: dict[str, Any]) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _parse_ranked_ids(self, response_text: str) -> list[str]:
        data = json.loads(response_text)
        ranked_ids = data.get("ranked_ids")
        if not isinstance(ranked_ids, list):
            raise RuntimeError("LLM rerank response must include ranked_ids list")
        return [item for item in ranked_ids if isinstance(item, str)]

    def _signal_id(self, signal: LeadSignal) -> str:
        return f"{signal.post.source}:{signal.post.source_id}"


class LLMIntentParser:
    """OpenAI-compatible parser that turns a loose market brief into scan parameters."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 45.0,
    ) -> None:
        self.api_key = api_key or os.getenv("LEAD_RADAR_LLM_API_KEY")
        self.base_url = (base_url or os.getenv("LEAD_RADAR_LLM_BASE_URL") or "").rstrip("/")
        self.model = model or os.getenv("LEAD_RADAR_LLM_MODEL")
        self.timeout = timeout

    def parse(self, brief: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Missing LEAD_RADAR_LLM_API_KEY")
        if not self.base_url:
            raise RuntimeError("Missing LEAD_RADAR_LLM_BASE_URL")
        if not self.model:
            raise RuntimeError("Missing LEAD_RADAR_LLM_MODEL")

        payload = self._build_payload(brief)
        response_text = self._call(payload)
        data = json.loads(response_text)
        return self._normalize(data)

    def _build_payload(self, brief: str) -> dict[str, Any]:
        system = """You convert a user's loose business research brief into concrete Reddit scan parameters.
Return compact JSON only. Do not include prose.

Schema:
{
  "target_users": "short buyer/user segment",
  "keywords": ["5-12 concrete search phrases"],
  "subreddits": ["5-10 subreddit names without r/"],
  "include_phrases": ["pain, help, buying, alternative, recommendation phrases"],
  "exclude_phrases": ["noise filters"],
  "lookback_hours": 168,
  "output_top_n": 10
}

Rules:
- Prefer concrete phrases users would actually write in Reddit posts.
- Include pain/problem words, alternatives, recommendations, budget, manual workflow, and tool-stack phrases.
- Choose broad but relevant communities. Avoid niche hallucinated subreddit names unless very likely.
- Keep it useful for commercial insight and demand validation, not generic SEO keyword research."""
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": brief},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

    def _call(self, payload: dict[str, Any]) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        def list_of_strings(key: str) -> list[str]:
            value = data.get(key)
            if not isinstance(value, list):
                return []
            return [str(item).strip() for item in value if str(item).strip()]

        return {
            "target_users": str(data.get("target_users") or "").strip(),
            "keywords": list_of_strings("keywords"),
            "subreddits": list_of_strings("subreddits"),
            "include_phrases": list_of_strings("include_phrases"),
            "exclude_phrases": list_of_strings("exclude_phrases"),
            "lookback_hours": int(data.get("lookback_hours") or 168),
            "output_top_n": int(data.get("output_top_n") or 10),
        }


class LLMReportGenerator:
    """OpenAI-compatible LLM generator for the final strategic Markdown report."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("LEAD_RADAR_LLM_API_KEY")
        self.base_url = (base_url or os.getenv("LEAD_RADAR_LLM_BASE_URL") or "").rstrip("/")
        self.model = model or os.getenv("LEAD_RADAR_LLM_MODEL")
        self.timeout = timeout

    def generate(self, signals: list[LeadSignal]) -> str:
        if not self.api_key:
            raise RuntimeError("Missing LEAD_RADAR_LLM_API_KEY")
        if not self.base_url:
            raise RuntimeError("Missing LEAD_RADAR_LLM_BASE_URL")
        if not self.model:
            raise RuntimeError("Missing LEAD_RADAR_LLM_MODEL")

        payload = self._build_payload(signals)
        return self._call(payload).strip()

    def _build_payload(self, signals: list[LeadSignal]) -> dict[str, Any]:
        analysis_data = "\n---\n".join(
            json.dumps(self._signal_to_analysis(signal), ensure_ascii=False)
            for signal in signals
        )
        user_prompt = (
            "Generate a report from the following original user request and analysis data.\n\n"
            f"Original request:\n{SUMMARY_REPORT_ORIGINAL_REQUEST}\n\n"
            f"Analysis data:\n{analysis_data}"
        )
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SUMMARY_REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

    def _call(self, payload: dict[str, Any]) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _signal_to_analysis(self, signal: LeadSignal) -> dict[str, Any]:
        post = signal.post
        return {
            "source": post.source,
            "community": post.community,
            "title": post.title,
            "body_excerpt": post.body[:1200],
            "url": post.url,
            "score": signal.score,
            "confidence": signal.confidence,
            "buying_intent": signal.buying_intent,
            "pain_summary": signal.pain_summary,
            "recommended_action": signal.recommended_action,
            "evidence": signal.evidence,
            "tags": signal.tags,
            "upvotes": post.upvotes,
            "num_comments": post.num_comments,
            "created_at": post.created_at.isoformat(),
        }
