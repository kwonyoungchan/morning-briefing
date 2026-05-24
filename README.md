# Morning Briefing Bot

매일 아침 7시(KST), 관심사 기반 뉴스와 서울 날씨를 Discord 채널로 자동 전송하는 GitHub Actions 봇입니다.

## 실행 환경

- Python 3.11
- GitHub Actions (서버리스, 별도 서버 불필요)

## 로컬 실행

```bash
pip install -r requirements.txt

export NEWS_API_KEY=...
export WEATHER_API_KEY=...
export DISCORD_WEBHOOK_URL=...

python src/main.py
```

## GitHub Secrets 설정

| Secret | 설명 |
|---|---|
| `NEWS_API_KEY` | [NewsAPI.org](https://newsapi.org) API 키 |
| `WEATHER_API_KEY` | [OpenWeatherMap](https://openweathermap.org/api) API 키 |
| `DISCORD_WEBHOOK_URL` | Discord 채널 Webhook URL |

## 설정 변경

`config/settings.yaml`에서 관심 키워드, 도시, 뉴스 언어, 기사 수를 코드 수정 없이 변경할 수 있습니다.

## 상세 설계

[morning-briefing-design.md](./morning-briefing-design.md) 참조
