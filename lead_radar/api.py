from __future__ import annotations

import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from lead_radar.config import load_config
from lead_radar.models import ScanResult, TopicConfig
from lead_radar.service import run_scan
from lead_radar.storage import SQLiteStore

load_dotenv()

DEFAULT_CONFIG_PATH = os.getenv("LEAD_RADAR_CONFIG_PATH", "config.yaml")
DEFAULT_OUTPUT_DIR = os.getenv("LEAD_RADAR_REPORTS_DIR", "reports")
DEFAULT_DB_PATH = os.getenv("LEAD_RADAR_DB_PATH", "data/lead_radar.sqlite")
API_TOKEN = os.getenv("LEAD_RADAR_API_TOKEN")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("LEAD_RADAR_CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app = FastAPI(
    title="Lead Radar API",
    version="0.1.0",
    description="JSON API for running and reviewing public social demand-signal scans.",
)

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )


class HealthResponse(BaseModel):
    status: str = "ok"


class TopicSummary(BaseModel):
    name: str
    description: str
    intent_profile: str
    report_goal: str


class ScanRequest(BaseModel):
    topic: str = "paid_demand_signals"
    config_path: str = DEFAULT_CONFIG_PATH
    mock: bool = False
    output_dir: str = DEFAULT_OUTPUT_DIR
    db_path: str | None = None
    llm_rerank: bool = False
    llm_report: bool = False
    llm_candidate_limit: int = Field(default=20, ge=1, le=100)
    persist: bool = True


class ScanResponse(BaseModel):
    run_id: int | None
    result: ScanResult
    markdown: str


class ReviewRequest(BaseModel):
    run_id: int
    source: str = "reddit"
    source_id: str
    status: str = Field(pattern="^(new|useful|not_useful|contacted|replied|converted)$")
    note: str = ""
    db_path: str | None = None


class ReviewSummaryResponse(BaseModel):
    run_id: int | None
    total: int
    reviewed: int
    positive: int
    positive_rate: float
    by_status: dict[str, int]


def require_api_token(authorization: Annotated[str | None, Header()] = None) -> None:
    if not API_TOKEN:
        return
    expected = f"Bearer {API_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token.",
        )


def load_topic_config(config_path: str, topic_name: str) -> TopicConfig:
    try:
        return load_config(config_path).get_topic(topic_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/topics", response_model=list[TopicSummary])
def list_topics(config_path: str = DEFAULT_CONFIG_PATH) -> list[TopicSummary]:
    try:
        config = load_config(config_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        TopicSummary(
            name=topic.name,
            description=topic.description,
            intent_profile=topic.intent_profile,
            report_goal=topic.report_goal,
        )
        for topic in config.topics
    ]


@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(require_api_token)])
def scan(request: ScanRequest) -> ScanResponse:
    load_topic_config(request.config_path, request.topic)
    try:
        result, markdown, run_id = run_scan(
            config_path=request.config_path,
            topic_name=request.topic,
            mock=request.mock,
            output_dir=request.output_dir,
            db_path=request.db_path or DEFAULT_DB_PATH,
            llm_rerank=request.llm_rerank,
            llm_report=request.llm_report,
            llm_candidate_limit=request.llm_candidate_limit,
            persist=request.persist,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScanResponse(run_id=run_id, result=result, markdown=markdown)


@app.post("/reviews", dependencies=[Depends(require_api_token)])
def update_review(request: ReviewRequest) -> dict[str, str]:
    SQLiteStore(request.db_path or DEFAULT_DB_PATH).update_signal_review(
        run_id=request.run_id,
        source=request.source,
        source_id=request.source_id,
        status=request.status,
        note=request.note,
    )
    return {"status": "ok"}


@app.get("/reviews/summary", response_model=ReviewSummaryResponse, dependencies=[Depends(require_api_token)])
def review_summary(
    run_id: int | None = None,
    db_path: str | None = None,
) -> ReviewSummaryResponse:
    summary = SQLiteStore(db_path or DEFAULT_DB_PATH).get_review_summary(run_id)
    return ReviewSummaryResponse.model_validate(summary)
