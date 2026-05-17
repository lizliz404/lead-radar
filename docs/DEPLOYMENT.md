# Deployment Notes

## Decision

Use option **B** for the public product boundary:

- Landing + browser-native instant preview: `https://lead-radar.lizliz.xyz`
- Private/operator Streamlit console: `https://app.lead-radar.lizliz.xyz` or another protected host
- Public API: **none yet**

Do **not** put Streamlit under `/preview` with a reverse proxy or iframe. `/preview` stays a static, instant UX harness on the landing site. Streamlit stays backstage for operator runs until real usage proves that a self-serve workflow is worth building.

FastAPI is **not used yet**. Add it only when the landing page needs a real public API: auth, submitted jobs, multi-user state, async queues, billing, or saved customer workspaces. Until then, FastAPI is premature plumbing.

## Architecture boundary

This repo contains three separate layers. Do not mix them up.

- Landing page
  - Tech: Next.js static export
  - Purpose: marketing, SEO, examples, pricing, and the browser-native `/preview` harness
  - Deploy target: Cloudflare Pages
  - Public URL: `https://lead-radar.lizliz.xyz`

- Operator UI
  - Tech: Streamlit (Python)
  - Purpose: internal console for real scans, review, exports, and debugging
  - Deploy target: VPS / Docker PaaS
  - Recommended URL: `https://app.lead-radar.lizliz.xyz`
  - Access: keep private or protected; do not treat this as the public product UI

- Python core
  - Tech: CLI + library modules
  - Purpose: source adapters, scoring, reports, storage, LLM report generation
  - Deploy target: same host as Operator UI, or scheduled jobs on a VPS

- Public API
  - Tech: future FastAPI service if needed
  - Purpose: public job submission, auth, billing, async status, persisted user workspaces
  - Deploy target: TBD after real data/customer validation
  - Status: intentionally absent

## CTA routing

Current landing CTA behavior:

- Primary CTAs point to `/preview` on the static landing site.
- `/preview` is a simulated browser-native flow, not live Reddit evidence.
- If `NEXT_PUBLIC_OPERATOR_APP_URL` is set at build time, `/preview` can show a secondary link to the protected Streamlit operator console.
- If `NEXT_PUBLIC_OPERATOR_APP_URL` is empty, no operator link is exposed.

This keeps the public experience fast while avoiding the bad pattern of exposing Streamlit as if it were a polished SaaS app. Tiny mercy from future architecture debt.

## Landing page

Build:

```bash
cd web
npx next build
```

Output is in `web/out/`. Deploy `out/` to Cloudflare Pages or any static host.

Recommended Cloudflare Pages env:

```bash
NEXT_PUBLIC_SITE_URL=https://lead-radar.lizliz.xyz
NEXT_PUBLIC_OPERATOR_APP_URL=
```

Set `NEXT_PUBLIC_OPERATOR_APP_URL=https://app.lead-radar.lizliz.xyz` only after the Streamlit operator console is deployed behind appropriate access control.

## Operator UI (Streamlit)

Local:

```bash
streamlit run app.py
```

Docker:

```bash
docker build -t lead-radar .
docker run --rm -p 8501:8501 \
  -e REDDIT_CLIENT_ID=xxx \
  -e REDDIT_CLIENT_SECRET=*** \
  -e REDDIT_USER_AGENT="lead-radar/0.1 by your_username" \
  lead-radar
```

Recommended deployment shape:

- Run Streamlit on a VPS or Docker PaaS.
- Put it behind Cloudflare Access, basic auth, Tailscale, or another protection layer.
- Map it to `app.lead-radar.lizliz.xyz` only when protected.
- Do not iframe it into the landing page.

## Reddit API setup

1. Go to https://www.reddit.com/prefs/apps
2. Create a "script" type app
3. Copy Client ID and Client Secret
4. Set `REDDIT_USER_AGENT` to something descriptive
5. Fill `.env` (see `.env.example`)
6. Verify with:
   ```bash
   python scripts/check_reddit_credentials.py
   ```

## Environment variables

See `.env.example` for the full list. Minimum for real data:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

Minimum for LLM reports:

- `LEAD_RADAR_LLM_API_KEY`
- `LEAD_RADAR_LLM_BASE_URL`
- `LEAD_RADAR_LLM_MODEL`

Static landing variables:

- `NEXT_PUBLIC_SITE_URL`
- `NEXT_PUBLIC_OPERATOR_APP_URL` (optional; expose only a protected operator URL)

## Platform fit

- **Cloudflare Pages**: landing page and `/preview` static harness
- **Cloudflare Workers / FastAPI**: future public API only; not needed now
- **Zeabur / Render / Fly.io / Railway / Koyeb**: good for Docker/Streamlit
- **VPS (this server)**: simplest for cron + SQLite + private operator runs
- **Netlify / Vercel**: fine for static landing, not suitable for the Python backend

## When to add FastAPI

Add FastAPI only when at least one of these becomes true:

- strangers submit scans from the landing page
- jobs need async status/progress polling
- results need persisted user accounts or workspaces
- billing/auth is needed
- Streamlit becomes a bottleneck for validated customer delivery

Until then, the clean boundary is: static preview for public UX, Streamlit for operator execution, CLI/core for real work.

## Scheduled scans

Use `systemd` timer or `cron` on the VPS, or GitHub Actions if you prefer managed scheduling. Example cron:

```cron
0 9 * * 1 cd /home/ubuntu/projects/lead-radar && python -m lead_radar.cli run --config config.yaml --topic paid_demand_signals
```

## Compliance reminder

- No automated DMs, comments, or upvotes
- No account rotation or ToS circumvention
- Output is human decision support, not a spam machine
- Only public posts; no private subreddits or messages
