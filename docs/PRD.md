# PRD: Lead Radar Social Demand Signal Radar

## 1. One-Line Product Definition

Lead Radar is a code-first demand signal radar that scans public communities, finds posts with possible payment intent, outsourcing intent, strong pain, or product opportunity, and generates actionable lead reports.

## 2. Background

The initial concept was an AI social insight agent that accepted a request, fetched Reddit data, cleaned and analyzed it, then sent a report back. After review, the core value is not the orchestration tool. The value is reliable source coverage, search strategy, signal scoring, and action-oriented output.

## 3. Target Users

Primary user:

- independent automation service provider;
- consultant or operator looking for paid workflow implementation opportunities;
- solo builder looking for public demand signals.

Secondary users:

- indie hackers looking for niche SaaS opportunities;
- content creators looking for pains and case studies;
- product managers monitoring complaints and unmet needs;
- early sales operators looking for public leads.

## 4. Core Problem

Users do not lack AI summaries. They lack a reliable way to reduce noisy public community data into a small set of source-linked, actionable opportunities.

Current pain points:

1. Too many community posts to review manually.
2. Keyword searches miss real demand or return noisy results.
3. Platform search lacks business-intent ranking.
4. LLM web search is hard to control and verify.
5. Generic summaries do not guide action.
6. Without history, trends and repeated pains are hard to observe.

## 5. Product Goals

MVP goal:

> After each run, output a Top N demand report that lets the user complete a 1-2 hour community scan in 10-20 minutes.

V1 goal:

> Build a daily personal workflow with scheduled runs, notifications, history, deduplication, and human feedback.

V2 goal:

> Expand into a multi-source, multi-topic demand intelligence system with iterated scoring.

## 6. Non-Goals

The MVP will not:

- build broad full-web social monitoring;
- build a complex web UI;
- automate private messages or sales outreach;
- retain unnecessary raw user content long term;
- generate insights without source links;
- depend on a low-code tool as core infrastructure;
- introduce a complex agent framework at the start.

## 7. MVP Scope

### Data Sources

- Reddit public posts.
- Local mock data for credential-free development.

Future sources may include RSS, Hacker News, Product Hunt, GitHub Issues, and compliant APIs for additional platforms.

### Input

Users define topics through YAML:

- topic name;
- topic description;
- target subreddit list;
- search keywords;
- strong signal phrases;
- exclusion phrases;
- lookback window;
- max posts per source;
- output Top N.

### Output

- Markdown report.
- SQLite history.
- Optional Telegram or Feishu notification.

Each lead should include title, source, community, URL, score, buying intent, pain summary, evidence, recommended action, created time, upvotes, and comment count.

## 8. User Stories

### Story 1: Daily Scan for Automation Service Demand

As an automation service provider, I want to scan high-relevance communities such as automation, smallbusiness, and Zapier so I can find people looking for consultants, implementation help, or alternatives.

Acceptance criteria:

- target subreddits and keywords are configurable;
- one scan can be run from the CLI;
- Top N results are produced;
- every result includes a source link and next action.

### Story 2: Fast Report Review

As a user, I want a Markdown report or notification summary so I can quickly decide whether there are opportunities worth opening today.

Acceptance criteria:

- the report includes a high-level judgment;
- Top Leads are sorted by priority;
- every lead traces back to the original post;
- the report avoids generic advice.

### Story 3: Low-Cost Debugging

As a developer, I want mock mode to run without Reddit credentials so scoring, report generation, and notifications can be checked quickly.

Acceptance criteria:

- `--mock` mode runs without external API keys;
- sample data produces a report;
- core logic can be exercised locally.

## 9. Functional Requirements

### Configuration

MVP:

- support YAML configuration;
- support multiple topics;
- support topic selection;
- return readable errors for missing configuration.

Later:

- per-topic output directories;
- per-topic notification config;
- weighted keyword groups.

### Data Collection

MVP:

- support Reddit OAuth;
- search by subreddit and keyword;
- filter by `lookback_hours`;
- limit by `max_posts_per_source`;
- deduplicate posts.

Later:

- read rate-limit headers;
- retry fetch failures;
- write fetch status to logs.

### Filtering and Scoring

MVP:

- score include phrase hits;
- penalize or remove exclude phrase hits;
- score keyword hits in title and body;
- include comments, upvotes, and freshness;
- output Top N.

Later:

- topic-specific weights;
- human feedback adjustments;
- already-reviewed deduplication.

