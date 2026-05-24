import logging
import os
import sys
from pathlib import Path

import yaml

from formatter import build_payload
from news import fetch_news
from notifier import send_to_discord
from weather import fetch_weather

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


def load_settings(path: Path = _SETTINGS_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    # API 키 미설정 시 즉시 종료
    for key in ("NEWS_API_KEY", "WEATHER_API_KEY", "DISCORD_WEBHOOK_URL"):
        if not os.environ.get(key):
            logger.error("환경 변수 %s가 설정되지 않았습니다.", key)
            sys.exit(1)

    settings = load_settings()

    # 뉴스 수집 — 실패 시 빈 리스트로 계속 진행
    try:
        articles = fetch_news(settings)
        logger.info("뉴스 수집 완료: %d건", len(articles))
    except Exception as e:
        logger.error("뉴스 수집 실패 (무시하고 계속): %s", e)
        articles = []

    # 날씨 수집 — 실패 시 None으로 계속 진행
    try:
        weather = fetch_weather(settings)
        if weather:
            logger.info("날씨 수집 완료: %s %s", weather["city"], weather["condition"])
        else:
            logger.warning("날씨 수집 실패 — 대체 텍스트로 대응")
    except Exception as e:
        logger.error("날씨 수집 실패 (무시하고 계속): %s", e)
        weather = None

    payload = build_payload(weather, articles)

    # Discord 전송 실패 시 exit(1)
    try:
        send_to_discord(os.environ["DISCORD_WEBHOOK_URL"], payload)
    except RuntimeError as e:
        logger.error("Discord 전송 최종 실패: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
