from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


SignalStrength = Literal["strong", "medium", "weak", "none"]
BuyingIntent = SignalStrength
IntentProfile = Literal["lead", "idea", "distribution", "competitor_pain", "alternative"]


class RedditSourceConfig(BaseModel):
    subreddits: list[str] = Field(default_factory=list)

    @field_validator("subreddits")
    @classmethod
    def normalize_subreddits(cls, value: list[str]) -> list[str]:
        return [item.strip().removeprefix("r/") for item in value if item.strip()]


class HackerNewsSourceConfig(BaseModel):
    enabled: bool = True
    tags: str = "story,comment"


class SourcesConfig(BaseModel):
    reddit: RedditSourceConfig | None = None
    hacker_news: HackerNewsSourceConfig | None = None


class TopicConfig(BaseModel):
    name: str
    description: str = ""
    intent_profile: IntentProfile = "lead"
    report_goal: str = "Find source-linked opportunities and recommend the next human review action."
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    keywords: list[str] = Field(default_factory=list)
    include_phrases: list[str] = Field(default_factory=list)
    exclude_phrases: list[str] = Field(default_factory=list)
    lookback_hours: int = 72
    max_posts_per_source: int = 30
    min_comments: int = 0
    min_upvotes: int = 0
    output_top_n: int = 10

    @field_validator("keywords", "include_phrases", "exclude_phrases")
    @classmethod
    def normalize_phrases(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class AppConfig(BaseModel):
    topics: list[TopicConfig]

    def get_topic(self, name: str) -> TopicConfig:
        for topic in self.topics:
            if topic.name == name:
                return topic
        available = ", ".join(topic.name for topic in self.topics)
        raise ValueError(f"Topic not found: {name}. Available topics: {available}")


class RawPost(BaseModel):
    source: str
    source_id: str
    url: str
    title: str
    body: str = ""
    author: str | None = None
    community: str | None = None
    created_at: datetime
    upvotes: int = 0
    num_comments: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
        elif isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        else:
            raise TypeError("created_at must be datetime, unix timestamp, or ISO string")

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.body}".strip()


class LeadSignal(BaseModel):
    post: RawPost
    score: float
    signal_strength: SignalStrength
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    pain_summary: str
    recommended_action: str
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_buying_intent(cls, data: Any) -> Any:
        if isinstance(data, dict) and "signal_strength" not in data and "buying_intent" in data:
            data = {**data, "signal_strength": data["buying_intent"]}
        return data

    @property
    def buying_intent(self) -> SignalStrength:
        """Backward-compatible alias for older lead-only code and stored reports."""
        return self.signal_strength


class IngestedAlert(BaseModel):
    source: str
    source_id: str
    url: str
    title: str
    body: str = ""
    author: str | None = None
    community: str | None = None
    created_at: datetime | None = None
    upvotes: int = 0
    num_comments: int = 0
    topic_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source", "source_id", "url", "title")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    def to_raw_post(self) -> RawPost:
        return RawPost(
            source=self.source,
            source_id=self.source_id,
            url=self.url,
            title=self.title,
            body=self.body,
            author=self.author,
            community=self.community,
            created_at=self.created_at or datetime.now(timezone.utc),
            upvotes=self.upvotes,
            num_comments=self.num_comments,
            raw={**self.raw, "ingest_tags": self.tags, "topic_name": self.topic_name},
        )


class ScanResult(BaseModel):
    topic_name: str
    scanned_at: datetime
    total_posts: int
    candidate_count: int
    signals: list[LeadSignal]
    report_path: str | None = None
