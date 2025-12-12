# taskflow/config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    _db_url = (os.environ.get("DATABASE_URL") or "").strip()

    # Render/Neon peuvent fournir postgres://, SQLAlchemy veut postgresql://
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _db_url if _db_url else "sqlite:///taskflow.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False