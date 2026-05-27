"""
共用的 Flask extension 實例。
放在這裡是為了避免循環 import：
  app.py → extensions → models → extensions（OK，不會繞回 app.py）
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
