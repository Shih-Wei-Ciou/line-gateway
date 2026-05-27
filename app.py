import os
from flask import Flask
from dotenv import load_dotenv
from extensions import db, migrate

load_dotenv()


def create_app():
    app = Flask(__name__)

    # 資料庫設定
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "postgresql://postgres:dev@localhost:5432/gateway"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # 初始化 extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # 把 models import 進來，Flask-Migrate 才能看到（建表用）
    with app.app_context():
        import models  # noqa: F401

    # 路由
    @app.route("/")
    def index():
        return "LINE Gateway is running!"

    # LIFF 頁面
    from flask import render_template, abort

    @app.route("/liff/subscribe")
    def liff_subscribe():
        return render_template("liff/subscribe.html")

    @app.route("/liff/test")
    def liff_test():
        liff_id = os.getenv("LIFF_ID_SUBSCRIBE", "").strip()
        if not liff_id:
            abort(500, description="LIFF_ID_SUBSCRIBE 未設定，請在 .env 加入此變數後重啟。")
        return render_template("liff/test.html", liff_id=liff_id)

    # LINE Webhook
    from blueprints.webhook import bp as webhook_bp
    app.register_blueprint(webhook_bp)

    # LIFF API (Stage 3 Group C)
    from blueprints.liff_api import bp as liff_api_bp
    app.register_blueprint(liff_api_bp)

    # Internal API (Stage 5 — TEP 呼叫入口)
    from blueprints.internal_api import bp as internal_api_bp
    app.register_blueprint(internal_api_bp)

    # Admin / LINE 訊息測試 API (Pre-Stage 4)
    from blueprints.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
