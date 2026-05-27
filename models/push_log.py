from datetime import datetime, timezone
from extensions import db


class PushLog(db.Model):
    """
    推播紀錄。
    每次推 Flex Message 給一個使用者就寫一筆。
    tep_event_id 對應 TEP 的 temple_events.id（跨系統，不是真正的 DB 外鍵）。
    """
    __tablename__ = "push_logs"

    id = db.Column(db.Integer, primary_key=True)
    line_user_id = db.Column(
        db.Integer, db.ForeignKey("line_users.id"), nullable=False, index=True
    )

    # 對應 TEP 的 temple_events.id
    tep_event_id = db.Column(db.Integer, nullable=True, index=True)

    # 推播類型：event_notify / welcome / confirm / cancel_confirm / broadcast
    push_type = db.Column(db.String(50), nullable=False, default="event_notify")

    # 實際送給 LINE 的 Flex Message JSON
    flex_payload = db.Column(db.JSON, nullable=True)

    # queued（排隊中）→ sent（已送出）/ failed（失敗）
    status = db.Column(
        db.Enum("queued", "sent", "failed", name="push_status_enum"),
        nullable=False,
        default="queued",
    )

    error_message = db.Column(db.Text, nullable=True)

    # 實際推出去的時間
    sent_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<PushLog user={self.line_user_id} event={self.tep_event_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "line_user_id": self.line_user_id,
            "tep_event_id": self.tep_event_id,
            "push_type": self.push_type,
            "status": self.status,
            "error_message": self.error_message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat(),
        }
