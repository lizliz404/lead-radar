from __future__ import annotations

import math
from datetime import datetime, timezone

from lead_radar.models import BuyingIntent, LeadSignal, RawPost, TopicConfig

BUYING_INTENT_PHRASES = [
    "willing to pay",
    "paid help",
    "pay someone",
    "hire someone",
    "hire a",
    "looking to hire",
    "freelancer",
    "consultant",
    "contractor",
    "budget",
    "quote",
    "proposal",
]

PAIN_PHRASES = [
    "manual work",
    "manual process",
    "takes too much time",
    "too much time",
    "repetitive",
    "tedious",
    "messy",
    "spreadsheet",
    "copy paste",
    "client onboarding",
    "reporting",
    "sync",
    "integration",
]

HELP_PHRASES = [
    "need help",
    "looking for help",
    "can someone",
    "how do i",
    "is there a way",
    "what is the best way",
    "stuck",
    "not sure",
]

HIGH_RELEVANCE_COMMUNITIES = {
    "automation",
    "zapier",
    "nocode",
    "smallbusiness",
    "entrepreneur",
    "saas",
}


def score_posts(posts: list[RawPost], topic: TopicConfig, limit: int | None = None) -> list[LeadSignal]:
    signals: list[LeadSignal] = []
    for post in posts:
        if post.num_comments < topic.min_comments or post.upvotes < topic.min_upvotes:
            continue
        signal = score_post(post, topic)
        if signal.score <= 0:
            continue
        signals.append(signal)

    signals.sort(key=lambda item: item.score, reverse=True)
    return signals[: (limit or topic.output_top_n)]


def score_post(post: RawPost, topic: TopicConfig) -> LeadSignal:
    text = post.text.lower()
    evidence: list[str] = []
    tags: list[str] = []
    score = 0.0

    for phrase in topic.exclude_phrases:
        if phrase.lower() in text:
            score -= 5
            evidence.append(f"excluded-ish: {phrase}")
            tags.append("possible_noise")

    for keyword in topic.keywords:
        if keyword.lower() in text:
            score += 1.5
            evidence.append(f"keyword: {keyword}")

    for phrase in topic.include_phrases:
        if phrase.lower() in text:
            score += 3
            evidence.append(f"include: {phrase}")

    buying_hits = [phrase for phrase in BUYING_INTENT_PHRASES if phrase in text]
    help_hits = [phrase for phrase in HELP_PHRASES if phrase in text]
    pain_hits = [phrase for phrase in PAIN_PHRASES if phrase in text]

    if buying_hits:
        score += 4 + min(len(buying_hits), 3)
        evidence.extend([f"buying: {phrase}" for phrase in buying_hits[:3]])
        tags.append("buying_intent")

    if help_hits:
        score += 2 + min(len(help_hits), 2)
        evidence.extend([f"help: {phrase}" for phrase in help_hits[:2]])
        tags.append("help_request")

    if pain_hits:
        score += 2 + min(len(pain_hits), 3)
        evidence.extend([f"pain: {phrase}" for phrase in pain_hits[:3]])
        tags.append("pain_signal")

    if post.community and post.community.lower() in HIGH_RELEVANCE_COMMUNITIES:
        score += 1.5
        tags.append("high_relevance_source")

    score += min(math.log1p(max(post.num_comments, 0)), 3)
    score += min(math.log1p(max(post.upvotes, 0)) / 2, 2)

    hours_old = (datetime.now(timezone.utc) - post.created_at).total_seconds() / 3600
    if hours_old <= 24:
        score += 1.0
        tags.append("fresh")
    elif hours_old <= 72:
        score += 0.5

    buying_intent = classify_buying_intent(buying_hits, help_hits, pain_hits)
    confidence = confidence_from_score(score)

    return LeadSignal(
        post=post,
        score=round(score, 2),
        buying_intent=buying_intent,
        confidence=confidence,
        evidence=evidence[:8],
        pain_summary=make_pain_summary(post, pain_hits, help_hits),
        recommended_action=make_recommended_action(buying_intent, post),
        tags=sorted(set(tags)),
    )


def classify_buying_intent(
    buying_hits: list[str], help_hits: list[str], pain_hits: list[str]
) -> BuyingIntent:
    if buying_hits:
        return "strong"
    if help_hits and pain_hits:
        return "medium"
    if help_hits or pain_hits:
        return "weak"
    return "none"


def confidence_from_score(score: float) -> float:
    if score <= 0:
        return 0.0
    return round(min(score / 20, 1.0), 2)


def make_pain_summary(post: RawPost, pain_hits: list[str], help_hits: list[str]) -> str:
    if pain_hits:
        return f"Likely pain signals: {', '.join(pain_hits[:3])}. Open the source post to confirm the business context."
    if help_hits:
        return f"Likely help request: {', '.join(help_hits[:3])}. Check whether budget or implementation intent is present."
    return "No strong pain was detected. This may be generic discussion; review at low priority."


def make_recommended_action(intent: BuyingIntent, post: RawPost) -> str:
    if intent == "strong":
        return "Open the source post first. If the context fits, ask one concrete diagnostic question and offer a lightweight consultation or solution breakdown."
    if intent == "medium":
        return "Open the source post and confirm the business context. Look for tool stack, budget, deadline, or repetitive-work clues."
    if intent == "weak":
        return "Use this as content research or demand observation. Do not treat it as an immediate sales lead."
    return "Low priority. Use only for trend observation."
