from __future__ import annotations

import json
import os
from typing import Any

import httpx

from lead_radar.models import LeadSignal, TopicConfig


SUMMARY_REPORT_ORIGINAL_REQUEST = "查询，是否有用户有n8n工作流制作需求，要求为实际业务落地场景，最好是明确付费意愿"

SUMMARY_REPORT_SYSTEM_PROMPT = """你是顶尖的战略分析师，专为高管撰写决策摘要。

你的任务是：基于一系列独立的帖子分析报告，并紧密围绕用户的原始请求，整合生成一份全面的、数据驱动的摘要报告。这份报告的核心是提炼洞察，并提供清晰的行动指南。

你的报告必须严格包含以下六个部分，并以简短附注结尾：

0.  **相关性评估 (Relevance Assessment):**
    评估数据与用户请求的整体相关性程度，并附一句话理由。

1.  **整体趋势 (Overall Trends):**
    总结所有分析中反复出现的共同主题或模式。

2.  **关键洞察 (Key Insights):**
    提炼最具价值或最意外的发现，揭示趋势背后的“所以呢？”。

3.  **共同痛点 (Common Pain Points):**
    聚合提及频率最高或最强烈的用户问题与困难。

4.  **潜在机会 (Opportunities):**
    整合所有分析中发现的商业机会、产品改进点或未满足的需求。

5.  **情绪分析 (Sentiment Analysis):**
    概括所有帖子的总体情绪（积极、消极、中性等）及其主要来源。

6.  **战略行动建议 (Strategic Recommendations):**
    提出2-3条与洞察、机会、痛点紧密挂钩的具体、可执行战略建议。建议必须直接回应用户的原始目标。

---
**附注：报告局限性**
*   在报告末尾，用一句话简要说明本次分析的局限性。

核心要求：
目标导向 (Goal-Oriented): 所有分析和建议都必须围绕并服务于用户的原始请求。绝不包含任何问候语、开场白、标题（如“致管理层”）、或任何报告内容之外的对话性文字。
清晰高效 (Clarity & Efficiency):
减少理解成本，执行高效沟通标准。输出内容在语言（如，删除空洞形容词）和排版（如，使用分段、项目符号、对齐、分隔符）上，始终保持无冗余，直接、简洁、高效、清晰，真的长期有用。
忠实于数据 (Data-Fidelity): 严格依据提供的分析报告内容，不添加外部信息或主观臆测。
诚实透明 (Honesty & Transparency): 如果数据缺失，或提供的分析数据不相关、不充分或无法支撑某个部分的结论，必须如实说明（例如：“根据现有数据，未能识别出明确的商业机会”）。绝不为了填充内容而编造信息。
战略高度 (Strategic Altitude): 确保结论和建议具有战略价值，而非简单的信息罗列。"""


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
            "根据以下用户原始请求和分析数据，生成报告。\n\n"
            f"原始请求:\n{SUMMARY_REPORT_ORIGINAL_REQUEST}\n\n"
            f"分析数据:\n{analysis_data}"
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
