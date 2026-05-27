"""
Internal API Blueprint — Stage 5
供 TEP 呼叫，需帶 X-Gateway-Key header。

POST /internal/push/event
  → 查訂閱者 → 批次 LINE Push → 回傳推播結果

驗證：request header X-Gateway-Key 必須等於 GATEWAY_INTERNAL_KEY（.env）。
"""
import os
import logging

from flask import Blueprint, request, jsonify

from services.push_service import push_event_notification
from services.tep_client import TEPError, get_tep_client

logger = logging.getLogger(__name__)

bp = Blueprint("internal_api", __name__, url_prefix="/internal")


# ── Auth middleware ───────────────────────────────────────────────────────────

def _check_api_key() -> tuple[None, None] | tuple[object, int]:
    """
    驗證 X-Gateway-Key header。
    合法 → 回傳 (None, None)；不合法 → 回傳 (response, status_code)。
    """
    expected = os.getenv("GATEWAY_INTERNAL_KEY", "")
    provided = request.headers.get("X-Gateway-Key", "")

    if not provided:
        return jsonify({"error": "Missing X-Gateway-Key header"}), 401
    if provided != expected:
        return jsonify({"error": "Invalid API key"}), 403
    return None, None


# ── POST /internal/push/event ─────────────────────────────────────────────────

@bp.post("/push/event")
def push_event():
    """
    TEP → Gateway：通知有新活動要推播。

    Request body（JSON）：
    {
      "temple_id":   1,          // 必填，對應 tep_temple_id
      "event_id":    42,         // 必填，TEP 的 temple_events.id
      "temple_name": "文武廟",   // 選填，顯示在 Flex header
      "event":       { ... }     // 選填；若有則直接用，否則 gateway 自行呼叫 TEP 拿
    }

    Response：
      200 { "pushed": 3, "event_id": 42 }
      400 缺少必填欄位
      401/403 API key 問題
      404 活動不存在（TEP 查不到）
      500 TEP 通訊失敗
    """
    err_resp, err_code = _check_api_key()
    if err_resp is not None:
        return err_resp, err_code

    body = request.get_json(silent=True) or {}
    temple_id = body.get("temple_id")
    event_id  = body.get("event_id")

    if temple_id is None or event_id is None:
        return jsonify({"error": "temple_id and event_id are required"}), 400
    if not isinstance(temple_id, int) or not isinstance(event_id, int):
        return jsonify({"error": "temple_id and event_id must be integers"}), 400

    # 取活動資料：優先用 body 帶來的，否則去 TEP 拿
    event = body.get("event")
    if not event:
        try:
            event = get_tep_client().get_event(event_id)
        except TEPError as exc:
            if exc.status_code == 404:
                return jsonify({"error": f"Event {event_id} not found in TEP"}), 404
            logger.error("[internal] 無法從 TEP 取得 event %d: %s", event_id, exc)
            return jsonify({"error": "Failed to fetch event from TEP"}), 500

    temple_name = body.get("temple_name", "")

    pushed = push_event_notification(temple_id, event, temple_name)

    logger.info(
        "[internal] push_event temple=%d event=%d pushed=%d",
        temple_id, event_id, pushed,
    )
    return jsonify({"pushed": pushed, "event_id": event_id}), 200
