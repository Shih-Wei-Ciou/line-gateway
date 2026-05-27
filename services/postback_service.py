"""
Postback Router — Stage 6
解析 LINE PostbackEvent.data，分派到對應的 handler，
最後組裝 ReplyMessageRequest 回傳給 webhook 層。

Postback data 格式：query string，例如：
  action=confirm_register&event_id=1
  action=do_register&event_id=1
  action=confirm_cancel&reg_id=5
  action=do_cancel&reg_id=5
  action=my_regs
  action=cancel_register_flow&event_id=1  （使用者按「不用了」）
  action=keep_registration&reg_id=5       （使用者按「保留報名」）

每個 handler 回傳 list[Message]，交由 webhook 層呼叫 reply_message()。
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qs

from linebot.v3.messaging import TextMessage

import services.event_service as ev_svc
from services.flex_builder import (
    build_cancel_confirm,
    build_my_registrations,
    build_register_confirm,
)

logger = logging.getLogger(__name__)


# ── 主入口 ────────────────────────────────────────────────────────────────────

def handle_postback(line_uid: str, data: str) -> list:
    """
    解析 postback data，回傳 LINE Message 物件清單。
    不應拋例外——任何錯誤都包成「系統錯誤」訊息回傳。
    """
    try:
        params = {k: v[0] for k, v in parse_qs(data).items()}
        action = params.get("action", "")

        if action == "confirm_register":
            return _confirm_register(line_uid, params)
        elif action == "do_register":
            return _do_register(line_uid, params)
        elif action == "confirm_cancel":
            return _confirm_cancel(line_uid, params)
        elif action == "do_cancel":
            return _do_cancel(line_uid, params)
        elif action == "my_regs":
            return _my_regs(line_uid)
        elif action in ("cancel_register_flow", "keep_registration"):
            return [TextMessage(text="好的，已取消操作。")]
        else:
            logger.warning("[postback] 未知 action=%s uid=%s", action, line_uid)
            return [TextMessage(text="收到！但我不確定你按了什麼，請再試一次。")]

    except Exception as exc:
        logger.error("[postback] 未預期錯誤 uid=%s data=%s: %s", line_uid, data, exc)
        return [TextMessage(text="系統暫時有點問題，請稍後再試。")]


# ── Action handlers ───────────────────────────────────────────────────────────

def _confirm_register(line_uid: str, params: dict) -> list:
    """顯示報名確認畫面（姓名、電話、活動資訊）。"""
    event_id = int(params.get("event_id", 0))
    if not event_id:
        return [TextMessage(text="活動資訊有誤，請重試。")]

    status, ctx = ev_svc.get_register_context(line_uid, event_id)

    if status == "missing_profile":
        return [TextMessage(
            text="報名前請先完善個人資料（姓名和電話）。\n"
                 "請點選選單中的「個人資料」進行設定。"
        )]
    if status == "not_found":
        return [TextMessage(text="找不到此活動，可能已下架或截止。")]
    if status == "tep_error":
        return [TextMessage(text="無法取得活動資訊，請稍後再試。")]

    user = ctx["user"]
    event = ctx["event"]

    # 活動已不可報名
    if event.get("canRegister") is False:
        return [TextMessage(text=f"「{event.get('title', '此活動')}」目前不開放報名（已截止或額滿）。")]

    return [build_register_confirm(event, user.real_name, user.phone)]


def _do_register(line_uid: str, params: dict) -> list:
    """實際執行報名。"""
    event_id = int(params.get("event_id", 0))
    if not event_id:
        return [TextMessage(text="活動資訊有誤，請重試。")]

    status, reg = ev_svc.do_register(line_uid, event_id)

    if status == "ok":
        return [TextMessage(text="✅ 報名成功！活動當天記得準時出席。\n如需取消請從「我的報名」操作。")]
    if status == "already_registered":
        return [TextMessage(text="您已報名此活動，無需重複操作。")]
    if status == "missing_profile":
        return [TextMessage(text="請先完善個人資料（姓名和電話）再報名。")]
    # tep_error / not_found
    return [TextMessage(text="報名失敗，請稍後再試或聯繫廟方。")]


def _confirm_cancel(line_uid: str, params: dict) -> list:
    """顯示取消確認畫面。"""
    reg_id = int(params.get("reg_id", 0))
    if not reg_id:
        return [TextMessage(text="報名資訊有誤，請重試。")]

    # 從 TEP 拿使用者的報名清單，找到這筆
    regs = ev_svc.get_my_registrations(line_uid)
    reg = next((r for r in regs if r.get("id") == reg_id), None)

    if reg is None:
        return [TextMessage(text="找不到此報名紀錄，可能已取消或不屬於您。")]

    event = reg.get("event") or {}
    event_title = event.get("title") or "此活動"

    return [build_cancel_confirm(reg, event_title)]


def _do_cancel(line_uid: str, params: dict) -> list:
    """實際執行取消報名。"""
    reg_id = int(params.get("reg_id", 0))
    if not reg_id:
        return [TextMessage(text="報名資訊有誤，請重試。")]

    status, _ = ev_svc.do_cancel(line_uid, reg_id)

    if status == "ok":
        return [TextMessage(text="✅ 已成功取消報名。")]
    if status == "not_found":
        return [TextMessage(text="找不到此報名紀錄。")]
    if status == "forbidden":
        return [TextMessage(text="您沒有權限取消此報名。")]
    return [TextMessage(text="取消失敗，請稍後再試。")]


def _my_regs(line_uid: str) -> list:
    """顯示我的報名清單。"""
    regs = ev_svc.get_my_registrations(line_uid)
    # 只顯示 registered 狀態
    active_regs = [r for r in regs if r.get("status") == "registered"]
    return [build_my_registrations(active_regs)]
