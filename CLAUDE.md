# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Morning Briefing Bot** — a serverless Python 3.11 system that runs daily via GitHub Actions (UTC 22:00 = KST 07:00), fetches news from NewsAPI.org and weather from OpenWeatherMap, and posts a formatted Discord Embed to a Webhook.

The full design spec is in `morning-briefing-design.md`.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot locally (requires env vars set)
python src/main.py

# Required environment variables
export NEWS_API_KEY=...
export WEATHER_API_KEY=...
export DISCORD_WEBHOOK_URL=...
```

## Architecture

```
GitHub Actions cron (UTC 22:00)
    └─ main.py            # orchestrator: load config → fetch → format → send
        ├─ news.py        # NewsAPI /v2/everything → list of article dicts
        ├─ weather.py     # OWM /weather + /forecast → single weather dict
        ├─ formatter.py   # combine into Discord Embed payload (JSON)
        └─ notifier.py    # HTTP POST to Webhook, retry up to 3×
```

Config lives in `config/settings.yaml` (keywords, city, language, article count) — no code changes needed for tuning behavior.

## Key Design Decisions

**Partial failure policy**: news failure or weather failure each produce a degraded-but-sent message (using fallback text). Only a Discord send failure triggers `exit 1` and fails the Actions run.

**Embed color** is driven by rain probability: ≤30% yellow (`16776960`), 31–60% blue (`3447003`), ≥61% gray (`9807270`).

**Retry**: `notifier.py` retries up to 3 times with 5s gaps; on HTTP 429 it reads `retry_after` header instead.

**API quotas** (free tier): NewsAPI 100 req/day (uses 1), OpenWeatherMap 1000 req/day (uses 2). Both called with 10s timeout.

## GitHub Actions Secrets

| Secret | Purpose |
|---|---|
| `NEWS_API_KEY` | NewsAPI.org |
| `WEATHER_API_KEY` | OpenWeatherMap |
| `DISCORD_WEBHOOK_URL` | Discord Webhook |
