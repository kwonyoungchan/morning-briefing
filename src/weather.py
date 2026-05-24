import logging
from datetime import date
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5"
_TIMEOUT = 10

_CONDITION_MAP: dict[str, tuple[str, str]] = {
    "Thunderstorm": ("체둥", "⛈️"),
    "Drizzle":      ("비",   "🌧️"),
    "Rain":         ("비",   "🌧️"),
    "Snow":         ("눈",   "❄️"),
    "Mist":         ("안개", "🌫️"),
    "Smoke":        ("안개", "🌫️"),
    "Haze":         ("안개", "🌫️"),
    "Dust":         ("안개", "🌫️"),
    "Fog":          ("안개", "🌫️"),
    "Sand":         ("안개", "🌫️"),
    "Ash":          ("안개", "🌫️"),
    "Squall":       ("체둥", "⛈️"),
    "Tornado":      ("체둥", "⛈️"),
    "Clear":        ("맑음", "☀️"),
    "Clouds":       ("구름", "☁️"),
}


def fetch_weather(settings: dict) -> dict[str, Any] | None:
    """날씨 수집: 설계 명세서 섹션 4.4 참조"""
    weather_cfg = settings.get("weather", {})
    api_key = settings.get("weather_api_key") or _get_env("WEATHER_API_KEY")
    city: str = weather_cfg.get("city", "Seoul")
    units: str = weather_cfg.get("units", "metric")

    common_params = {"q": city, "appid": api_key, "units": units}

    current = _get_current(common_params)
    if current is None:
        return None

    forecast = _get_forecast(common_params)
    temp_min, temp_max, rain_prob = _parse_forecast(forecast, current)

    main_condition = current.get("weather", [{}])[0].get("main", "Clear")
    condition_ko, emoji = _CONDITION_MAP.get(main_condition, ("맑음", "☀️"))

    return {
        "city": city,
        "condition": condition_ko,
        "temp_current": round(current["main"]["temp"]),
        "temp_min": round(temp_min),
        "temp_max": round(temp_max),
        "humidity": current["main"]["humidity"],
        "rain_probability": rain_prob,
        "emoji": emoji,
    }


def _get_current(params: dict) -> dict | None:
    try:
        resp = requests.get(f"{_BASE_URL}/weather", params=params, timeout=_TIMEOUT)
    except requests.Timeout:
        logger.error("OpenWeatherMap /weather 타임아웃 (%ds)", _TIMEOUT)
        return None
    except requests.RequestException as e:
        logger.error("OpenWeatherMap /weather 네트워크 오류: %s", e)
        return None

    if resp.status_code != 200:
        logger.error("OpenWeatherMap /weather HTTP %d — %s", resp.status_code, resp.text)
        return None

    return resp.json()


def _get_forecast(params: dict) -> list[dict]:
    try:
        resp = requests.get(f"{_BASE_URL}/forecast", params=params, timeout=_TIMEOUT)
    except (requests.Timeout, requests.RequestException) as e:
        logger.warning("OpenWeatherMap /forecast 요청 실패 (무시): %s", e)
        return []

    if resp.status_code != 200:
        logger.warning("OpenWeatherMap /forecast HTTP %d (무시)", resp.status_code)
        return []

    return resp.json().get("list", [])


def _parse_forecast(entries: list[dict], current: dict) -> tuple[float, float, int]:
    """오늘 날짜의 예보 항목에서 최저/최고 온도 및 최대 강수확률 추출"""
    today = date.today().isoformat()
    today_entries = [e for e in entries if e.get("dt_txt", "").startswith(today)]

    if not today_entries:
        main = current["main"]
        return main.get("temp_min", main["temp"]), main.get("temp_max", main["temp"]), 0

    temps = [e["main"]["temp"] for e in today_entries]
    rain_prob = max(int(e.get("pop", 0) * 100) for e in today_entries)
    return min(temps), max(temps), rain_prob


def _get_env(key: str) -> str:
    import os
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(f"환경 변수 {key}가 설정되지 않았습니다.")
    return value
