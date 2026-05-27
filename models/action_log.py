from datetime import datetime, timezone
from extensions import db


class ActionLog(db.Model):
    """
    使用者操作流水帳。
    每次呼叫 TEP API（報名、取消）都寫一筆。
    是除錯用的黑盒子——使用者說「我明明按了但沒報到」時，翻這裡找原因。
    """
    __tablename__ = "action_logs"

    id = db.Column(db.Integer, primary_key=True)
    line_user_id = db.Column(
        db.Integer, db.ForeignKey("line_users.id"), nullable=True, index=True
    )

    # register / cancel / view / subscribe / unsubscribe / profile_update
    action_type = db.Column(db.String(50), nullable=False)

    # 我們送給 TEP 的 request body（或 postback data）
    request_payload = db.Column(db.JSON, nullable=True)

    # TEP 回給我們的 response（含 status code 和 body）
    tep_response = db.Column(db.JSON, nullable=True)

    # pending → success / failed
    status = db.Column(
        db.Enum("pending", "success", "failed", name="action_status_enum"),
        nullable=False,
        default="pending",
    )

    error_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<ActionLog {self.action_type} user={self.line_user_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "line_user_id": self.line_user_id,
            "action_type": self.action_type,
            "request_payload": self.request_payload,
            "tep_response": self.tep_response,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }
