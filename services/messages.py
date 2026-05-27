"""
Messages — LINE 訊息測試包的高階組合層

對外暴露三個 send_*：
  - send_welcome_sequence(line_user_id): 加好友完整流程
  - send_test_message(line_user_id, type): 測試訊息分發
  - send_location_message(line_user_id): 推三官寶殿位置

底層用 line-bot-sdk v3 的 push_message。
"""
from __future__ import annotations

import logging
import os
from typing import Callable

import requests
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    LocationMessage,
    MessageAction,
    MessagingApi,
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    StickerMessage,
    TextMessage,
)

from services.flex_templates import get_explore_carousel, get_single_card

logger = logging.getLogger(__name__)

# Loading Animation API（line-bot-sdk 3.5 還沒包進 SDK，直接打 HTTP）
LOADING_ANIMATION_URL = "https://api.line.me/v2/bot/chat/loading/start"

# ── 常數 ────────────────────────────────────────────────────────────────────
WELCOME_TEXT = (
    "歡迎您加入緣引拜拜通\n\n"
    "這是一座以線上方式陪你參拜的小廟。\n"
    "輸入「探索」可以看四個主題，\n"
    "或直接點下方圖文選單開始。"
)

SIMPLE_GREETING = "你好，這裡是緣引拜拜通。\n下方有四個主題，往右滑試試。"

STICKER_PACKAGE_ID = "446"
STICKER_ID = "1988"

# 三官寶殿 — 台南白河（近似座標，未來可換成 DB 實值）
LOCATION_TEMPLE = {
    "title": "三官寶殿",
    "address": "台南市白河區竹門里崁仔頭8號",
    "latitude": 23.3528,
    "longitude": 120.4150,
}


# ── LINE API 客戶端 ─────────────────────────────────────────────────────────
def _api() -> tuple[Configuration, MessagingApi, ApiClient]:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN is not set in .env")
    cfg = Configuration(access_token=token)
    client = ApiClient(cfg)
    return cfg, MessagingApi(client), client


def _push(line_user_id: str, messages: list) -> None:
    """送出 push_message（最多 5 則）。"""
    if len(messages) > 5:
        raise ValueError(f"push_message accepts up to 5 messages, got {len(messages)}")
    _, api, client = _api()
    try:
        api.push_message(PushMessageRequest(to=line_user_id, messages=messages))
    finally:
        client.close()


def _show_loading(line_user_id: str, seconds: int = 5) -> None:
    """
    LINE Loading Animation。直接打 HTTP（SDK 3.5 還沒包此 API）。
    僅對「使用者主動聊過天」的對象有效；新加好友尚未發過訊息可能會 400。
    """
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN is not set in .env")
    try:
        resp = requests.post(
            LOADING_ANIMATION_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"chatId": line_user_id, "loadingSeconds": seconds},
            timeout=5,
        )
        if resp.status_code >= 400:
            logger.warning(
                "[messages] loading animation failed: %d %s",
                resp.status_code, resp.text,
            )
    except Exception as exc:
        logger.warning("[messages] loading animation request error: %s", exc)


# ── 公開入口 ────────────────────────────────────────────────────────────────
def send_welcome_sequence(line_user_id: str) -> None:
    """
    加好友完整流程：
      1. show_loading_animation 5 秒
      2. push 文字 + 貼圖 + Carousel + Quick Reply（一次 push，4 則訊息）
    """
    _show_loading(line_user_id, seconds=5)

    quick_reply = QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="探索拜拜通", text="探索")),
            QuickReplyItem(action=MessageAction(label="廟宇地圖", text="廟宇")),
            QuickReplyItem(action=MessageAction(label="我有問題", text="我有問題")),
        ]
    )

    messages = [
        TextMessage(text=WELCOME_TEXT),
        StickerMessage(package_id=STICKER_PACKAGE_ID, sticker_id=STICKER_ID),
        get_explore_carousel(),
        TextMessage(
            text="想看哪個？或者跟我說「我有問題」。",
            quick_reply=quick_reply,
        ),
    ]
    _push(line_user_id, messages)


def send_test_message(line_user_id: str, msg_type: str) -> None:
    """
    測試訊息分發。msg_type 支援：
      explore | welcome | quick_reply | location | sticker | loading_test
    """
    dispatch: dict[str, Callable[[str], None]] = {
        "explore": _send_explore,
        "welcome": send_welcome_sequence,
        "quick_reply": _send_quick_reply_only,
        "location": send_location_message,
        "sticker": _send_sticker_only,
        "loading_test": _send_loading_only,
    }
    fn = dispatch.get(msg_type)
    if not fn:
        raise ValueError(
            f"unknown msg_type: {msg_type!r}; valid: {list(dispatch)}"
        )
    fn(line_user_id)


def send_location_message(line_user_id: str) -> None:
    """推三官寶殿位置（用 LINE 內建 Location Message，會在聊天室顯示地圖縮圖）。"""
    msg = LocationMessage(
        title=LOCATION_TEMPLE["title"],
        address=LOCATION_TEMPLE["address"],
        latitude=LOCATION_TEMPLE["latitude"],
        longitude=LOCATION_TEMPLE["longitude"],
    )
    _push(line_user_id, [msg])


# ── 子流程 ──────────────────────────────────────────────────────────────────
def _send_explore(line_user_id: str) -> None:
    _push(line_user_id, [get_explore_carousel()])


def _send_quick_reply_only(line_user_id: str) -> None:
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="廟宇地圖", text="廟宇")),
            QuickReplyItem(action=MessageAction(label="神明速查", text="神明")),
            QuickReplyItem(action=MessageAction(label="拜拜指南", text="指南")),
            QuickReplyItem(action=MessageAction(label="附近的廟", text="附近")),
        ]
    )
    _push(
        line_user_id,
        [TextMessage(text="想看哪個主題？", quick_reply=quick_reply)],
    )


def _send_sticker_only(line_user_id: str) -> None:
    _push(
        line_user_id,
        [StickerMessage(package_id=STICKER_PACKAGE_ID, sticker_id=STICKER_ID)],
    )


def _send_loading_only(line_user_id: str) -> None:
    _show_loading(line_user_id, seconds=5)


# ── Webhook 用：單張卡片 + 簡化歡迎 ─────────────────────────────────────
def send_card(line_user_id: str, theme: str) -> None:
    """推單張卡片。theme ∈ {"welcome", "temples", "deities", "guides", "nearby"}."""
    _push(line_user_id, [get_single_card(theme)])


def send_carousel(line_user_id: str) -> None:
    """推 Flex Carousel（探索 5 卡）。"""
    _push(line_user_id, [get_explore_carousel()])


def send_simple_greeting(line_user_id: str) -> None:
    """text 觸發的簡化版打招呼，不做 loading / sticker，只送文字 + Carousel。"""
    _push(
        line_user_id,
        [
            TextMessage(text=SIMPLE_GREETING),
            get_explore_carousel(),
        ],
    )
