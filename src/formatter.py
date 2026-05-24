from datetime import datetime, timezone
from typing import Any

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

_COLOR_SUNNY = 16776960   # 노란색: 강수확률 0~30%
_COLOR_CLOUDY = 3447003   # 파란색: 강수확률 31~60%
_COLOR_RAINY  = 9807270   # 회색:   강수확률 61~100%


def build_payload(
    weather: dict[str, Any] | None,
    articles: list[dict[str, Any]],
) -> dict:
    """Discord Embed payload 생성: 설계 명세서 섹션 4.5 참조"""
    now = datetime.now(tz=timezone.utc)
    rain_prob = (weather or {}).get("rain_probability", 0)
    color = _pick_color(rain_prob)

    title_emoji = (weather or {}).get("emoji", "🌤️")
    title = f"{title_emoji} {_format_date(now)} 모닝 브리핑"

    fields = [
        _weather_field(weather),
        _news_field(articles),
    ]

    return {
        "username": "Morning Briefing Bot",
        "embeds": [
            {
                "title": title,
                "color": color,
                "fields": fields,
                "footer": {"text": "NewsAPI · OpenWeatherMap | 매일 오전 7시 업데이트"},
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        ],
    }


def _weather_field(weather: dict[str, Any] | None) -> dict:
    if weather is None:
        return {
            "name": "🌤️ 오늘의 날씨",
            "value": "날씨 정보를 불러올 수 없습니다.",
            "inline": False,
        }

    line1 = (
        f"{weather['emoji']} {weather['condition']}  |  "
        f"현재 {weather['temp_current']}°C  |  "
        f"최저 {weather['temp_min']}°C / 최고 {weather['temp_max']}°C"
    )
    line2 = f"💧 습도 {weather['humidity']}%  |  🌂 강수확률 {weather['rain_probability']}%"

    return {
        "name": f"🌤️ 오늘의 날씨 — {weather['city']}",
        "value": f"{line1}\n{line2}",
        "inline": False,
    }


def _news_field(articles: list[dict[str, Any]]) -> dict:
    if not articles:
        value = "오늘 관련 뉴스가 없습니다."
    else:
        lines = [
            f"{i}. [{a['title']}]({a['url']}) — {a['source']}"
            for i, a in enumerate(articles, start=1)
        ]
        value = "\n".join(lines)

    return {
        "name": "📰 오늘의 뉴스",
        "value": value,
        "inline": False,
    }


def _pick_color(rain_probability: int) -> int:
    if rain_probability <= 30:
        return _COLOR_SUNNY
    if rain_probability <= 60:
        return _COLOR_CLOUDY
    return _COLOR_RAINY


def _format_date(dt: datetime) -> str:
    # KST = UTC+9
    kst_hour = (dt.hour + 9) % 24
    kst = dt.replace(hour=kst_hour)
    weekday = _WEEKDAYS[kst.weekday()]
    return f"{kst.year}년 {kst.month}월 {kst.day}일 {weekday}요일"
