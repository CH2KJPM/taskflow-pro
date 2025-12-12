from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔥 Type d'utilisateur : "standard" ou "creator"
    user_type = db.Column(db.String(20), nullable=False, default="standard")

    # 🔥 Indique si l'utilisateur a terminé l'onboarding
    onboarding_done = db.Column(db.Boolean, default=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_creator(self) -> bool:
        return self.user_type == "creator"


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔥 Chaque projet appartient à un utilisateur
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    owner = db.relationship("User", backref="projects")

    tasks = db.relationship("Task", backref="project", lazy=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)

    # Tâche de base
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Workflow général
    status = db.Column(db.String(20), default="todo")  # todo / in_progress / done
    priority = db.Column(db.String(10), default="medium")

    # 🔥 Mode créateur
    task_type = db.Column(db.String(20), default="general")
    # general = tâche classique
    # content = contenu (reel, short, etc.)

    platform = db.Column(db.String(20), nullable=True)
    creator_stage = db.Column(db.String(20), nullable=True)

    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
