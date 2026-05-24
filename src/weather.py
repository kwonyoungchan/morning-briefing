import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

_NCST_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
_FCST_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
_TIMEOUT = 10
_KST = timezone(timedelta(hours=9))

# 단기예보 발표 시각 (KST, HHMM 정수)
_FCST_BASE_TIMES = [200, 500, 800, 1100, 1400, 1700, 2000, 2300]


def fetch_weather(settings: dict) -> dict[str, Any] | None:
    """날씨 수집: 기상청 단기예보 API (설계 명세서 섹션 4.4 참조)"""
    weather_cfg = settings.get("weather", {})
    api_key = settings.get("weather_api_key") or _get_env("WEATHER_API_KEY")
    # data.go.kr에서 발급된 키는 URL 인코딩 상태일 수 있으므로 디코딩 후 사용
    api_key = urllib.parse.unquote(api_key)

    nx: int = weather_cfg.get("nx", 60)    # 기상청 격자 X (서울 기본값)
    ny: int = weather_cfg.get("ny", 127)   # 기상청 격자 Y (서울 기본값)
    city: str = weather_cfg.get("city", "서울")

    now_kst = datetime.now(_KST)

    current = _get_current(api_key, nx, ny, now_kst)
    if current is None:
        return None

    forecast = _get_forecast(api_key, nx, ny, now_kst)

    pty = int(current.get("PTY", 0))
    sky = int(forecast.get("SKY", 1))
    condition, emoji = _get_condition(sky, pty)

    return {
        "city": city,
        "condition": condition,
        "temp_current": round(float(current.get("T1H", 0))),
        "temp_min": round(float(forecast.get("TMN", current.get("T1H", 0)))),
        "temp_max": round(float(forecast.get("TMX", current.get("T1H", 0)))),
        "humidity": int(current.get("REH", 0)),
        "rain_probability": int(forecast.get("POP", 0)),
        "emoji": emoji,
    }


def _get_current(api_key: str, nx: int, ny: int, now_kst: datetime) -> dict | None:
    """초단기실황 조회 — T1H(기온), REH(습도), PTY(강수형태)"""
    adjusted = now_kst - timedelta(minutes=10)
    base_date = adjusted.strftime("%Y%m%d")
    base_time = adjusted.strftime("%H00")

    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    try:
        resp = requests.get(_NCST_URL, params=params, timeout=_TIMEOUT)
    except requests.Timeout:
        logger.error("기상청 초단기실황 타임아웃 (%ds)", _TIMEOUT)
        return None
    except requests.RequestException as e:
        logger.error("기상청 초단기실황 네트워크 오류: %s", e)
        return None

    if resp.status_code != 200:
        logger.error("기상청 초단기실황 HTTP %d — %s", resp.status_code, resp.text)
        return None

    body = resp.json().get("response", {})
    if body.get("header", {}).get("resultCode") != "00":
        logger.error("기상청 초단기실황 오류: %s", body.get("header", {}))
        return None

    items = body.get("body", {}).get("items", {}).get("item", [])
    return {item["category"]: item["obsrValue"] for item in items}


def _get_forecast(api_key: str, nx: int, ny: int, now_kst: datetime) -> dict:
    """단기예보 조회 — TMN(최저기온), TMX(최고기온), POP(강수확률), SKY(하늘상태)"""
    base_date, base_time = _latest_fcst_base(now_kst)
    today = now_kst.strftime("%Y%m%d")

    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    try:
        resp = requests.get(_FCST_URL, params=params, timeout=_TIMEOUT)
    except (requests.Timeout, requests.RequestException) as e:
        logger.warning("기상청 단기예보 요청 실패 (무시): %s", e)
        return {}

    if resp.status_code != 200:
        logger.warning("기상청 단기예보 HTTP %d (무시)", resp.status_code)
        return {}

    body = resp.json().get("response", {})
    if body.get("header", {}).get("resultCode") != "00":
        logger.warning("기상청 단기예보 오류: %s (무시)", body.get("header", {}))
        return {}

    items = body.get("body", {}).get("items", {}).get("item", [])
    today_items = [i for i in items if i.get("fcstDate") == today]

    result: dict[str, Any] = {}

    # 일 최저/최고 기온
    for item in today_items:
        cat = item["category"]
        if cat == "TMN":
            result["TMN"] = float(item["fcstValue"])
        elif cat == "TMX":
            result["TMX"] = float(item["fcstValue"])

    # 오늘 최대 강수확률
    pops = [int(i["fcstValue"]) for i in today_items if i["category"] == "POP"]
    if pops:
        result["POP"] = max(pops)

    # 현재 시각에 가장 가까운 하늘상태
    now_hhmm = int(now_kst.strftime("%H%M"))
    sky_items = [i for i in today_items if i["category"] == "SKY"]
    if sky_items:
        closest = min(sky_items, key=lambda x: abs(int(x["fcstTime"]) - now_hhmm))
        result["SKY"] = int(closest["fcstValue"])

    return result


def _latest_fcst_base(now_kst: datetime) -> tuple[str, str]:
    """단기예보 가장 최근 발표 시각 반환 (발표 후 10분 여유 적용)"""
    current_hhmm = now_kst.hour * 100 + now_kst.minute - 10

    selected = None
    for t in _FCST_BASE_TIMES:
        if t <= current_hhmm:
            selected = t

    if selected is None:
        prev = now_kst - timedelta(days=1)
        return prev.strftime("%Y%m%d"), "2300"

    return now_kst.strftime("%Y%m%d"), f"{selected:04d}"


def _get_condition(sky: int, pty: int) -> tuple[str, str]:
    """SKY(하늘상태) + PTY(강수형태) → 한국어 설명, 이모지"""
    if pty == 1:
        return "비", "🌧️"
    if pty == 2:
        return "비/눈", "🌨️"
    if pty == 3:
        return "눈", "❄️"
    if pty == 4:
        return "소나기", "🌦️"
    # PTY 0(없음): 하늘상태 기준
    if sky == 1:
        return "맑음", "☀️"
    if sky == 3:
        return "구름많음", "⛅"
    return "흐림", "☁️"


def _get_env(key: str) -> str:
    import os
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(f"환경 변수 {key}가 설정되지 않았습니다.")
    return value
