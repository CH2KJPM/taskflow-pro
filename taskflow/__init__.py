# taskflow/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # 👈 où rediriger si non connecté


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # 👇 force le chargement des modèles (pour user_loader)
    from .models import User, Project, Task  # noqa: F401

    # 👇 importe les blueprints
    from .routes import main_bp
    from .auth import auth_bp

    # 👇 enregistre les blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    return app
