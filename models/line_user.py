from datetime import datetime, timezone
from extensions import db


class LineUser(db.Model):
    """
    LINE 使用者主表。
    每個 follow 的人在這裡有一筆 row。
    line_uid 是 LINE 給的唯一識別碼（格式：Uxxxxxxxx...）。
    """
    __tablename__ = "line_users"

    id = db.Column(db.Integer, primary_key=True)
    line_uid = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=True)
    picture_url = db.Column(db.String(500), nullable=True)

    # 首次報名時讓使用者填，之後呼叫 TEP 報名 API 用
    real_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    # active = 正在追蹤；unfollowed = 已取消追蹤
    follow_status = db.Column(
        db.Enum("active", "unfollowed", name="follow_status_enum"),
        nullable=False,
        default="active",
    )
    followed_at = db.Column(db.DateTime, nullable=True)
    unfollowed_at = db.Column(db.DateTime, nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # 關聯
    subscriptions = db.relationship("Subscription", backref="user", lazy="dynamic")
    action_logs = db.relationship("ActionLog", backref="user", lazy="dynamic")
    push_logs = db.relationship("PushLog", backref="user", lazy="dynamic")

    def __repr__(self):
        return f"<LineUser {self.line_uid} ({self.display_name})>"

    def to_dict(self):
        return {
            "id": self.id,
            "line_uid": self.line_uid,
            "display_name": self.display_name,
            "picture_url": self.picture_url,
            "real_name": self.real_name,
            "phone": self.phone,
            "follow_status": self.follow_status,
            "followed_at": self.followed_at.isoformat() if self.followed_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }
