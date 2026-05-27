"""
Push Service — Stage 5
查詢訂閱者 → 批次 LINE Push → 寫 PushLog。

公開入口：
  push_event_notification(temple_id, event, temple_name) -> int
    回傳成功推送的人數。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
)
from sqlalchemy import select

from extensions import db
from models.line_user import LineUser
from models.push_log import PushLog
from models.subscription import Subscription
from services.flex_builder import build_event_notification

logger = logging.getLogger(__name__)


def _line_api() -> tuple[Configuration, MessagingApi]:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    cfg = Configuration(access_token=token)
    return cfg, MessagingApi(ApiClient(cfg))


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── 主入口 ────────────────────────────────────────────────────────────────────

def push_event_notification(
    temple_id: int,
    event: dict,
    temple_name: str = "",
) -> int:
    """
    把活動通知推播給所有訂閱該廟、is_active=True 的 LINE 用戶。

    Args:
        temple_id:   TEP temples.id
        event:       TEP 活動 dict（camelCase，至少含 id / title）
        temple_name: 廟宇名稱，用於 Flex header 顯示

    Returns:
        成功推播人數（已送出，不含失敗）
    """
    subscribers = _get_subscribers(temple_id)
    if not subscribers:
        logger.info("[push] temple_id=%d 無訂閱者，略過", temple_id)
        return 0

    flex = build_event_notification(event, temple_name)
    event_id = event.get("id")

    cfg = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
    success_count = 0

    for line_user in subscribers:
        ok = _push_one(cfg, line_user, flex, event_id=event_id)
        if ok:
            success_count += 1

    logger.info(
        "[push] temple_id=%d event_id=%s 推播完成：%d/%d 成功",
        temple_id, event_id, success_count, len(subscribers),
    )
    return success_count


# ── 內部工具 ──────────────────────────────────────────────────────────────────

def _get_subscribers(temple_id: int) -> list[LineUser]:
    """查出所有訂閱該廟且 is_active=True 的 LineUser。"""
    stmt = (
        select(LineUser)
        .join(Subscription, Subscription.line_user_id == LineUser.id)
        .where(
            Subscription.tep_temple_id == temple_id,
            Subscription.is_active == True,
        )
    )
    return list(db.session.execute(stmt).scalars())


def _push_one(
    cfg: Configuration,
    line_user: LineUser,
    message,
    *,
    event_id: int | None = None,
    push_type: str = "event_notify",
) -> bool:
    """
    推送單則訊息給一個 LINE 用戶，並寫 PushLog。
    成功 → True；失敗 → False（不拋例外，避免中斷批次）。
    """
    log = PushLog(
        line_user_id=line_user.id,
        tep_event_id=event_id,
        push_type=push_type,
        status="queued",
    )
    db.session.add(log)
    db.session.flush()  # 取得 log.id，但還沒 commit

    try:
        with ApiClient(cfg) as api_client:
            MessagingApi(api_client).push_message(
                PushMessageRequest(to=line_user.line_uid, messages=[message])
            )
        log.status = "sent"
        log.sent_at = _now()
        db.session.commit()
        return True

    except Exception as exc:
        logger.error(
            "[push] 推播失敗 line_uid=%s event_id=%s: %s",
            line_user.line_uid, event_id, exc,
        )
        log.status = "failed"
        log.error_message = str(exc)[:500]
        db.session.commit()
        return False
