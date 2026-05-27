"""
TEP API Client — Stage 4
Gateway 呼叫廟宇平台（TEP）的 HTTP 客戶端。

已知可用的無需認證端點（/api/public/* 與 /api/temples/*）：
  - GET  /api/temples/<id>
  - GET  /api/public/temples/<temple_id>/events
  - GET  /api/public/events/<event_id>
  - POST /api/public/events/<event_id>/register
  - GET  /api/public/registrations?line_uid=Uxxxxxxx
  - PUT  /api/public/registrations/<id>/cancel

TODO(Stage 7 / 需要 TEP service account 的功能):
  - 若未來需要呼叫需 JWT 的 TEP endpoint（積分、護身符、兌換等），
    在此加入 _login() + _ensure_token() 的 service account 邏輯。
    目前 TEP 只有 email/password → JWT 這條路，
    需跟學長確認 gateway 要用哪組帳號或是否新增 API key 模式。
"""

import os
import time
import logging

import requests

logger = logging.getLogger(__name__)

# ── 重試設定 ──────────────────────────────────────────────────────────────────
_MAX_RETRIES = 3
_RETRY_BACKOFF = 0.5   # 首次等待秒數；實際等待 = backoff * 2^attempt
_RETRY_ON_STATUS = {500, 502, 503, 504}   # 只對 5xx 重試，4xx 不重試


class TEPError(Exception):
    """TEP API 回傳非預期錯誤時拋出"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"TEP {status_code}: {message}")


class TEPClient:
    """
    單一 TEP API 客戶端，封裝所有 HTTP 呼叫細節。
    透過 os.getenv("TEP_BASE_URL") 取得 base URL。

    使用範例：
        client = TEPClient()
        temple = client.get_temple(1)
        events = client.get_temple_events(1)
    """

    def __init__(self):
        base = os.getenv("TEP_BASE_URL", "http://localhost:5000/api").rstrip("/")
        self._base_url = base
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    # ── 底層 HTTP + 重試 ───────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        timeout: int = 10,
    ) -> dict:
        """
        發送 HTTP 請求，自動對 5xx 做指數退避重試，4xx 直接拋 TEPError。

        回傳 TEP 標準格式中的 `data` 欄位；若 `data` 為 None 則回傳 {}。
        """
        url = f"{self._base_url}{path}"

        for attempt in range(_MAX_RETRIES):
            try:
                resp = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    timeout=timeout,
                )
            except requests.ConnectionError as exc:
                if attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF * (2 ** attempt)
                    logger.warning("TEP connection error (attempt %d), retry in %.1fs: %s", attempt + 1, wait, exc)
                    time.sleep(wait)
                    continue
                raise TEPError(0, f"Cannot connect to TEP: {exc}") from exc
            except requests.Timeout as exc:
                raise TEPError(0, f"TEP request timed out: {exc}") from exc

            if resp.status_code in _RETRY_ON_STATUS and attempt < _MAX_RETRIES - 1:
                wait = _RETRY_BACKOFF * (2 ** attempt)
                logger.warning("TEP %s (attempt %d), retry in %.1fs", resp.status_code, attempt + 1, wait)
                time.sleep(wait)
                continue

            if not resp.ok:
                # 嘗試解析 TEP 標準錯誤格式
                try:
                    body = resp.json()
                    msg = body.get("message") or body.get("error") or resp.text
                except Exception:
                    msg = resp.text
                raise TEPError(resp.status_code, msg)

            body = resp.json()
            return body.get("data") or {}

        # 不應走到這裡，但保險起見
        raise TEPError(0, "Max retries exceeded")

    # ── 廟宇 ──────────────────────────────────────────────────────────────────

    def get_temple(self, temple_id: int) -> dict:
        """
        GET /api/temples/<temple_id>
        回傳廟宇詳情 dict；找不到時拋 TEPError(404, ...)。
        """
        return self._request("GET", f"/temples/{temple_id}")

    def list_temples(self, *, is_active: bool = True, search: str = "", limit: int = 50) -> list[dict]:
        """
        GET /api/temples/
        回傳廟宇清單，供訂閱頁下拉選單用。
        """
        params: dict = {"limit": limit}
        if is_active is not None:
            params["is_active"] = "true" if is_active else "false"
        if search:
            params["search"] = search

        data = self._request("GET", "/temples/", params=params)
        return data.get("temples", [])

    # ── 活動 ──────────────────────────────────────────────────────────────────

    def get_temple_events(self, temple_id: int) -> list[dict]:
        """
        GET /api/public/temples/<temple_id>/events
        回傳該廟目前 published 且報名未截止的活動清單。
        供推播前確認是否有活動可通知。
        """
        data = self._request("GET", f"/public/temples/{temple_id}/events")
        return data.get("events", [])

    def get_event(self, event_id: int) -> dict:
        """
        GET /api/public/events/<event_id>
        回傳單一活動詳情，含 canRegister / remainingCapacity。
        """
        return self._request("GET", f"/public/events/{event_id}")

    # ── 報名 ──────────────────────────────────────────────────────────────────

    def register_event(
        self,
        event_id: int,
        *,
        name: str,
        phone: str,
        line_uid: str,
        email: str = "",
        people_count: int = 1,
        notes: str = "",
    ) -> dict:
        """
        POST /api/public/events/<event_id>/register
        用 LINE UID 報名活動（不需要 TEP 帳號）。
        成功回傳報名 dict；失敗拋 TEPError。
        """
        payload = {
            "name": name,
            "phone": phone,
            "lineUserId": line_uid,
            "peopleCount": people_count,
        }
        if email:
            payload["email"] = email
        if notes:
            payload["notes"] = notes

        return self._request("POST", f"/public/events/{event_id}/register", json=payload)

    def get_my_registrations(self, line_uid: str) -> list[dict]:
        """
        GET /api/public/registrations?line_uid=Uxxxxxx
        查詢該 LINE 用戶的所有報名紀錄（含活動資訊）。
        """
        data = self._request("GET", "/public/registrations", params={"line_uid": line_uid})
        return data.get("registrations", [])

    def cancel_registration(self, registration_id: int, line_uid: str) -> dict:
        """
        PUT /api/public/registrations/<id>/cancel
        取消報名。TEP 端用 lineUserId 驗身，gateway 直接傳 line_uid。
        """
        return self._request(
            "PUT",
            f"/public/registrations/{registration_id}/cancel",
            json={"lineUserId": line_uid},
        )


# ── module-level singleton（避免每次 request 都重建 Session）────────────────

_client: TEPClient | None = None


def get_tep_client() -> TEPClient:
    """回傳 module-level TEPClient，第一次呼叫時初始化。"""
    global _client
    if _client is None:
        _client = TEPClient()
    return _client
