import logging
from datetime import date, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

_API_URL = "https://newsapi.org/v2/everything"
_TIMEOUT = 10


def fetch_news(settings: dict) -> list[dict[str, Any]]:
    """뉴스 수집: 설계 명세서 섹션 4.3 참조"""
    news_cfg = settings.get("news", {})
    api_key = settings.get("news_api_key") or _get_env("NEWS_API_KEY")

    keywords: list[str] = news_cfg.get("keywords", [])
    language: str = news_cfg.get("language", "ko")
    article_count: int = news_cfg.get("article_count", 5)
    from_date: str = (date.today() - timedelta(days=1)).isoformat()

    params = {
        "apiKey": api_key,
        "q": " OR ".join(keywords),
        "language": language,
        "sortBy": "publishedAt",
        "pageSize": article_count,
        "from": from_date,
    }

    try:
        response = requests.get(_API_URL, params=params, timeout=_TIMEOUT)
    except requests.Timeout:
        logger.error("NewsAPI 요청 타임아웃 (%ds)", _TIMEOUT)
        return []
    except requests.RequestException as e:
        logger.error("NewsAPI 네트워크 오류: %s", e)
        return []

    if response.status_code != 200:
        logger.error("NewsAPI 응답 오류: HTTP %d — %s", response.status_code, response.text)
        return []

    articles = response.json().get("articles", [])
    return [_parse_article(a) for a in articles]


def _parse_article(raw: dict) -> dict[str, Any]:
    description = raw.get("description") or ""
    return {
        "title": raw.get("title", ""),
        "description": description[:100],
        "url": raw.get("url", ""),
        "source": (raw.get("source") or {}).get("name", ""),
        "published_at": raw.get("publishedAt", ""),
    }


def _get_env(key: str) -> str:
    import os
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(f"환경 변수 {key}가 설정되지 않았습니다.")
    return value
