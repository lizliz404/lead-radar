from __future__ import annotations

import math
from datetime import datetime, timezone

from lead_radar.models import LeadSignal, RawPost, SignalStrength, TopicConfig

SCORING_PROFILES = {
    "lead": {
        "primary_label": "buying",
        "primary_tag": "buying_intent",
        "primary_phrases": [
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
        ],
        "help_phrases": [
            "need help",
            "looking for help",
            "can someone",
            "how do i",
            "is there a way",
            "what is the best way",
            "stuck",
            "not sure",
        ],
        "pain_phrases": [
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
        ],
        "high_relevance_communities": {"automation", "zapier", "nocode", "smallbusiness", "entrepreneur", "saas"},
    },
    "idea": {
        "primary_label": "idea",
        "primary_tag": "idea_signal",
        "primary_phrases": [
            "i wish there was",
            "does anyone know a tool",
            "is there a tool",
            "looking for a tool",
            "alternative to",
            "nothing works",
            "too expensive",
            "missing feature",
            "would pay for",
        ],
        "help_phrases": ["how do i", "any recommendations", "what do you use", "is there a way", "workaround"],
        "pain_phrases": ["frustrating", "annoying", "manual", "tedious", "time consuming", "broken", "limited", "expensive"],
        "high_relevance_communities": {"saas", "startups", "entrepreneur", "indiehackers", "smallbusiness"},
    },
    "distribution": {
        "primary_label": "distribution",
        "primary_tag": "distribution_signal",
        "primary_phrases": [
            "where do you find",
            "how do you promote",
            "best channels",
            "growth channel",
            "acquisition",
            "traffic source",
            "subreddit recommendations",
            "communities for",
        ],
        "help_phrases": ["how do i", "what worked", "any advice", "recommendations", "where should i"],
        "pain_phrases": ["no traction", "hard to reach", "low conversion", "expensive ads", "distribution", "marketing"],
        "high_relevance_communities": {"saas", "startups", "entrepreneur", "marketing", "growthhacking"},
    },
    "competitor_pain": {
        "primary_label": "complaint",
        "primary_tag": "competitor_pain_signal",
        "primary_phrases": [
            "alternative to",
            "switching from",
            "migrating away",
            "too expensive",
            "poor support",
            "missing feature",
            "keeps breaking",
            "vendor lock-in",
        ],
        "help_phrases": ["any alternatives", "what should i use", "recommend", "replace", "switch"],
        "pain_phrases": ["frustrating", "broken", "slow", "expensive", "buggy", "limited", "bad support"],
        "high_relevance_communities": {"saas", "smallbusiness", "selfhosted", "sysadmin", "productivity"},
    },
    "alternative": {
        "primary_label": "alternative",
        "primary_tag": "alternative_request",
        "primary_phrases": [
            "alternative to",
            "open source alternative",
            "cheaper alternative",
            "self-hosted alternative",
            "replace",
            "switch from",
            "similar to",
        ],
        "help_phrases": ["any recommendations", "what do you use", "looking for", "need a tool", "is there a tool"],
        "pain_phrases": ["too expensive", "limited", "bad support", "privacy", "vendor lock-in", "missing feature"],
        "high_relevance_communities": {"selfhosted", "opensource", "saas", "productivity", "smallbusiness"},
    },
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

    profile = SCORING_PROFILES[topic.intent_profile]
    primary_label = profile["primary_label"]
    primary_tag = profile["primary_tag"]

    primary_hits = [phrase for phrase in profile["primary_phrases"] if phrase in text]
    help_hits = [phrase for phrase in profile["help_phrases"] if phrase in text]
    pain_hits = [phrase for phrase in profile["pain_phrases"] if phrase in text]

    if primary_hits:
        score += 4 + min(len(primary_hits), 3)
        evidence.extend([f"{primary_label}: {phrase}" for phrase in primary_hits[:3]])
        tags.append(primary_tag)

    if help_hits:
        score += 2 + min(len(help_hits), 2)
        evidence.extend([f"help: {phrase}" for phrase in help_hits[:2]])
        tags.append("help_request")

    if pain_hits:
        score += 2 + min(len(pain_hits), 3)
        evidence.extend([f"pain: {phrase}" for phrase in pain_hits[:3]])
        tags.append("pain_signal")

    if post.community and post.community.lower() in profile["high_relevance_communities"]:
        score += 1.5
        tags.append("high_relevance_source")

    if post.source == "hacker_news":
        score += 0.8
        tags.append("hn_source")

    score += min(math.log1p(max(post.num_comments, 0)), 3)
    score += min(math.log1p(max(post.upvotes, 0)) / 2, 2)

    hours_old = (datetime.now(timezone.utc) - post.created_at).total_seconds() / 3600
    if hours_old <= 24:
        score += 1.0
        tags.append("fresh")
    elif hours_old <= 72:
        score += 0.5

    signal_strength = classify_signal_strength(primary_hits, help_hits, pain_hits)
    confidence = confidence_from_score(score)

    return LeadSignal(
        post=post,
        score=round(score, 2),
        signal_strength=signal_strength,
        confidence=confidence,
        evidence=evidence[:8],
        pain_summary=make_pain_summary(post, pain_hits, help_hits, topic),
        recommended_action=make_recommended_action(signal_strength, post, topic),
        tags=sorted(set(tags)),
    )


def classify_signal_strength(
    primary_hits: list[str], help_hits: list[str], pain_hits: list[str]
) -> SignalStrength:
    if primary_hits:
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


def make_pain_summary(post: RawPost, pain_hits: list[str], help_hits: list[str], topic: TopicConfig) -> str:
    if pain_hits:
        return f"Likely {topic.intent_profile} pain signals: {', '.join(pain_hits[:3])}. Open the source post to confirm the user, context, and repeatability."
    if help_hits:
        return f"Likely {topic.intent_profile} request: {', '.join(help_hits[:3])}. Check whether the context supports the report goal: {topic.report_goal}"
    return "No strong pain was detected. This may be generic discussion; review at low priority."


def make_recommended_action(intent: SignalStrength, post: RawPost, topic: TopicConfig) -> str:
    actions = {
        "lead": {
            "strong": "Open the source post first. If the context fits, ask one concrete diagnostic question and offer a lightweight consultation or solution breakdown.",
            "medium": "Open the source post and confirm the business context. Look for tool stack, budget, deadline, or repetitive-work clues.",
            "weak": "Use this as content research or demand observation. Do not treat it as an immediate sales lead.",
            "none": "Low priority. Use only for trend observation.",
        },
        "idea": {
            "strong": "Open the source post and capture the user, pain, current workaround, and weak alternatives. Turn it into a 7-day validation test before building.",
            "medium": "Check whether this pain repeats across communities. Save only if the user and current workaround are clear.",
            "weak": "Use as raw idea fodder, not product evidence yet.",
            "none": "Low priority. Do not promote it to an idea without repeated evidence.",
        },
        "distribution": {
            "strong": "Open the source post and extract channel, audience, angle, and compliance risk. Convert into one safe distribution experiment.",
            "medium": "Review for channel clues and objections. Avoid automation or manipulation unless explicitly compliant.",
            "weak": "Use as market-language research, not an execution target.",
            "none": "Low priority. Track only if the same channel pattern repeats.",
        },
        "competitor_pain": {
            "strong": "Open the source post and capture the competitor, complaint, switching trigger, and missing feature. Look for repeated pain before outreach or positioning changes.",
            "medium": "Check whether the complaint is specific enough to inform positioning or feature comparison.",
            "weak": "Use as objection-language research, not proof of demand.",
            "none": "Low priority. Avoid overfitting to one vague complaint.",
        },
        "alternative": {
            "strong": "Open the source post and identify the incumbent, required replacement criteria, budget sensitivity, and decision context.",
            "medium": "Review for concrete alternative criteria and repeated unmet needs.",
            "weak": "Use as keyword and positioning research.",
            "none": "Low priority. Track only if repeated.",
        },
    }
    return actions[topic.intent_profile][intent]
