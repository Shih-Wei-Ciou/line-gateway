from datetime import datetime, timezone
from extensions import db


class Subscription(db.Model):
    """
    LINE 使用者 ↔ 廟宇訂閱關係。
    tep_temple_id 對應 TEP 的 temples.id，但不是真正的外鍵（跨系統）。
    """
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    line_user_id = db.Column(
        db.Integer, db.ForeignKey("line_users.id"), nullable=False, index=True
    )
    # 對應 TEP temples.id，透過 API 查詢，不是真正的 DB 外鍵
    tep_temple_id = db.Column(db.Integer, nullable=False, index=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    subscribed_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    unsubscribed_at = db.Column(db.DateTime, nullable=True)

    # 同一個使用者不能重複訂閱同一間廟（active 狀態）
    __table_args__ = (
        db.UniqueConstraint("line_user_id", "tep_temple_id", name="uq_user_temple"),
    )

    def __repr__(self):
        return f"<Subscription user={self.line_user_id} temple={self.tep_temple_id} active={self.is_active}>"

    def to_dict(self):
        return {
            "id": self.id,
            "line_user_id": self.line_user_id,
            "tep_temple_id": self.tep_temple_id,
            "is_active": self.is_active,
            "subscribed_at": self.subscribed_at.isoformat(),
            "unsubscribed_at": (
                self.unsubscribed_at.isoformat() if self.unsubscribed_at else None
            ),
        }
