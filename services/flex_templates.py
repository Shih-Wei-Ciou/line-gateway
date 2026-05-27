"""
Flex Templates — LINE 訊息測試包

提供：
  - get_explore_carousel(): 5 張卡片的 Carousel（總覽 + 4 主題）
  - get_single_card(theme): 單張卡片，theme ∈
        {"welcome", "temples", "deities", "guides", "nearby"}

設計風格：莊重襯線、白底黑字。
URL 一律帶 ?from=line&utm_source=flex&utm_medium={theme}
基礎網址由環境變數 WEBAPP_BASE_URL 提供。
"""
from __future__ import annotations

import os

from linebot.v3.messaging import (
    FlexBox,
    FlexBubble,
    FlexButton,
    FlexCarousel,
    FlexMessage,
    FlexSeparator,
    FlexText,
    URIAction,
)

# ── 設計常數 ────────────────────────────────────────────────────────────────
BG_WHITE = "#FFFFFF"
BORDER = "#E8E0D4"
TITLE = "#1A1612"
SUBTITLE = "#6A6058"
BUTTON_BG = "#1A1612"

# ── 卡片內容 ────────────────────────────────────────────────────────────────
CARDS: dict[str, dict] = {
    "welcome": {
        "title": "探索拜拜通",
        "subtitle": "開始你的線上參拜",
        "hint": "往右滑探索四個主題",
        "button": "開始",
        "path": "/",
    },
    "temples": {
        "title": "廟宇地圖",
        "subtitle": "找一座你想去的廟",
        "button": "探索",
        "path": "/temples",
    },
    "deities": {
        "title": "神明速查",
        "subtitle": "認識每位神明的故事",
        "button": "探索",
        "path": "/deities",
    },
    "guides": {
        "title": "拜拜指南",
        "subtitle": "從第一次到熟門熟路",
        "button": "探索",
        "path": "/guides",
    },
    "nearby": {
        "title": "附近的廟",
        "subtitle": "用座標找你身邊的香火",
        "button": "探索",
        "path": "/temples/nearby",
    },
}

CAROUSEL_ORDER: list[str] = ["welcome", "temples", "deities", "guides", "nearby"]


# ── 工具 ────────────────────────────────────────────────────────────────────
def _build_url(path: str, theme: str) -> str:
    base = os.getenv("WEBAPP_BASE_URL", "").rstrip("/")
    return f"{base}{path}?from=line&utm_source=flex&utm_medium={theme}"


def _bubble(theme: str) -> FlexBubble:
    card = CARDS[theme]
    url = _build_url(card["path"], theme)

    body_contents: list = [
        FlexText(text=card["title"], weight="bold", size="xl", color=TITLE, wrap=True),
        FlexText(
            text=card["subtitle"],
            size="sm",
            color=SUBTITLE,
            margin="md",
            wrap=True,
        ),
    ]

    if hint := card.get("hint"):
        body_contents.append(
            FlexText(text=hint, size="sm", color=SUBTITLE, margin="xs", wrap=True)
        )
        body_contents.append(
            FlexText(
                text="→  →",
                size="lg",
                color=SUBTITLE,
                margin="lg",
                align="end",
            )
        )

    return FlexBubble(
        size="kilo",
        body=FlexBox(
            layout="vertical",
            padding_all="20px",
            background_color=BG_WHITE,
            contents=body_contents,
        ),
        footer=FlexBox(
            layout="vertical",
            padding_all="20px",
            padding_top="none",
            contents=[
                FlexSeparator(color=BORDER),
                FlexButton(
                    style="primary",
                    color=BUTTON_BG,
                    margin="md",
                    height="sm",
                    action=URIAction(label=card["button"], uri=url),
                ),
            ],
        ),
    )


# ── 公開入口 ────────────────────────────────────────────────────────────────
def get_explore_carousel() -> FlexMessage:
    """5 張卡片的 Carousel：總覽 → 廟宇 → 神明 → 指南 → 附近。"""
    bubbles = [_bubble(theme) for theme in CAROUSEL_ORDER]
    return FlexMessage(
        alt_text="探索拜拜通 - 開始你的線上參拜",
        contents=FlexCarousel(contents=bubbles),
    )


def get_single_card(theme: str) -> FlexMessage:
    """單張卡片。theme 必須在 CARDS 鍵裡。"""
    if theme not in CARDS:
        raise ValueError(f"unknown theme: {theme!r}; valid: {list(CARDS)}")
    card = CARDS[theme]
    return FlexMessage(
        alt_text=f"{card['title']} - {card['subtitle']}",
        contents=_bubble(theme),
    )
