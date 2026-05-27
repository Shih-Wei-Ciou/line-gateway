"""
活動報名服務層 — Stage 6/7
透過 TEPClient 呼叫報名/取消，並寫 ActionLog。

LineUser.real_name / phone 是報名必填欄位。
若使用者尚未填寫，回傳 ('missing_profile', None)。

回傳 tuple (status, data)：
  status: 'ok' | 'missing_profile' | 'already_registered' | 'tep_error' | 'not_found' | 'forbidden'
  data:   成功時為 dict（TEP 回傳）；失敗時為 None
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from extensions import db
from models.action_log import ActionLog
from models.line_user import LineUser
from services.tep_client import TEPError, get_tep_client

logger = logging.getLogger(__name__)

_Result = tuple[str, dict | None]


# ── 工具 ──────────────────────────────────────────────────────────────────────

def _get_user(line_uid: str) -> LineUser | None:
    stmt = select(LineUser).where(LineUser.line_uid == line_uid)
    return db.session.execute(stmt).scalar_one_or_none()


def _write_log(
    line_user: LineUser,
    action_type: str,
    payload: dict,
    tep_response: dict | None,
    status: str,
    error: str | None = None,
) -> None:
    log = ActionLog(
        line_user_id=line_user.id,
        action_type=action_type,
        request_payload=payload,
        tep_response=tep_response,
        status=status,
        error_message=error,
    )
    db.session.add(log)
    db.session.commit()


# ── 取得活動資訊（供 postback handler 組裝確認畫面用）────────────────────────

def get_event(event_id: int) -> tuple[str, dict | None]:
    """
    取得 TEP 活動詳情。
    回傳 ('ok', event_dict) 或 ('tep_error', None)。
    """
    try:
        event = get_tep_client().get_event(event_id)
        return "ok", event
    except TEPError as exc:
        logger.warning("[event_service] get_event %d failed: %s", event_id, exc)
        if exc.status_code == 404:
            return "not_found", None
        return "tep_error", None


# ── 報名 ──────────────────────────────────────────────────────────────────────

def get_register_context(line_uid: str, event_id: int) -> tuple[str, dict | None]:
    """
    取得「確認報名」所需資料：使用者姓名/電話 + 活動詳情。
    供 postback confirm_register 使用。

    回傳：
      ('ok', {'user': LineUser, 'event': dict})
      ('missing_profile', None) — 使用者未填 real_name/phone
      ('not_found', None)       — 活動不存在
      ('tep_error', None)       — TEP 呼叫失敗
    """
    user = _get_user(line_uid)
    if user is None:
        return "not_found", None

    if not user.real_name or not user.phone:
        return "missing_profile", None

    status, event = get_event(event_id)
    if status != "ok":
        # 使用者已觸發報名流程但 TEP 回傳錯誤，記錄起來
        _write_log(
            user,
            "register",
            {"event_id": event_id, "step": "fetch_event"},
            None,
            "failed",
            f"get_event returned {status}",
        )
        return status, None

    return "ok", {"user": user, "event": event}


def do_register(line_uid: str, event_id: int) -> _Result:
    """
    實際呼叫 TEP 報名。
    回傳 ('ok', registration_dict) 或錯誤 status。
    """
    user = _get_user(line_uid)
    if user is None:
        return "not_found", None

    if not user.real_name or not user.phone:
        return "missing_profile", None

    payload = {"event_id": event_id, "name": user.real_name, "phone": user.phone}

    try:
        reg = get_tep_client().register_event(
            event_id,
            name=user.real_name,
            phone=user.phone,
            line_uid=line_uid,
        )
        _write_log(user, "register", payload, reg, "success")
        return "ok", reg

    except TEPError as exc:
        logger.warning("[event_service] do_register event=%d uid=%s: %s", event_id, line_uid, exc)
        error_msg = exc.message
        _write_log(user, "register", payload, None, "failed", error_msg)

        # TEP 回 400「您已報名此活動」
        if exc.status_code == 400 and "已報名" in exc.message:
            return "already_registered", None
        return "tep_error", None


# ── 取消報名 ──────────────────────────────────────────────────────────────────

def get_my_registrations(line_uid: str) -> list[dict]:
    """
    取得使用者在 TEP 的報名清單（含活動資訊）。
    失敗時回傳空清單。
    """
    try:
        return get_tep_client().get_my_registrations(line_uid)
    except TEPError as exc:
        logger.warning("[event_service] get_my_registrations uid=%s: %s", line_uid, exc)
        return []


def do_cancel(line_uid: str, reg_id: int) -> _Result:
    """
    取消報名。
    回傳 ('ok', registration_dict) 或錯誤 status。
    """
    user = _get_user(line_uid)
    if user is None:
        return "not_found", None

    payload = {"reg_id": reg_id}

    try:
        result = get_tep_client().cancel_registration(reg_id, line_uid)
        _write_log(user, "cancel", payload, result, "success")
        return "ok", result

    except TEPError as exc:
        logger.warning("[event_service] do_cancel reg=%d uid=%s: %s", reg_id, line_uid, exc)
        _write_log(user, "cancel", payload, None, "failed", exc.message)

        if exc.status_code == 404:
            return "not_found", None
        if exc.status_code == 403:
            return "forbidden", None
        return "tep_error", None
