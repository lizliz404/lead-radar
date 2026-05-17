# Deployment Notes

## Current decision

Use FastAPI as the long-term backend boundary now. Streamlit is no longer the main product path; it is kept only as an optional internal/legacy operator console.

Public shape:

- Landing + browser-native instant preview: `https://lead-radar.lizliz.xyz`
- API service: `https://api.lead-radar.lizliz.xyz`
- Optional private operator UI: `https://app.lead-radar.lizliz.xyz` only if protected

This keeps the product boundary clean: Next.js owns presentation and SEO, FastAPI owns scan execution and JSON contracts, Python core owns adapters/scoring/reporting/storage.

## Architecture boundary

- Landing page
  - Tech: Next.js static export
  - Purpose: marketing, SEO, examples, pricing, and low-friction `/preview`
  - Deploy target: Cloudflare Pages
  - Public URL: `https://lead-radar.lizliz.xyz`

- FastAPI service
  - Tech: FastAPI + Pydantic + Uvicorn
  - Purpose: health checks, topic listing, scan execution, review updates, OpenAPI contract
  - Deploy target: Docker on VPS / Fly.io / Render / Railway / Koyeb
  - Recommended URL: `https://api.lead-radar.lizliz.xyz`
  - Protect state-changing endpoints with `LEAD_RADAR_API_TOKEN` before public exposure

- Python core
  - Tech: library modules under `lead_radar/`
  - Purpose: Reddit adapter, scoring profiles, report generation, LLM rerank/report, SQLite storage
  - Used by: FastAPI and CLI

- Optional Streamlit operator UI
  - Tech: Streamlit
  - Purpose: internal visual console only
  - Deploy target: private/protected host if ever needed
  - Status: optional, not the long-term public product UI

Do not put Streamlit under `/preview` with a reverse proxy or iframe. `/preview` stays a static/browser-native demo surface.

## API endpoints

FastAPI app:

```bash
uvicorn lead_radar.api:app --host 0.0.0.0 --port 8000
```

Key routes:

- `GET /health`
- `GET /topics?config_path=config.yaml`
- `POST /scan`
- `POST /reviews`
- `GET /reviews/summary`
- `GET /docs` for Swagger/OpenAPI
- `GET /openapi.json` for typed frontend client generation

Example mock scan:

```bash
curl -sS http://localhost:8000/scan \
  -H 'Content-Type: application/json' \
  -d '{
    "config_path": "config.example.yaml",
    "topic": "paid_demand_signals",
    "mock": true,
    "persist": false
  }'
```

If `LEAD_RADAR_API_TOKEN` is set, state-changing endpoints require:

```http
Authorization: Bearer <token>
```

## Landing page

Build:

```bash
cd web
npm ci
npm run build
```

Output is in `web/out/`. Deploy `out/` to Cloudflare Pages.

Recommended Cloudflare Pages env:

```bash
NEXT_PUBLIC_SITE_URL=https://lead-radar.lizliz.xyz
NEXT_PUBLIC_API_URL=https://api.lead-radar.lizliz.xyz
NEXT_PUBLIC_OPERATOR_APP_URL=
```

`NEXT_PUBLIC_OPERATOR_APP_URL` should normally stay empty unless an internal operator surface is explicitly protected.

## Docker backend

Build:

```bash
docker build -t lead-radar .
```

Run API:

```bash
docker run --rm -p 8000:8000 \
  -e REDDIT_CLIENT_ID=xxx \
  -e REDDIT_CLIENT_SECRET=*** \
  -e REDDIT_USER_AGENT="lead-radar/0.1 by your_username" \
  -e LEAD_RADAR_API_TOKEN=*** \
  -e LEAD_RADAR_CORS_ORIGINS=https://lead-radar.lizliz.xyz \
  lead-radar
```

## Platform choice

### Cloudflare Workers

Not the right primary host for this backend.

Why:

- FastAPI is ASGI/Python and expects a normal Python runtime.
- Reddit scans can be slow, network-heavy, retry-heavy, and eventually async/job-like.
- SQLite/report files fit a small server much better than an edge worker.
- Workers are excellent for edge glue, auth gates, proxying, caching, and lightweight request handling — not for this Python scanning core.

Could use later for:

- edge auth / request filtering
- proxy from `api.lead-radar.lizliz.xyz` to the origin
- lightweight rate limiting
- cached public demo responses

### VPS / Docker / Python PaaS

Best current choice.

Why:

- Native Python/FastAPI runtime
- Easy Docker deployment
- Persistent SQLite/report files are simple
- Cron/background jobs are straightforward
- Easier debugging while Reddit access and scoring quality are still being validated

Recommended now:

- Cloudflare Pages for `lead-radar.lizliz.xyz`
- Dockerized FastAPI on this VPS or a Python-friendly PaaS for `api.lead-radar.lizliz.xyz`
- Cloudflare DNS/proxy in front
- Add Cloudflare Access or a bearer token before exposing real scan endpoints

## Reddit API setup

1. Go to https://www.reddit.com/prefs/apps or the current Reddit API access request form.
2. Create/request access for a read-only/script style application.
3. Set these env vars:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`
4. Verify with:

```bash
python scripts/check_reddit_credentials.py
```

## Environment variables

Minimum for real data:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

Minimum for public API exposure:

- `LEAD_RADAR_API_TOKEN`
- `LEAD_RADAR_CORS_ORIGINS`

Minimum for LLM reports:

- `LEAD_RADAR_LLM_API_KEY`
- `LEAD_RADAR_LLM_BASE_URL`
- `LEAD_RADAR_LLM_MODEL`

Static landing variables:

- `NEXT_PUBLIC_SITE_URL`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_OPERATOR_APP_URL` optional

## Compliance reminder

- No automated DMs, comments, upvotes, or account actions
- No account rotation or ToS circumvention
- Use public posts only
- Store only minimal evidence needed for human review
- Output is decision support, not spam automation
