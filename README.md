# Lead Radar

> A code-first social demand radar that scans public communities, ranks high-intent demand signals, writes actionable Markdown reports, and optionally sends notifications.

Chinese version: [README.zh.md](README.zh.md).

Lead Radar is intentionally narrow: it helps you find posts from people who may be willing to pay for products, services, automation workflows, consulting, or implementation help.

The current MVP focuses on one use case:

> Find recent English-language community posts where users express a concrete business automation need, especially with payment, hiring, outsourcing, or strong help-seeking intent.

## 1. Why This Exists

The original idea came from an n8n automation workflow, but the durable need is not the workflow tool itself. The real need is a repeatable way to discover demand signals without manually browsing Reddit, Hacker News, Product Hunt, forums, or other public sources.

Lead Radar prioritizes:

- high-signal posts over broad social listening;
- source links and evidence over unsupported summaries;
- code, tests, and versioned configuration over fragile low-code flows;
- action-oriented output over polished but vague analysis.

## 2. MVP Scope

The MVP answers one question:

> Given a topic, communities, keywords, and signal rules, which recent posts are worth reviewing or contacting?

Each lead should include:

- post title and URL;
- source and community;
- pain summary;
- buying, outsourcing, procurement, or strong help-seeking signal;
- evidence for why the post matters;
- recommended next action;
- confidence and priority.

The MVP does not try to cover every platform, build a complex UI, or automate outreach.

## 3. Current State

```text
README.md                  English overview and usage
README.zh.md               Chinese overview and usage
app.py                     Lightweight Streamlit review UI
docs/PRD.md                Product requirements
docs/ARCHITECTURE.md       Architecture notes
config.example.yaml        Example topic configuration
.env.example               Environment variable example
lead_radar/                Python CLI implementation
examples/sample_posts.json Local mock data
tests/                     Focused unit tests
```

Core flow:

```text
Topic config -> collect posts or mock data -> rule scoring -> optional LLM rerank -> optional LLM report -> Markdown report -> optional notifications -> optional SQLite history
```

## 4. Why Python

Python fits this project because collection, cleaning, scoring, SQLite, CLIs, and scheduled jobs are straightforward. It also keeps later LLM, vector search, analytics, or notebook workflows easy to add.

This project intentionally avoids LangChain or a full agent framework for the MVP. The main job is a stable data pipeline and signal ranking, not multi-step autonomous reasoning.

## 5. Architecture

```text
config.yaml
  -> Collector: Reddit or mock data
  -> Scorer: rule-first ranking
  -> LLM: optional rerank and strategic report
  -> Report Builder: Markdown output
  -> Storage: SQLite history
  -> Notifier: Telegram or Feishu
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 6. Quick Start

Install with `uv`:

```bash
uv sync --extra dev
uv sync --extra ui
```

Or with a standard virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,ui]'
```

Copy local configuration:

```bash
cp .env.example .env
cp config.example.yaml config.yaml
```

Run with mock data:

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock
```

Or open the lightweight Streamlit UI:

```bash
streamlit run app.py
```

The UI wraps the same pipeline as the CLI. It lets you select a topic, run mock or real Reddit scans, preview scored leads, and download CSV or Markdown output.

Reports are written to:

```text
reports/
```

## 7. Reddit Setup

For stable Reddit access, configure a Reddit app with client credentials:

```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT="lead-radar/0.1 by your_reddit_username"
```

You can also pass an existing bearer token:

```bash
REDDIT_ACCESS_TOKEN=your_access_token
```

Long-running usage should prefer `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` because Reddit access tokens expire.

Run against real Reddit data:

```bash
lead-radar run --config config.yaml --topic paid_demand_signals
```

## 8. Notifications

Telegram sends the full Markdown report and automatically chunks long messages. Feishu sends a concise text summary plus the local report path.

Telegram:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
lead-radar run --config config.yaml --topic paid_demand_signals --mock --notify telegram
```

