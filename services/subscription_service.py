"""
訂閱服務層 — Stage 3 Group C
POST (subscribe) / DELETE (unsubscribe) / GET (list) 的 DB 操作。
"""
from datetime import datetime, timezone

from sqlalchemy import select

from extensions import db
from models.line_user import LineUser
from models.subscription import Subscription


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_user_by_uid(line_uid: str) -> LineUser | None:
    stmt = select(LineUser).where(LineUser.line_uid == line_uid)
    return db.session.execute(stmt).scalar_one_or_none()


def subscribe(user: LineUser, tep_temple_id: int) -> tuple[Subscription, bool]:
    """
    訂閱廟宇。
    回傳 (subscription, created)：
      created=True  → 201（全新訂閱）
      created=False → 200（已存在或重新啟用）
    """
    stmt = select(Subscription).where(
        Subscription.line_user_id == user.id,
        Subscription.tep_temple_id == tep_temple_id,
    )
    sub: Subscription | None = db.session.execute(stmt).scalar_one_or_none()

    if sub is None:
        sub = Subscription(
            line_user_id=user.id,
            tep_temple_id=tep_temple_id,
            is_active=True,
            subscribed_at=_now(),
        )
        db.session.add(sub)
        db.session.commit()
        return sub, True

    if not sub.is_active:
        # 重新訂閱（之前刪過）
        sub.is_active = True
        sub.subscribed_at = _now()
        sub.unsubscribed_at = None
        db.session.commit()

    return sub, False


def unsubscribe(subscription_id: int, user: LineUser) -> tuple[Subscription | None, str | None]:
    """
    取消訂閱。
    回傳 (subscription, error_code)：
      error_code None   → 成功
      error_code 'not_found' → 404
      error_code 'forbidden' → 403
    """
    stmt = select(Subscription).where(Subscription.id == subscription_id)
    sub: Subscription | None = db.session.execute(stmt).scalar_one_or_none()

    if sub is None:
        return None, "not_found"

    if sub.line_user_id != user.id:
        return None, "forbidden"

    sub.is_active = False
    sub.unsubscribed_at = _now()
    db.session.commit()
    return sub, None


def get_active_subscriptions(user: LineUser) -> list[Subscription]:
    stmt = (
        select(Subscription)
        .where(Subscription.line_user_id == user.id, Subscription.is_active == True)
        .order_by(Subscription.subscribed_at)
    )
    return list(db.session.execute(stmt).scalars())
