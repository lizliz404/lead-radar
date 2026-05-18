# Architecture: Lead Radar

## 1. Principles

Lead Radar follows five architecture principles:

1. Code first: core logic must be testable, versioned, and portable.
2. Pluggable sources: Reddit is the MVP source, not a permanent platform lock-in.
3. Presets over rewrites: Lead Radar, Idea Hunt, Go Global, competitor pain, and alternative-request workflows should reuse the same core pipeline with different topic presets, scoring profiles, and report goals.
4. Rules before LLMs: broad data is filtered by deterministic rules before any LLM call.
5. Evidence loop: every useful insight must point back to an original source URL.
6. Low operational cost: the MVP should run from a local CLI, cron, GitHub Actions, or a small server.

## 2. Modules

```text
lead_radar/
  api.py          FastAPI JSON API and OpenAPI contract
  service.py      shared scan orchestration used by API and CLI
  cli.py          CLI entrypoint
  config.py       YAML configuration loading and validation
  models.py       Pydantic data models
  sources.py      source adapter boundary and native source registry
  reddit.py       Reddit source client
  ingest.py       third-party alert ingest and ingested-post scoring workflow
  scoring.py      rule filtering and scoring
  llm.py          optional LLM rerank and strategic report generation
  report.py       deterministic Markdown report builder
  storage.py      SQLite persistence
  feishu.py       Feishu webhook notification
  telegram.py     Telegram bot notification
```

### Config

Loads `config.yaml`, validates topics, and provides structured settings to the rest of the pipeline. A topic is a use-case preset: it can select an `intent_profile` and `report_goal` without changing collectors, storage, notifications, or the core scoring flow.

### API

FastAPI is the long-term backend boundary for the product. It exposes health checks, topic metadata, scan execution, review updates, and OpenAPI docs while reusing the same Python core as the CLI.

### Service

`service.py` owns scan orchestration: load config, collect posts, score, optionally rerank/report with an LLM, write Markdown, and persist to SQLite. Both FastAPI and CLI call this layer so business logic does not drift between interfaces.

### Source Adapters

`sources.py` is the native collection boundary. A source adapter fetches public discussion data and normalizes it into `RawPost`. It should not make business judgments, score posts, write reports, or know about notification channels.

Current native sources:

- `reddit`: Reddit API client, configured per topic.
- `hacker_news`: Hacker News Algolia search, configured per topic.

Stable adapter contract:

```text
TopicConfig -> SourceAdapter.fetch(topic) -> list[RawPost]
```

Adding RSS, Product Hunt, GitHub Issues, or another compliant public source should mean adding one adapter plus config fields. It should not require changing scoring, report generation, review storage, notification, or CLI/API orchestration.

### Third-Party Alert Ingest

`ingest.py` is the boundary for vendor-collected alerts from tools such as F5Bot, Syften, Octolens, Zapier, or n8n. These tools are treated as outsourced collection, not as Lead Radar's moat.

The stable ingest contract is:

```text
IngestedAlert -> RawPost -> SQLite posts table -> scoring/report/review workflow
```

Rules:

- Vendors map into the generic `IngestedAlert` shape.
- Each alert must identify `source` and should provide a stable `source_id`.
- SQLite upsert is idempotent on `(source, source_id)`.
- Vendor-specific quirks belong in thin normalization code before or at the ingest boundary, not in scoring/report modules.
- Scoring ingested posts uses the same `score_posts`, report builder, and scan-run storage as native scans.

### Scorer

Scores posts against topic rules and the selected `intent_profile`, returns `LeadSignal`, keeps evidence, and controls the Top N candidate set. `signal_strength` is the canonical strength field. `buying_intent` remains only as a backward-compatible alias for old lead-only callers and SQLite rows.

### LLM

Optionally reranks rule-selected candidates and optionally generates the final executive-style strategic report. It should operate on a small candidate set, not on unfiltered raw posts.

### Report Builder

Builds deterministic Markdown reports from `LeadSignal` data. This remains available even when LLM reporting is disabled.

### Storage

Stores scan runs, posts, signals, report paths, notification status, and review feedback in SQLite. Ingested alerts are stored in the same `posts` table as native source posts so downstream scoring and reports do not fork.

### Notifier

Sends report output to Telegram or Feishu. Telegram can send the full Markdown report in chunks; Feishu currently sends a summary and local report path.

## 3. Data Flow

```text
1. Next.js or an operator calls FastAPI, or an operator runs the CLI
2. API/CLI calls the shared service layer
3. Service loads config.yaml and selects a topic
4. Source adapters fetch RawPost items, or mock data is loaded
5. Scorer filters, scores, and sorts posts
6. Optional LLM reranker reorders the candidate set
7. Deterministic report builder or LLM report generator writes Markdown
8. Storage writes SQLite history
9. API returns JSON / CLI prints output / notifier optionally sends Telegram or Feishu messages
```

Third-party alert flow:

```text
1. Vendor, Zapier, n8n, or an operator POSTs alerts to /ingest/alerts
2. API validates IngestedAlert items and upserts them into SQLite posts
3. Operator, schedule, or automation calls /ingest/score or `lead-radar score-ingested`
4. Ingested posts are loaded from SQLite with optional source/topic filters
5. The normal scorer, report builder, and scan-run storage are reused
6. Review feedback updates the same signal/review tables
```

