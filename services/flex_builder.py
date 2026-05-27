"""
Flex Message 建構器 — Stage 5/6/7
所有推播與 postback 回覆用的 Flex Message 都在這裡組裝。

TEP 回傳的 event dict 使用 camelCase（startAt、signupEndAt 等），
本模組以 .get("camelKey") or .get("snake_key") 雙向取值，避免格式耦合。
"""
from __future__ import annotations

from datetime import datetime, timezone

from linebot.v3.messaging import (
    FlexBubble,
    FlexBox,
    FlexButton,
    FlexMessage,
    FlexSeparator,
    FlexText,
    PostbackAction,
)


# ── 工具 ──────────────────────────────────────────────────────────────────────

def _fmt_dt(dt_str: str | None) -> str:
    """把 ISO 8601 字串格式化成 YYYY/MM/DD HH:MM，解析失敗直接回傳原字串。"""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return dt_str


def _ev(event: dict, *keys: str, default: str = "") -> str:
    """依序嘗試多個 key，回傳第一個非空值（支援 camelCase / snake_case 混用）。"""
    for k in keys:
        v = event.get(k)
        if v is not None and v != "":
            return str(v)
    return default


# ── 活動通知（push 時用）──────────────────────────────────────────────────────

def build_event_notification(event: dict, temple_name: str = "") -> FlexMessage:
    """
    給訂閱者的活動通知 Flex Bubble。
    Footer 有「立即報名」postback 按鈕 → action=confirm_register&event_id=<id>
    """
    event_id = event.get("id", 0)
    title     = _ev(event, "title", default="活動通知")
    location  = _ev(event, "location")
    start_at  = _fmt_dt(_ev(event, "startAt", "start_at"))
    fee       = event.get("fee", 0)
    remaining = event.get("remainingCapacity")

    info_rows: list = [
        FlexText(text=f"📅 {start_at}", size="sm", color="#888888", wrap=True),
    ]
    if location:
        info_rows.append(
            FlexText(text=f"📍 {location}", size="sm", color="#888888", wrap=True)
        )
    info_rows.append(
        FlexText(text=f"💰 費用：{'免費' if fee == 0 else f'NT${fee}'}", size="sm", color="#888888")
    )
    if remaining is not None:
        info_rows.append(
            FlexText(text=f"👥 剩餘名額：{remaining}", size="sm", color="#888888")
        )

    header_text = f"【{temple_name}】活動通知" if temple_name else "活動通知"

    return FlexMessage(
        alt_text=f"【活動通知】{title}",
        contents=FlexBubble(
            header=FlexBox(
                layout="vertical",
                background_color="#1DB446",
                padding_all="md",
                contents=[
                    FlexText(text=header_text, color="#ffffff", size="sm", weight="bold")
                ],
            ),
            body=FlexBox(
                layout="vertical",
                contents=[
                    FlexText(text=title, weight="bold", size="lg", wrap=True),
                    FlexBox(
                        layout="vertical",
                        margin="md",
                        spacing="sm",
                        contents=info_rows,
                    ),
                ],
            ),
            footer=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label="立即報名",
                            data=f"action=confirm_register&event_id={event_id}",
                            display_text="我要報名這個活動",
                        ),
                        style="primary",
                        color="#1DB446",
                    ),
                ],
            ),
        ),
    )


# ── 報名確認（postback confirm_register 回覆）────────────────────────────────

def build_register_confirm(event: dict, real_name: str, phone: str) -> FlexMessage:
    """
    讓使用者確認「用這個姓名/電話報名嗎？」
    Footer：確認報名 / 不用了 兩個按鈕。
    """
    event_id = event.get("id", 0)
    title    = _ev(event, "title", default="活動")
    start_at = _fmt_dt(_ev(event, "startAt", "start_at"))

    return FlexMessage(
        alt_text="請確認報名資訊",
        contents=FlexBubble(
            body=FlexBox(
                layout="vertical",
                spacing="md",
                contents=[
                    FlexText(text="確認報名資訊", weight="bold", size="lg"),
                    FlexSeparator(margin="md"),
                    FlexBox(
                        layout="vertical",
                        margin="md",
                        spacing="sm",
                        contents=[
                            FlexText(text=f"活動：{title}", size="sm", wrap=True),
                            FlexText(text=f"時間：{start_at}", size="sm"),
                            FlexText(text=f"姓名：{real_name}", size="sm"),
                            FlexText(text=f"電話：{phone}", size="sm"),
                        ],
                    ),
                ],
            ),
            footer=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label="確認報名",
                            data=f"action=do_register&event_id={event_id}",
                            display_text="確認報名",
                        ),
                        style="primary",
                        color="#1DB446",
                    ),
                    FlexButton(
                        action=PostbackAction(
                            label="不用了",
                            data=f"action=cancel_register_flow&event_id={event_id}",
                            display_text="取消",
                        ),
                        style="secondary",
                    ),
                ],
            ),
        ),
    )


