# taskflow/config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # DATABASE_URL fourni par Render / Neon
    db_url = os.environ.get("DATABASE_URL", "").strip()

    # Fix Neon / Render : postgres:// → postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = (
        db_url if db_url else "sqlite:///taskflow.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False