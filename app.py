import os
from flask import Flask
from dotenv import load_dotenv
from extensions import db, migrate

load_dotenv()


def create_app():
    app = Flask(__name__)

    # 資料庫設定（MySQL，與 Web App / TEP 統一）
    db_url = os.getenv(
        "DATABASE_URL", "mysql+pymysql://root:@localhost:3306/gateway?charset=utf8mb4"
    )
    # 部署環境（Zeabur）常給 mysql:// 開頭，SQLAlchemy 需要明確指定 pymysql driver
    if db_url.startswith("mysql://"):
        db_url = "mysql+pymysql://" + db_url[len("mysql://"):]
    # 確保 utf8mb4（中文不亂碼）
    if db_url.startswith("mysql+pymysql://") and "charset=" not in db_url:
        db_url += ("&" if "?" in db_url else "?") + "charset=utf8mb4"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # 初始化 extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # 把 models import 進來，並在啟動時確保資料表存在
    # （雲端免手動 flask db upgrade；DB 還沒設好時不讓 app 崩潰，postback 仍可運作）
    with app.app_context():
        import models  # noqa: F401
        try:
            db.create_all()
        except Exception as exc:
            app.logger.warning("db.create_all 跳過（DB 可能還沒設好）：%s", exc)

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
