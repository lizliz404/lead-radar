from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


BuyingIntent = Literal["strong", "medium", "weak", "none"]


class RedditSourceConfig(BaseModel):
    subreddits: list[str] = Field(default_factory=list)

    @field_validator("subreddits")
    @classmethod
    def normalize_subreddits(cls, value: list[str]) -> list[str]:
        return [item.strip().removeprefix("r/") for item in value if item.strip()]


class SourcesConfig(BaseModel):
    reddit: RedditSourceConfig | None = None


class TopicConfig(BaseModel):
    name: str
    description: str = ""
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
    buying_intent: BuyingIntent
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    pain_summary: str
    recommended_action: str
    tags: list[str] = Field(default_factory=list)


class ScanResult(BaseModel):
    topic_name: str
    scanned_at: datetime
    total_posts: int
    candidate_count: int
    signals: list[LeadSignal]
    report_path: str | None = None
