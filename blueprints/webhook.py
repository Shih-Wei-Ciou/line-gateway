"""
LINE Webhook Blueprint — Stage 2: 使用者識別與資料庫
POST /webhook
"""
import os
import logging

from flask import Blueprint, request, abort
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import (
    MessageEvent,
    FollowEvent,
    UnfollowEvent,
    PostbackEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.exceptions import InvalidSignatureError

from services.line_user_service import handle_follow, handle_unfollow, update_last_seen
from services.messages import (
    send_card,
    send_carousel,
    send_simple_greeting,
)
from services.postback_service import handle_postback


# 關鍵字 → 動作的對應表。priority 由上而下，第一個命中即觸發。
# 使用 `in` 比對（substring），所以「拜拜通」會優先於「拜拜」。
KEYWORD_ROUTES: list[tuple[tuple[str, ...], str]] = [
    (("探索", "主題", "拜拜通"), "carousel"),
    (("廟宇", "廟"), "temples"),
    (("神明", "神"), "deities"),
    (("指南", "拜拜"), "guides"),
    (("附近",), "nearby"),
    (("你好", "hi", "Hi", "hello", "Hello", "嗨"), "greet"),
]

logger = logging.getLogger(__name__)

bp = Blueprint("webhook", __name__)


@bp.route("/webhook", methods=["POST"])
def webhook():
    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        events = WebhookParser(channel_secret).parse(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature — 簽章驗證失敗")
        abort(400)

    configuration = Configuration(access_token=channel_access_token)

    for event in events:
        if isinstance(event, MessageEvent):
            _handle_message(event, configuration)
        elif isinstance(event, FollowEvent):
            _handle_follow(event, configuration)
        elif isinstance(event, UnfollowEvent):
            _handle_unfollow(event)
        elif isinstance(event, PostbackEvent):
            _handle_postback(event, configuration)

    return "OK", 200


# ── 事件處理 ──────────────────────────────────────────────

def _handle_message(event: MessageEvent, configuration: Configuration):
    """文字訊息 → 更新 last_seen，依關鍵字路由（無命中則不回應）。"""
    if not isinstance(event.message, TextMessageContent):
        return

    line_uid = event.source.user_id
    update_last_seen(line_uid)

    text = event.message.text or ""
    action = _match_keyword(text)
    if not action:
        return  # 無關鍵字命中，沉默

    try:
        if action == "carousel":
            send_carousel(line_uid)
        elif action == "greet":
            send_simple_greeting(line_uid)
        else:
            send_card(line_uid, action)
    except Exception:
        logger.exception("[webhook] keyword dispatch failed (action=%s)", action)


def _match_keyword(text: str) -> str | None:
    for keywords, action in KEYWORD_ROUTES:
        if any(kw in text for kw in keywords):
            return action
    return None


def _handle_follow(event: FollowEvent, configuration: Configuration):
    """
    加好友事件：
    1. 呼叫 LINE Profile API 拿 displayName / pictureUrl
    2. 寫入 / 更新 line_users 表
    """
    line_uid = event.source.user_id
    logger.info("FollowEvent: user_id=%s", line_uid)

    display_name = None
    picture_url = None
    try:
        with ApiClient(configuration) as api_client:
            profile = MessagingApi(api_client).get_profile(line_uid)
            display_name = profile.display_name
            picture_url = profile.picture_url
    except Exception as exc:
        print(f"[LINE API ERROR] get_profile failed for {line_uid}: {exc}")

    # 記錄用戶（DB）與「引導探索卡」互不影響：任一失敗都不擋另一個
    try:
        handle_follow(line_uid, display_name, picture_url)
    except Exception:
        logger.exception("[webhook] handle_follow failed for %s", line_uid)

    # 歡迎「文字+圖」由 LINE 後台設；這裡只補一張「引導用」探索卡（5 張引導 Flex）
    try:
        send_carousel(line_uid)
    except Exception:
        logger.exception("[webhook] send_carousel (follow) failed for %s", line_uid)


def _handle_unfollow(event: UnfollowEvent):
    """封鎖 / 取消追蹤事件 → 更新 DB follow_status"""
    line_uid = event.source.user_id
    logger.info("UnfollowEvent: user_id=%s", line_uid)
    handle_unfollow(line_uid)


def _handle_postback(event: PostbackEvent, configuration: Configuration):
    """
    Postback 事件（使用者點選 Flex 按鈕）→ 解析 action → 回覆訊息。
    Stage 6/7：報名確認、執行報名、取消確認、執行取消、我的報名。
    """
    line_uid = event.source.user_id
    data = event.postback.data or ""
    logger.info("PostbackEvent: user_id=%s data=%s", line_uid, data)

    messages = handle_postback(line_uid, data)
    if not messages:
        return

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages,
            )
        )
