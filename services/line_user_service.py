"""
LINE 使用者服務層 — Stage 2
負責 follow / unfollow / last_seen 的 DB 操作。
所有 DB 操作均包在 try/except，失敗時只印 log，不崩潰。
使用 SQLAlchemy 2.x 語法（select() + session.execute()）。
"""
from datetime import datetime, timezone

from sqlalchemy import select

from extensions import db
from models.line_user import LineUser


def _now() -> datetime:
    return datetime.now(timezone.utc)


def handle_follow(line_uid: str, display_name: str | None, picture_url: str | None) -> None:
    """
    加好友時呼叫。
    - 已有 row → 更新 follow_status='active'、display_name/picture_url、followed_at、last_seen_at
    - 沒有 row → INSERT 新 row
    """
    try:
        stmt = select(LineUser).where(LineUser.line_uid == line_uid)
        user: LineUser | None = db.session.execute(stmt).scalar_one_or_none()

        now = _now()
        if user is None:
            user = LineUser(
                line_uid=line_uid,
                display_name=display_name,
                picture_url=picture_url,
                follow_status="active",
                followed_at=now,
                last_seen_at=now,
            )
            db.session.add(user)
        else:
            user.display_name = display_name
            user.picture_url = picture_url
            user.follow_status = "active"
            user.followed_at = now
            user.last_seen_at = now

        db.session.commit()
        print(f"[DB] handle_follow OK: line_uid={line_uid}, display_name={display_name}")
    except Exception as exc:
        db.session.rollback()
        print(f"[DB ERROR] handle_follow failed for {line_uid}: {exc}")


def handle_unfollow(line_uid: str) -> None:
    """
    封鎖 / 取消追蹤時呼叫。
    - 找到 row → 更新 follow_status='unfollowed'、unfollowed_at
    - 找不到 row → 只印 warning，不做任何事
    """
    try:
        stmt = select(LineUser).where(LineUser.line_uid == line_uid)
        user: LineUser | None = db.session.execute(stmt).scalar_one_or_none()

        if user is None:
            print(f"[DB WARNING] handle_unfollow: {line_uid} 不存在於 DB，略過")
            return

        user.follow_status = "unfollowed"
        user.unfollowed_at = _now()
        db.session.commit()
        print(f"[DB] handle_unfollow OK: line_uid={line_uid}")
    except Exception as exc:
        db.session.rollback()
        print(f"[DB ERROR] handle_unfollow failed for {line_uid}: {exc}")


def update_last_seen(line_uid: str) -> None:
    """
    收到任何訊息時呼叫，更新 last_seen_at。
    找不到 row 時略過（用戶可能在 follow 前就傳訊息，極少見）。
    """
    try:
        stmt = select(LineUser).where(LineUser.line_uid == line_uid)
        user: LineUser | None = db.session.execute(stmt).scalar_one_or_none()

        if user is None:
            print(f"[DB WARNING] update_last_seen: {line_uid} 不存在於 DB，略過")
            return

        user.last_seen_at = _now()
        db.session.commit()
        print(f"[DB] update_last_seen OK: line_uid={line_uid}")
    except Exception as exc:
        db.session.rollback()
        print(f"[DB ERROR] update_last_seen failed for {line_uid}: {exc}")
