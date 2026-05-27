"""
Admin Blueprint — LINE 訊息測試 API

POST /admin/test/send
  Header: X-Admin-Key (對 .env 的 ADMIN_KEY)
  Body  : {"type": "...", "to_uid": "..." (optional)}

  type 支援:
    explore       Flex Carousel
    welcome       完整加好友流程（loading + text + sticker + carousel + quick reply）
    quick_reply   只送 Quick Reply
    location      位置訊息（三官寶殿）
    sticker       貼圖
    loading_test  Loading Animation

  to_uid 未提供時用 .env 的 ADMIN_LINE_UID。
  回 JSON {"ok": true, "type": "...", "to_uid": "..."}
"""
from __future__ import annotations

import logging
import os

from flask import Blueprint, jsonify, request

from services.messages import send_test_message

logger = logging.getLogger(__name__)

bp = Blueprint("admin", __name__, url_prefix="/admin")


VALID_TYPES = {"explore", "welcome", "quick_reply", "location", "sticker", "loading_test"}


@bp.route("/test/send", methods=["POST"])
def test_send():
    expected_key = os.getenv("ADMIN_KEY", "").strip()
    if not expected_key:
        return jsonify(ok=False, error="ADMIN_KEY not configured on server"), 500

    if request.headers.get("X-Admin-Key", "") != expected_key:
        return jsonify(ok=False, error="invalid admin key"), 401

    data = request.get_json(silent=True) or {}
    msg_type = (data.get("type") or "").strip()
    if msg_type not in VALID_TYPES:
        return (
            jsonify(
                ok=False,
                error=f"invalid type {msg_type!r}",
                valid=sorted(VALID_TYPES),
            ),
            400,
        )

    to_uid = (data.get("to_uid") or os.getenv("ADMIN_LINE_UID", "")).strip()
    if not to_uid:
        return jsonify(ok=False, error="no to_uid (provide in body or set ADMIN_LINE_UID)"), 400

    try:
        send_test_message(to_uid, msg_type)
    except Exception as exc:
        logger.exception("[admin/test/send] failed")
        return jsonify(ok=False, error=str(exc), type=msg_type, to_uid=to_uid), 500

    return jsonify(ok=True, type=msg_type, to_uid=to_uid)
