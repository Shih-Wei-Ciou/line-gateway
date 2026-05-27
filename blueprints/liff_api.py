"""
LIFF API Blueprint — Stage 3 Group C
所有 endpoint 都要求 X-Line-Uid header（模擬 LIFF token 驗證）。
"""
from flask import Blueprint, request, jsonify

from services.subscription_service import (
    get_user_by_uid,
    subscribe,
    unsubscribe,
    get_active_subscriptions,
)

bp = Blueprint("liff_api", __name__, url_prefix="/api/liff")


def _get_current_user():
    """
    【DEV MODE — 開發用身份識別，Stage 8 上線前必須替換】
    目前直接信任 client 傳來的 X-Line-Uid header，無任何簽名驗證。

    TODO(Stage 8 / production hardening):
      - 改成接收 LIFF access token（前端 liff.getAccessToken()）
      - 呼叫 LINE Verify API（https://api.line.me/oauth2/v2.1/verify）
        確認 token 合法且 client_id 對得上本系統的 LIFF Channel
      - 從 verify 回傳的 sub 欄位取得真實 line_uid，不再信任 header
      - 參考文件：https://developers.line.biz/en/reference/line-login/#verify-access-token
    """
    line_uid = request.headers.get("X-Line-Uid", "").strip()
    if not line_uid:
        return None, (jsonify({"error": "Missing X-Line-Uid header"}), 401)

    user = get_user_by_uid(line_uid)
    if user is None:
        return None, (jsonify({"error": "User not found"}), 404)

    return user, None


# ── GET /api/liff/me ──────────────────────────────────────────────────────────

@bp.get("/me")
def me():
    user, err = _get_current_user()
    if err:
        return err

    subs = get_active_subscriptions(user)
    return jsonify({
        "user": user.to_dict(),
        "subscriptions": [s.to_dict() for s in subs],
    }), 200


# ── POST /api/liff/subscriptions ─────────────────────────────────────────────

@bp.post("/subscriptions")
def create_subscription():
    user, err = _get_current_user()
    if err:
        return err

    body = request.get_json(silent=True) or {}
    tep_temple_id = body.get("tep_temple_id")
    if tep_temple_id is None:
        return jsonify({"error": "tep_temple_id is required"}), 400
    if not isinstance(tep_temple_id, int) or tep_temple_id <= 0:
        return jsonify({"error": "tep_temple_id must be a positive integer"}), 400

    sub, created = subscribe(user, tep_temple_id)
    status = 201 if created else 200
    return jsonify(sub.to_dict()), status


# ── DELETE /api/liff/subscriptions/<id> ──────────────────────────────────────

@bp.delete("/subscriptions/<int:subscription_id>")
def delete_subscription(subscription_id: int):
    user, err = _get_current_user()
    if err:
        return err

    sub, error_code = unsubscribe(subscription_id, user)
    if error_code == "not_found":
        return jsonify({"error": "Subscription not found"}), 404
    if error_code == "forbidden":
        return jsonify({"error": "Forbidden"}), 403

    return jsonify(sub.to_dict()), 200
