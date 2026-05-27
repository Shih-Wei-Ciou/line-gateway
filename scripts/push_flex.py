"""
Push a Flex Message to a single LINE user.

Usage:
  python scripts/push_flex.py --to <UID> --url <URL> [--title 標題] [--label 開啟]
"""
import argparse
import os
import sys

import requests
from dotenv import load_dotenv

LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"
GOLD = "#C9A961"


def build_flex(title: str, url: str, label: str) -> dict:
    return {
        "type": "flex",
        "altText": title,
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "lg",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": url,
                        "size": "xs",
                        "color": "#999999",
                        "wrap": True,
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": GOLD,
                        "action": {"type": "uri", "label": label, "uri": url},
                    }
                ],
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Push a Flex Message to a LINE user.")
    parser.add_argument("--to", required=True, help="LINE user ID, e.g. Uxxxxxxxx...")
    parser.add_argument("--url", required=True, help="URL the button opens")
    parser.add_argument("--title", default="拜拜通", help="Card title (default: 拜拜通)")
    parser.add_argument("--label", default="開啟", help="Button label (default: 開啟)")
    args = parser.parse_args()

    load_dotenv()
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("ERROR: LINE_CHANNEL_ACCESS_TOKEN not set in .env")

    payload = {
        "to": args.to,
        "messages": [build_flex(args.title, args.url, args.label)],
    }

    print(f"To:    {args.to}")
    print(f"Title: {args.title}")
    print(f"URL:   {args.url}")
    print(f"Label: {args.label}")

    response = requests.post(
        LINE_PUSH_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )

    if response.status_code == 200:
        print("\nSuccess. Check your LINE chat with the bot.")
    else:
        print(f"\nERROR {response.status_code}: {response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
