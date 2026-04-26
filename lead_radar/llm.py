from __future__ import annotations

import json
import os
from typing import Any

import httpx

from lead_radar.models import LeadSignal, TopicConfig


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
