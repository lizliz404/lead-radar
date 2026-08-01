# OG / favicon craft — lead-radar (PASS 2) — 2026-08-01

## Favicon (primary gap)
- `web/public/favicon.svg` — paper plate + simplified radar mark (origin, arcs, rust evidence node `#C76F3A`)
- `web/public/favicon-32.png`, `favicon.ico`, `apple-touch-icon.png` (180)
- Wired in `web/app/layout.tsx` via `metadata.icons` (+ themeColor / authors)

## OG
- Existing `web/public/og-image.png` (1200×630 editorial workflow) kept — not thin; still the share card
- Absolute URLs already via `metadataBase` + `/og-image.png`

## SEO polish
- `SoftwareApplication` JSON-LD on `web/app/page.tsx` extended with `url`, `image`, `author`, `isPartOf`
- Title / description / canonical / robots / OG / Twitter were already present

## Verify (after Hermes deploy)
```bash
curl -sI https://lead-radar.lizliz.xyz/favicon.svg | head
curl -sI https://lead-radar.lizliz.xyz/og-image.png | head
# portfolio FALLBACK iconUrl can flip from og-image → favicon.svg after live
```

No commit / push / deploy from Cursor.