Feishu:

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
lead-radar run --config config.yaml --topic paid_demand_signals --mock --notify feishu
```

## 9. Optional LLM Usage

The default path uses deterministic rule scoring and does not call an LLM.

Configure any OpenAI-compatible provider:

```bash
LEAD_RADAR_LLM_API_KEY=your_api_key
LEAD_RADAR_LLM_BASE_URL=https://your-provider.example/v1
LEAD_RADAR_LLM_MODEL=your_model
```

Rerank rule-selected candidates:

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock --llm-rerank
```

Generate the final strategic Markdown report with the executive-summary prompt:

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock --llm-report
```

Use both when you want the LLM to rerank candidates first and then write the final report:

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock --llm-rerank --llm-report
```

## 10. GitHub Actions

The repository includes `.github/workflows/lead-radar.yml` for manual and scheduled runs. Configure repository secrets as needed:

```text
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
FEISHU_WEBHOOK_URL
LEAD_RADAR_LLM_API_KEY
LEAD_RADAR_LLM_BASE_URL
LEAD_RADAR_LLM_MODEL
```

The default workflow runs `paid_demand_signals` and sends Telegram notifications. Manual runs can change the topic and notification channel.

## 11. Example Topic Config

```yaml
topics:
  - name: paid_demand_signals
    description: Find public community posts with payment, outsourcing, procurement, or strong help-seeking intent.
    sources:
      reddit:
        subreddits:
          - automation
          - smallbusiness
          - entrepreneur
          - SaaS
          - Zapier
          - NoCode
          - selfhosted
    keywords:
      - "need automation"
      - "automate my workflow"
      - "looking for help"
      - "Zapier alternative"
      - "manual work"
      - "hire someone"
      - "workflow consultant"
      - "business process automation"
      - "client onboarding automation"
      - "willing to pay"
      - "paid help"
    include_phrases:
      - "looking for help"
      - "can someone build"
      - "willing to pay"
      - "paid help"
      - "hire"
      - "freelancer"
      - "consultant"
      - "too much manual work"
      - "manual process"
      - "automate this"
      - "need someone"
    exclude_phrases:
      - "i am selling"
      - "course"
      - "affiliate"
      - "job posting"
      - "hiring for full-time"
      - "giveaway"
    lookback_hours: 72
    max_posts_per_source: 30
    min_comments: 0
    min_upvotes: 0
    output_top_n: 10
```

## 12. Quality Bar

Success is not measured by how many posts are collected. It is measured by how many results are worth opening.

MVP acceptance criteria:

- each run outputs at most the configured Top N leads;
- each lead has a source URL;
- each lead explains why it is worth reviewing;
- manual review time drops from 1-2 hours to 10-20 minutes;
- at least 30% of Top 10 results are worth opening;
- unnecessary raw user content and personal data are not retained long term.

## 13. Roadmap

MVP:

- [x] topic configuration
- [x] mock data mode
- [x] Reddit API collector
- [x] rule scoring
- [x] Markdown reports
- [x] SQLite history
- [x] Feishu webhook notification
- [x] Telegram bot notification
- [x] GitHub Actions schedule
- [x] optional LLM rerank
- [x] optional LLM strategic report

V1:

- [ ] daily production workflow
- [ ] multiple topics
- [ ] report history comparison
- [ ] deduplication and review status
- [ ] Feishu interactive cards
- [ ] simple human feedback: useful, not useful, handled

V2:

- [ ] RSS, Hacker News, Product Hunt, and GitHub Issues sources
- [ ] compliant data access for additional platforms
- [ ] LLM pain clustering
- [ ] competitor monitoring
- [ ] lightweight CRM workflow
- [ ] prompt and scoring-rule experiments

## 14. Compliance Boundaries

- Use only public or authorized data.
- Follow platform API terms, rate limits, and data retention rules.
- Do not aggregate private personal information.
- Do not automate harassment, spam, or bulk outreach.
- Treat reports as decision support, not as a replacement for human judgment.

## 15. Project Principles

1. Start narrow and make one valuable use case work well.
2. Filter with rules before spending LLM tokens.
3. Keep every insight traceable to a source link.
4. Prefer CLI and scheduled jobs until product complexity is justified.
5. Optimize output for the next action, not for sounding impressive.

## Status

Parked prototype. Public on purpose. Do not iterate toward V1 unless Liz explicitly asks.

## License

No license specified yet.
