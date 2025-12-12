# taskflow/auth.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            flash("Tous les champs sont obligatoires.", "error")
            return redirect(url_for("auth.register"))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Un compte existe déjà avec cet e-mail.", "error")
            return redirect(url_for("auth.register"))

        user = User(name=name, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # 🔥 Connexion automatique du nouvel utilisateur
        login_user(user)

        flash("Compte créé, configurons ton espace ✨", "success")
        return redirect(url_for("main.onboarding"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash("Identifiants invalides.", "error")
            return redirect(url_for("auth.login"))

        login_user(user)
        flash("Connexion réussie.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Tu es déconnecté.", "success")
    return redirect(url_for("auth.login"))