### Report Generation

MVP:

- generate Markdown reports;
- summarize fetched count, candidate count, and Top N;
- include evidence and recommended action for each lead.

Later:

- add structured LLM analysis;
- LLM rerank of rule-selected candidates;
- trend observation;
- opportunity classification.

### Storage

MVP:

- use SQLite for scan runs, posts, and signals;
- avoid duplicate source IDs;
- store report paths.

Later:

- CSV export;
- Supabase or Postgres;
- historical trend statistics.

### Notifications

MVP:

- Telegram bot sends full Markdown reports;
- Feishu webhook sends text summaries;
- notifications can be disabled.

Later:

- Feishu interactive cards;
- generic webhooks;
- useful, not useful, and handled buttons;
- retry on notification failure.

## 10. Scoring Strategy

The MVP uses rule-first scoring and does not rely on an LLM for full-data judgment.

Positive signals:

| Signal | Score Impact |
| --- | --- |
| Topic keyword match | +1.5 per hit |
| Strong help phrase | +3 |
| Payment or outsourcing intent | +4 or more |
| Pain phrase | +2 |
| Higher comment count | small boost |
| Fresh post | small boost |
| Highly relevant source | small boost |

Negative signals:

| Signal | Handling |
| --- | --- |
| obvious ad | penalize or remove |
| course promotion | penalize or remove |
| job posting | penalize |
| stale content | remove by lookback window |
| weak title-only match | low priority |

Buying intent levels:

- `strong`: clear payment, hiring, consultant, freelancer, budget, or paid help language;
- `medium`: strong help request plus a concrete business context;
- `weak`: pain exists but solution-seeking is unclear;
- `none`: generic discussion or broad question.

## 11. Success Metrics

| Metric | Target |
| --- | --- |
| Manual review time per run | <= 20 minutes |
| Top 10 open-worthy rate | >= 30% |
| Strong leads per week | >= 3 |
| Report generation failure rate | < 10% |
| Insights without source links | 0 |
| Cost before LLM step | near 0 |

## 12. Technical Plan

Stack:

- Python 3.11+
- Typer CLI
- httpx for HTTP
- Pydantic for models
- PyYAML for config
- SQLite for local storage
- Rich for terminal output

Deployment:

- local CLI;
- GitHub Actions;
- VPS cron or systemd timer;
- future container deployment if needed.

## 13. Risks and Constraints

Data-source risk:

- Reddit API limits and terms can change;
- platform anti-scraping rules may affect availability;
- additional platforms require compliant access.

Mitigation:

- use official APIs or authorized data sources;
- run at low frequency;
- avoid retaining unnecessary raw text;
- keep source adapters pluggable.

Quality risk:

- narrow keywords miss demand;
- broad keywords create noise;
- LLM summaries may become generic;
- rules may bias results.

Mitigation:

- use high-quality source allowlists;
- filter with rules before LLM use;
- keep source evidence;
- require reports to show evidence.

Product-scope risk:

The easiest ways to drift are building a complex UI, adding every platform, building an agent, building a CRM, or turning this into low-code orchestration. The correction principle is simple: first make the system find 3-10 real posts worth opening every day.

## 14. Milestones

Milestone 0: Project definition

- README
- PRD
- architecture
- sample config

Milestone 1: Local MVP

- mock mode;
- Reddit collector;
- rule scoring;
- Markdown report;
- SQLite writes.

Milestone 2: Daily workflow

- GitHub Actions schedule;
- Telegram and Feishu notifications;
- history deduplication;
- error logging.

Milestone 3: LLM analysis

- Top N structured analysis;
- opportunity classification;
- reply suggestions;
- report quality evaluation.

Milestone 4: Multi-platform expansion

- RSS;
- Hacker News;
- Product Hunt;
- GitHub Issues;
- compliant additional platform sources.

## 15. MVP Acceptance Checklist

- [ ] `lead-radar run --mock` generates a report.
- [ ] Every report lead has a URL.
- [ ] New topics can be added in config.
- [ ] Reddit credentials enable real data fetches.
- [ ] The same post is not repeated in results.
- [ ] Top N ordering is reasonable.
- [ ] Telegram or Feishu can send through the unified notification entrypoint.
- [ ] SQLite stores scan history.
- [ ] SQLite stores notification status.
- [ ] Missing API keys produce clear errors.
- [ ] README is sufficient for a future developer to continue the project.
