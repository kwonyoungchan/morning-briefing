import sys
import yaml

from news import fetch_news
from weather import fetch_weather
from formatter import build_payload
from notifier import send_to_discord


def load_settings(path: str = "config/settings.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    # TODO: 1. load_settings()
    # TODO: 2. fetch_news() — 실패 시 빈 리스트로 계속 진행
    # TODO: 3. fetch_weather() — 실패 시 None으로 계속 진행
    # TODO: 4. build_payload()
    # TODO: 5. send_to_discord() — 실패 시 sys.exit(1)
    raise NotImplementedError


if __name__ == "__main__":
    main()
