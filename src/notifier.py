import requests


def send_to_discord(webhook_url: str, payload: dict) -> None:
    """Discord Webhook 전송: 설계 명세서 섹션 4.6 참조

    재시도 전략: 최대 3회, 간격 5초, 429 시 retry_after 헤더 준수
    """
    # TODO: implement
    raise NotImplementedError
