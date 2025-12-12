# taskflow/config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    db_url = (os.environ.get("DATABASE_URL") or "").strip()

    # Neon/Render peuvent donner "postgres://", SQLAlchemy veut "postgresql://"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url if db_url else "sqlite:///taskflow.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False