## 4. Why Not Send Everything to an LLM

LLMs are useful for semantic synthesis, not for replacing the full filtering layer. Sending every fetched post to an LLM creates avoidable cost, latency, prompt complexity, and debugging difficulty.

The intended flow is:

```text
all posts -> rule filter -> Top N candidates -> optional LLM analysis
```

## 5. Data Model

`RawPost` represents a normalized source post:

- `source`
- `source_id`
- `url`
- `title`
- `body`
- `author`
- `community`
- `created_at`
- `upvotes`
- `num_comments`
- `topic_name`
- `raw`

`IngestedAlert` represents a vendor or webhook alert before normalization:

- `source`
- `source_id`
- `url`
- `title`
- `body`
- `author`
- `community`
- `created_at`
- `topic_name`
- `upvotes`
- `num_comments`
- `tags`
- `raw`

The ingest layer converts `IngestedAlert` into `RawPost`. Keep the conversion lossy only where necessary; preserve vendor payload details in `raw` when they may help debugging.

`LeadSignal` represents a scored opportunity:

- `post`
- `score`
- `signal_strength`
- `buying_intent` compatibility alias
- `confidence`
- `evidence`
- `pain_summary`
- `recommended_action`
- `tags`

## 6. Extension Points

### Use-Case Presets

The stable core is:

```text
Source adapters -> Topic presets -> Rule scoring -> Optional LLM rerank -> Evidence-linked report -> Review feedback -> Scheduled run
```

Current presets should be configuration-level variants, not separate products or forks:

- `paid_demand_signals`: Lead Radar / sales-lead review.
- `saas_idea_hunt`: Idea Hunt / product opportunity validation.
- `go_global_distribution`: Go Global / safe distribution experiment discovery.
- `competitor_pain`: competitor complaint and switching-trigger monitoring.
- `alternative_requests`: replacement-demand and positioning research.

### New Sources

Add a new source adapter that returns `list[RawPost]`. Candidate sources include RSS, Product Hunt, GitHub Issues, and compliant APIs for other public platforms.

Do not add source-specific scoring branches unless the source itself changes signal quality. Most source differences should be represented as `RawPost.source`, `community`, metadata in `raw`, and optional tags.

### New Vendor Ingests

For F5Bot, Syften, Octolens, Zapier, n8n, or another third-party alert provider, prefer this path:

```text
Vendor payload -> IngestedAlert -> /ingest/alerts -> /ingest/score or score-ingested CLI
```

Only create a dedicated vendor module when the mapping is complex enough to justify tests. The main pipeline should never know the vendor's API shape.

Minimum recommended fields:

- `source`: vendor or upstream source name, such as `f5bot`, `syften`, or `octolens`.
- `source_id`: stable alert/post id for idempotency.
- `url`: canonical evidence URL.
- `title` and/or `body`: text to score.
- `community`: forum, subreddit, site, or channel name if available.
- `topic_name`: optional topic hint for later filtering.
- `tags`: vendor/source metadata such as `vendor:f5bot`.

### New LLM Analysis

Keep LLM analysis downstream of rule scoring. Recommended outputs include pain category, buying intent, business context, recommended action, confidence, and source evidence.

### New Notification Channels

The notification layer can support additional webhooks, email, Slack, Discord, or interactive cards without changing the scoring pipeline.

## 7. Deployment Options

FastAPI service:

```bash
uvicorn lead_radar.api:app --host 0.0.0.0 --port 8000
```

Docker deploys the FastAPI service by default. Streamlit is optional legacy/operator UI, not the public product path.

Local manual run:

```bash
lead-radar run --config config.yaml --topic paid_demand_signals
```

Score already-ingested third-party alerts:

```bash
lead-radar score-ingested \
  --config config.yaml \
  --topic paid_demand_signals \
  --db-path data/lead_radar.sqlite \
  --output-dir reports \
  --source f5bot
```

GitHub Actions:

```text
scheduled workflow -> install package -> run CLI -> upload report artifacts -> send notification
```

Server or cron:

```text
cron/systemd timer -> CLI -> SQLite -> notification
```

## 8. Security and Compliance

- Read API keys only from environment variables.
- Do not commit `.env`.
- Avoid retaining unnecessary personal data.
- Respect platform deletion, retention, and API rules.
- Do not automate spam, harassment, bulk private outreach, account rotation, vote manipulation, or ToS circumvention.
- Treat reports as human decision support, not automatic acquisition or growth hacking execution.

## 9. Stability Boundary

The project is considered architecturally stable when new collection paths follow one of two routes:

```text
Native public source -> SourceAdapter -> RawPost
Third-party alert -> IngestedAlert -> RawPost
```

Everything downstream should stay shared:

```text
RawPost -> score_posts -> LeadSignal -> Markdown report -> SQLite scan run -> review feedback
```

If a future change requires editing scoring, report generation, API contracts, CLI commands, and storage all at once just to add a source, that is a design regression. The correct fix is usually to repair the boundary, not to keep patching vendor-specific paths.

## 10. Upgrade Criteria

Before adding complexity, answer one question:

> Will this improve lead quality, reduce manual review cost, or improve reliability enough to justify the added system surface?

If not, keep the architecture simple.
