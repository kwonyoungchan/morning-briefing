import logging
import time

import requests

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_INTERVAL = 5


def send_to_discord(webhook_url: str, payload: dict) -> None:
    """Discord Webhook 전송: 설계 명세서 섹션 4.6 참조

    재시도 전략: 최대 3회, 간격 5초, 429 시 retry_after 헤더 준수
    3회 실패 시 RuntimeError raise → main.py에서 exit(1) 처리
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
        except requests.Timeout:
            logger.error("[%d/%d] Discord Webhook 타임아웃", attempt, _MAX_RETRIES)
            _wait_before_retry(attempt, _RETRY_INTERVAL)
            continue
        except requests.RequestException as e:
            logger.error("[%d/%d] Discord Webhook 네트워크 오류: %s", attempt, _MAX_RETRIES, e)
            _wait_before_retry(attempt, _RETRY_INTERVAL)
            continue

        if resp.status_code in (200, 204):
            logger.info("Discord 전송 성공 (HTTP %d)", resp.status_code)
            return

        if resp.status_code == 429:
            retry_after = _parse_retry_after(resp)
            logger.warning("[%d/%d] Discord Rate Limit — %.1fs 대기", attempt, _MAX_RETRIES, retry_after)
            time.sleep(retry_after)
            continue

        logger.error("[%d/%d] Discord Webhook HTTP %d — %s", attempt, _MAX_RETRIES, resp.status_code, resp.text)
        _wait_before_retry(attempt, _RETRY_INTERVAL)

    raise RuntimeError(f"Discord 전송 {_MAX_RETRIES}회 실패")


def _parse_retry_after(resp: requests.Response) -> float:
    try:
        return float(resp.headers.get("retry_after") or resp.json().get("retry_after", _RETRY_INTERVAL))
    except (ValueError, AttributeError):
        return float(_RETRY_INTERVAL)


def _wait_before_retry(attempt: int, interval: int) -> None:
    if attempt < _MAX_RETRIES:
        time.sleep(interval)
