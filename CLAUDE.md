# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Morning Briefing Bot** — a serverless Python 3.11 system that runs daily via GitHub Actions (UTC 22:00 = KST 07:00), fetches news from NewsAPI.org and weather from the Korea Meteorological Administration (기상청) short-term forecast API, and posts a formatted Discord Embed to a Webhook.

The full design spec is in `morning-briefing-design.md`.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot locally (requires env vars set)
python src/main.py

# Required environment variables
export NEWS_API_KEY=...          # NewsAPI.org
export WEATHER_API_KEY=...       # 기상청 단기예보 API (data.go.kr)
export DISCORD_WEBHOOK_URL=...
```

## Architecture

```
GitHub Actions cron (UTC 22:00)
    └─ main.py            # orchestrator: load config → fetch → format → send
        ├─ news.py        # NewsAPI /v2/everything → list of article dicts
        ├─ weather.py     # 기상청 getUltraSrtNcst + getVilageFcst → single weather dict
        ├─ formatter.py   # combine into Discord Embed payload (JSON)
        └─ notifier.py    # HTTP POST to Webhook, retry up to 3×
```

Config lives in `config/settings.yaml` (keywords, city display name, nx/ny grid coords, language, article count).

## Key Design Decisions

**Weather API**: Uses two KMA endpoints — `getUltraSrtNcst` (초단기실황) for current T1H/REH/PTY, and `getVilageFcst` (단기예보) for TMN/TMX/POP/SKY. Location is specified as KMA grid coordinates (`nx`, `ny`) in settings.yaml, not city name.

**Partial failure policy**: news failure or weather failure each produce a degraded-but-sent message (using fallback text). Only a Discord send failure triggers `exit 1` and fails the Actions run.

**Embed color** is driven by rain probability: ≤30% yellow (`16776960`), 31–60% blue (`3447003`), ≥61% gray (`9807270`).

**Retry**: `notifier.py` retries up to 3 times with 5s gaps; on HTTP 429 it reads `retry_after` header instead.

**KMA API key**: The key from data.go.kr is URL-encoded; `weather.py` applies `urllib.parse.unquote()` before use.

## GitHub Actions Secrets

| Secret | Purpose |
|---|---|
| `NEWS_API_KEY` | NewsAPI.org |
| `WEATHER_API_KEY` | 기상청 단기예보 API (data.go.kr 발급) |
| `DISCORD_WEBHOOK_URL` | Discord Webhook |

## KMA Grid Coordinates (주요 도시)

| 도시 | nx | ny |
|---|---|---|
| 서울 | 60 | 127 |
| 부산 | 98 | 76 |
| 대구 | 89 | 90 |
| 인천 | 55 | 124 |
| 대전 | 67 | 100 |
| 광주 | 58 | 74 |
| 제주 | 52 | 38 |