# ── 取消報名確認（postback confirm_cancel 回覆）───────────────────────────────

def build_cancel_confirm(registration: dict, event_title: str) -> FlexMessage:
    """
    讓使用者確認「確定要取消這筆報名嗎？」
    """
    reg_id = registration.get("id", 0)

    return FlexMessage(
        alt_text="確認取消報名",
        contents=FlexBubble(
            body=FlexBox(
                layout="vertical",
                spacing="md",
                contents=[
                    FlexText(text="確認取消報名", weight="bold", size="lg"),
                    FlexSeparator(margin="md"),
                    FlexBox(
                        layout="vertical",
                        margin="md",
                        spacing="sm",
                        contents=[
                            FlexText(text=f"活動：{event_title}", size="sm", wrap=True),
                            FlexText(
                                text="取消後名額將釋出，無法復原。",
                                size="sm",
                                color="#ff5551",
                                wrap=True,
                            ),
                        ],
                    ),
                ],
            ),
            footer=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=[
                    FlexButton(
                        action=PostbackAction(
                            label="確定取消",
                            data=f"action=do_cancel&reg_id={reg_id}",
                            display_text="確定取消報名",
                        ),
                        style="primary",
                        color="#ff5551",
                    ),
                    FlexButton(
                        action=PostbackAction(
                            label="保留報名",
                            data=f"action=keep_registration&reg_id={reg_id}",
                            display_text="保留報名",
                        ),
                        style="secondary",
                    ),
                ],
            ),
        ),
    )


# ── 我的報名清單（最多顯示 5 筆）────────────────────────────────────────────

def build_my_registrations(registrations: list[dict]) -> FlexMessage:
    """
    顯示使用者目前有效的報名清單，每筆附「取消報名」按鈕。
    registrations 是 TEP /api/public/registrations 回傳的清單（含 event 子dict）。
    """
    if not registrations:
        return FlexMessage(
            alt_text="目前沒有報名紀錄",
            contents=FlexBubble(
                body=FlexBox(
                    layout="vertical",
                    contents=[
                        FlexText(
                            text="目前沒有報名中的活動",
                            color="#888888",
                            align="center",
                        )
                    ],
                )
            ),
        )

    rows: list = [FlexText(text="我的報名", weight="bold", size="lg")]

    for reg in registrations[:5]:
        event = reg.get("event") or {}
        title    = _ev(event, "title", default="（活動已移除）")
        start_at = _fmt_dt(_ev(event, "startAt", "start_at"))
        reg_id   = reg.get("id", 0)
        status   = reg.get("status", "")

        rows.append(FlexSeparator(margin="md"))
        rows.append(
            FlexBox(
                layout="vertical",
                margin="md",
                spacing="xs",
                contents=[
                    FlexText(text=title, size="sm", weight="bold", wrap=True),
                    FlexText(text=f"📅 {start_at}", size="xs", color="#888888"),
                    FlexText(
                        text="✅ 報名中" if status == "registered" else f"狀態：{status}",
                        size="xs",
                        color="#1DB446" if status == "registered" else "#888888",
                    ),
                    FlexButton(
                        action=PostbackAction(
                            label="取消報名",
                            data=f"action=confirm_cancel&reg_id={reg_id}",
                            display_text="取消這個報名",
                        ),
                        style="secondary",
                        margin="sm",
                        height="sm",
                    ),
                ],
            )
        )

    return FlexMessage(
        alt_text="我的報名清單",
        contents=FlexBubble(
            body=FlexBox(layout="vertical", contents=rows)
        ),
    )
