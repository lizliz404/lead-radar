# Architecture: Lead Radar

## 1. Principles

Lead Radar follows five architecture principles:

1. Code first: core logic must be testable, versioned, and portable.
2. Pluggable sources: Reddit is the MVP source, not a permanent platform lock-in.
3. Rules before LLMs: broad data is filtered by deterministic rules before any LLM call.
4. Evidence loop: every useful insight must point back to an original source URL.
5. Low operational cost: the MVP should run from a local CLI, cron, GitHub Actions, or a small server.

## 2. Modules

```text
lead_radar/
  cli.py          CLI entrypoint
  config.py       YAML configuration loading and validation
  models.py       Pydantic data models
  reddit.py       Reddit source adapter
  scoring.py      rule filtering and scoring
  llm.py          optional LLM rerank and strategic report generation
  report.py       deterministic Markdown report builder
  storage.py      SQLite persistence
  feishu.py       Feishu webhook notification
  telegram.py     Telegram bot notification
```

### Config

Loads `config.yaml`, validates topics, and provides structured settings to the rest of the pipeline.

### Collector

Fetches posts from Reddit or mock data and normalizes them into `RawPost`. It should not make business judgments.

### Scorer

Scores posts against topic rules, returns `LeadSignal`, keeps evidence, and controls the Top N candidate set.

### LLM

Optionally reranks rule-selected candidates and optionally generates the final executive-style strategic report. It should operate on a small candidate set, not on unfiltered raw posts.

### Report Builder

Builds deterministic Markdown reports from `LeadSignal` data. This remains available even when LLM reporting is disabled.

### Storage

Stores scan runs, posts, signals, report paths, and notification status in SQLite.

### Notifier

Sends report output to Telegram or Feishu. Telegram can send the full Markdown report in chunks; Feishu currently sends a summary and local report path.

## 3. Data Flow

```text
1. User runs the CLI
2. CLI loads config.yaml
3. CLI selects a topic
4. Collector fetches RawPost items
5. Scorer filters, scores, and sorts posts
6. Optional LLM reranker reorders the candidate set
7. Deterministic report builder or LLM report generator writes Markdown
8. Storage writes SQLite history
9. Notifier optionally sends Telegram or Feishu messages
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
- `raw`

`LeadSignal` represents a scored opportunity:

- `post`
- `score`
- `buying_intent`
- `confidence`
- `evidence`
- `pain_summary`
- `recommended_action`
- `tags`

## 6. Extension Points

### New Sources

Add a new source adapter that returns `list[RawPost]`. Candidate sources include RSS, Hacker News, Product Hunt, GitHub Issues, and compliant APIs for other public platforms.

### New LLM Analysis

Keep LLM analysis downstream of rule scoring. Recommended outputs include pain category, buying intent, business context, recommended action, confidence, and source evidence.

### New Notification Channels

The notification layer can support additional webhooks, email, Slack, Discord, or interactive cards without changing the scoring pipeline.

## 7. Deployment Options

Local manual run:

```bash
lead-radar run --config config.yaml --topic paid_demand_signals
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
- Do not automate spam, harassment, or bulk private outreach.
- Treat reports as human decision support.

## 9. Upgrade Criteria

Before adding complexity, answer one question:

> Will this improve lead quality, reduce manual review cost, or improve reliability enough to justify the added system surface?

If not, keep the architecture simple.
