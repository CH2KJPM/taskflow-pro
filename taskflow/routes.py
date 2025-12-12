# taskflow/routes.py

import calendar
from datetime import datetime, date, timedelta
import calendar as pycal
from sqlalchemy import or_

from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from .models import User, Project, Task, db
from flask import jsonify


main_bp = Blueprint("main", __name__)

# 🔥 Modèles de contenus pour créateurs
CONTENT_TEMPLATES = {
    "tiktok_tip": {
        "label": "TikTok · Astuce rapide",
        "platform": "tiktok",
        "default_title": "Astuce rapide : une astuce en 3 étapes",
        "default_description": (
            "Hook (3 sec) : pose une question ou un problème.\n"
            "• Étape 1 : contexte rapide\n"
            "• Étape 2 : ta solution\n"
            "• Étape 3 : exemple concret\n"
            "CTA : abonne-toi pour plus d’astuces."
        ),
        "default_creator_stage": "idea",
    },
    "tiktok_storytime": {
        "label": "TikTok · Storytime",
        "platform": "tiktok",
        "default_title": "Storytime : ce qui m’est arrivé…",
        "default_description": (
            "Intro : annonce le thème de l’histoire.\n"
            "• Début : pose le contexte\n"
            "• Tension : le problème ou le moment clé\n"
            "• Résolution : ce que tu en retires\n"
            "CTA : demande l’avis des gens en commentaire."
        ),
        "default_creator_stage": "idea",
    },
    "reel_facecam": {
        "label": "Instagram Reel · Facecam conseil",
        "platform": "instagram",
        "default_title": "3 conseils pour progresser sur …",
        "default_description": (
            "Hook : phrase choc ou chiffre.\n"
            "Conseil 1\n"
            "Conseil 2\n"
            "Conseil 3\n"
            "CTA : sauvegarde le reel pour plus tard."
        ),
        "default_creator_stage": "idea",
    },
    "shorts_tuto": {
        "label": "YouTube Shorts · Tutoriel express",
        "platform": "youtube",
        "default_title": "Comment faire X en 30 secondes",
        "default_description": (
            "Annonce du résultat final.\n"
            "Étape 1\n"
            "Étape 2\n"
            "Étape 3\n"
            "CTA : abonne-toi pour les tutos détaillés."
        ),
        "default_creator_stage": "idea",
    },
    "yt_long_tuto": {
        "label": "YouTube · Tuto complet 5–10 min",
        "platform": "youtube",
        "default_title": "Tutoriel complet : apprendre à …",
        "default_description": (
            "Intro : ce que la vidéo va apporter.\n"
            "Chapitre 1 : bases\n"
            "Chapitre 2 : mise en pratique\n"
            "Chapitre 3 : astuces avancées\n"
            "Conclusion : résumé + CTA (abonnement, like, commentaire)."
        ),
        "default_creator_stage": "idea",
    },
}

# ---------- ONBOARDING ----------
@main_bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    # Si l'onboarding est déjà fait, on renvoie au bon endroit
    if getattr(current_user, "onboarding_done", False):
        if getattr(current_user, "user_type", None) == "creator":
            return redirect(url_for("main.creator_dashboard"))
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        user_type = request.form.get("user_type")

        if user_type not in ("simple", "creator"):
            flash("Type d’utilisateur invalide.", "error")
            return redirect(url_for("main.onboarding"))

        # Mise à jour de l'utilisateur
        current_user.user_type = user_type
        current_user.onboarding_done = True
        db.session.commit()

        flash("Bienvenue dans TaskFlow !", "success")

        # Redirection selon le type choisi
        if user_type == "creator":
            return redirect(url_for("main.creator_dashboard"))
        else:
            return redirect(url_for("main.dashboard"))

    return render_template("onboarding.html")

# ---------- DASHBOARD CRÉATEUR ----------

@main_bp.route("/creator")
@login_required
def creator_dashboard():
    if not current_user.is_creator:
        flash("Accès réservé aux créateurs.", "error")
        return redirect(url_for("main.dashboard"))

    today = date.today()
    start_today = datetime.combine(today, datetime.min.time())
    end_today = datetime.combine(today, datetime.max.time())

    # Base : toutes les tâches "contenu" de l'utilisateur
    base_query = (
        Task.query
        .join(Project)
        .filter(
            Project.owner_id == current_user.id,
            Task.task_type == "content",
        )
    )

    contents_all = base_query.all()

    # Stats globales
    total_contents = len(contents_all)
    contents_to_film = sum(1 for t in contents_all if t.creator_stage == "to_film")
    contents_to_edit = sum(1 for t in contents_all if t.creator_stage == "to_edit")
    contents_scheduled = sum(1 for t in contents_all if t.creator_stage == "scheduled")

    contents_scheduled_today = (
        base_query
        .filter(
            Task.creator_stage == "scheduled",
            Task.due_date.isnot(None),
            Task.due_date >= start_today,
            Task.due_date <= end_today,
        )
        .count()
    )

    # Prochains contenus (7 jours)
    upcoming_contents = (
        base_query
        .filter(
            Task.status != "done",
            Task.due_date.isnot(None),
            Task.due_date >= start_today,
            Task.due_date <= start_today + timedelta(days=7),
        )
        .order_by(Task.due_date.asc())
        .all()
    )

    # Boîte à idées
    backlog_ideas = (
        base_query
        .filter(Task.creator_stage == "idea")
        .order_by(Task.created_at.desc())
        .all()
    )

    # Backlog sans date
    backlog_no_date = (
        base_query
        .filter(
            Task.due_date.is_(None),
            Task.status != "done",
        )
        .order_by(Task.created_at.desc())
        .all()
    )

    # ---------- FOCUS DU JOUR ----------
    focus_query = (
        base_query
        .filter(
            Task.status != "done",
            Task.creator_stage.in_(["to_film", "to_edit"]),
        )
    )

    # 1) priorité : contenus à filmer/éditer DU JOUR
    focus_content = (
        focus_query
        .filter(
            Task.due_date.isnot(None),
            Task.due_date >= start_today,
            Task.due_date <= end_today,
        )
        .order_by(
            Task.priority.desc(),
            Task.due_date.asc(),
            Task.created_at.asc(),
        )
        .first()
    )

    # 2) sinon : prochain contenu à filmer/éditer (peu importe la date)
    if focus_content is None:
        focus_content = (
            focus_query
            .order_by(
                Task.due_date.asc(),
                Task.priority.desc(),
                Task.created_at.asc(),
            )
            .first()
        )

    return render_template(
        "creator_dashboard.html",
        today=today,
        total_contents=total_contents,
        contents_to_film=contents_to_film,
        contents_to_edit=contents_to_edit,
        contents_scheduled=contents_scheduled,
        contents_scheduled_today=contents_scheduled_today,
        upcoming_contents=upcoming_contents,
        backlog_ideas=backlog_ideas,
        backlog_no_date=backlog_no_date,
        focus_content=focus_content,
    )

@main_bp.route("/search")
@login_required
def search():
    q = (request.args.get("q") or "").strip()

    # Si rien tapé → retour au dashboard avec un petit message
    if not q:
        flash("Entre un mot-clé pour lancer une recherche.", "info")
        return redirect(url_for("main.dashboard"))

    # Recherche dans les projets de l’utilisateur
    projects = (
        Project.query
        .filter(
            Project.owner_id == current_user.id,
            or_(
                Project.name.ilike(f"%{q}%"),
                Project.description.ilike(f"%{q}%")
            )
        )
        .order_by(Project.created_at.desc())
        .all()
    )

    # Recherche dans les tâches de ses projets
    tasks = (
        Task.query
        .join(Project)
        .filter(
            Project.owner_id == current_user.id,
            or_(
                Task.title.ilike(f"%{q}%"),
                Task.description.ilike(f"%q%")
            )
        )
        .order_by(Task.created_at.desc())
        .all()
    )

    # On peut séparer un peu pour l’affichage
    general_tasks = [t for t in tasks if t.task_type != "content"]
    content_tasks = [t for t in tasks if t.task_type == "content"]

    return render_template(
        "search.html",
        q=q,
        projects=projects,
        general_tasks=general_tasks,
        content_tasks=content_tasks,
        total_projects=len(projects),
        total_tasks=len(tasks),
    )


@main_bp.route("/creator/pipeline")
@login_required
def creator_pipeline():
    # réservé aux créateurs
    if not current_user.is_creator:
        flash("Accès réservé aux créateurs.", "error")
        return redirect(url_for("main.dashboard"))

    # toutes les tâches de contenu du user (non terminées)
    tasks = (
        Task.query
        .join(Project)
        .filter(
            Project.owner_id == current_user.id,
            Task.task_type == "content",
            Task.status != "done",
        )
        .order_by(Task.created_at.desc())
        .all()
    )

    # colonnes du pipeline
    columns = {
        "idea": [],
        "to_film": [],
        "to_edit": [],
        "scheduled": [],
        "published": [],
        "none": [],
    }

    for t in tasks:
        key = t.creator_stage or "none"
        if key not in columns:
            key = "none"
        columns[key].append(t)

    # meta pour affichage dans le template
    columns_meta = [
        {"key": "idea",      "label": "Idées"},
        {"key": "to_film",   "label": "À filmer"},
        {"key": "to_edit",   "label": "À monter"},
        {"key": "scheduled", "label": "Programmés"},
        {"key": "published", "label": "Publiés"},
        {"key": "none",      "label": "Non classés"},
    ]

    return render_template(
        "creator_pipeline.html",
        columns=columns,
        columns_meta=columns_meta,
    )


@main_bp.route("/creator/content/new", methods=["GET", "POST"])
@login_required
def creator_new_content():
    # réservé aux créateurs
    if not current_user.is_creator:
        flash("Accès réservé aux créateurs.", "error")
        return redirect(url_for("main.dashboard"))

    # Projets du user (pour le select)
    projects = (
        Project.query
        .filter_by(owner_id=current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        project_id_str = request.form.get("project_id") or ""
        platform = request.form.get("platform") or None
        creator_stage = request.form.get("creator_stage") or "idea"
        priority = request.form.get("priority") or "medium"
        due_date_str = request.form.get("due_date") or ""

        # validation simple
        if not title:
            flash("Le titre du contenu est obligatoire.", "error")
            return redirect(url_for("main.creator_new_content"))

        if not project_id_str:
            flash("Sélectionne un projet.", "error")
            return redirect(url_for("main.creator_new_content"))

        try:
            project_id = int(project_id_str)
        except ValueError:
            flash("Projet invalide.", "error")
            return redirect(url_for("main.creator_new_content"))

        project = Project.query.filter_by(
            id=project_id,
            owner_id=current_user.id
        ).first()
        if not project:
            flash("Projet introuvable ou non autorisé.", "error")
            return redirect(url_for("main.creator_new_content"))

        # date optionnelle
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                flash("Format de date invalide, la date a été ignorée.", "error")

        # création de la tâche de contenu
        task = Task(
            project_id=project.id,
            title=title,
            description=description,
            status="todo",
            priority=priority,
            due_date=due_date,
            task_type="content",
            platform=platform,
            creator_stage=creator_stage,
        )
        db.session.add(task)
        db.session.commit()

        flash("Nouveau contenu créé ✅", "success")
        return redirect(url_for("main.creator_dashboard"))

    return render_template("creator_new_content.html", projects=projects)

# ---------- HOME / LANDING ----------
@main_bp.route("/")
def home():
    """
    Page publique (landing) si l'utilisateur n'est pas connecté.
    Dashboard direct s'il est connecté.
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("landing.html")


# ---------- DASHBOARD ----------
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Tous les projets de l'utilisateur
    projects = Project.query.filter_by(owner_id=current_user.id).all()

    # Base : toutes les tâches liées à ses projets
    base_tasks_query = (
        Task.query
        .join(Project)
        .filter(Project.owner_id == current_user.id)
    )

    # --- Compteurs globaux ---
    total_projects = len(projects)
    total_tasks_open = base_tasks_query.filter(Task.status != "done").count()
    total_general_open = (
        base_tasks_query
        .filter(Task.status != "done", Task.task_type != "content")
        .count()
    )
    total_content_open = (
        base_tasks_query
        .filter(Task.status != "done", Task.task_type == "content")
        .count()
    )

    # --- Aujourd'hui ---
    today = date.today()
    start_today = datetime.combine(today, datetime.min.time())
    end_today = datetime.combine(today, datetime.max.time())

    todays_contents = (
        base_tasks_query
        .filter(
            Task.task_type == "content",
            Task.due_date.isnot(None),
            Task.due_date >= start_today,
            Task.due_date <= end_today,
            Task.status != "done",
        )
        .count()
    )

    # --- Pipeline créateur (si user créateur) ---
    contents_to_film = (
        base_tasks_query
        .filter(
            Task.task_type == "content",
            Task.creator_stage == "to_film",
            Task.status != "done",
        )
        .count()
    )
    contents_to_edit = (
        base_tasks_query
        .filter(
            Task.task_type == "content",
            Task.creator_stage == "to_edit",
            Task.status != "done",
        )
        .count()
    )
    contents_scheduled = (
        base_tasks_query
        .filter(
            Task.task_type == "content",
            Task.creator_stage == "scheduled",
            Task.status != "done",
        )
        .count()
    )

    # --- Stats de productivité : semaine + mois ---
    # Lundi de la semaine actuelle
    start_week = today - timedelta(days=today.weekday())
    # 1er jour du mois
    start_month = today.replace(day=1)

    tasks_done_week = (
        base_tasks_query
        .filter(
            Task.status == "done",
            Task.updated_at >= datetime.combine(start_week, datetime.min.time()),
            Task.updated_at <= end_today,
        )
        .count()
    )

    tasks_done_month = (
        base_tasks_query
        .filter(
            Task.status == "done",
            Task.updated_at >= datetime.combine(start_month, datetime.min.time()),
            Task.updated_at <= end_today,
        )
        .count()
    )

    return render_template(
        "dashboard.html",
        projects=projects,
        total_projects=total_projects,
        total_tasks_open=total_tasks_open,
        total_general_open=total_general_open,
        total_content_open=total_content_open,
        todays_contents=todays_contents,
        contents_to_film=contents_to_film,
        contents_to_edit=contents_to_edit,
        contents_scheduled=contents_scheduled,
        today=today,
        tasks_done_week=tasks_done_week,
        tasks_done_month=tasks_done_month,
    )


# ---------- VUE "AUJOURD'HUI" ----------
@main_bp.route("/today")
@login_required
def today():
    today_date = date.today()

    # --- TÂCHES DU JOUR (non terminées) ---
    tasks_today = (
        Task.query
        .join(Project)
        .filter(
            Project.owner_id == current_user.id,
            Task.due_date.isnot(None),
            Task.due_date >= datetime.combine(today_date, datetime.min.time()),
            Task.due_date <= datetime.combine(today_date, datetime.max.time()),
            Task.status != "done",
        )
        .order_by(Task.priority.desc(), Task.created_at.desc())
        .all()
    )

    # --- TÂCHES EN COURS (toutes dates) ---
    tasks_in_progress = (
        Task.query
        .join(Project)
        .filter(
            Project.owner_id == current_user.id,
            Task.status == "in_progress",
        )
        .order_by(Task.priority.desc(), Task.created_at.desc())
        .all()
    )

    # --- Séparation Général / Contenu pour les tâches du jour ---
    general_tasks = [t for t in tasks_today if t.task_type != "content"]
    content_tasks = [t for t in tasks_today if t.task_type == "content"]

    # --- Séparation "en cours" ---
    general_in_progress = [
        t for t in tasks_in_progress if t.task_type != "content"
    ]
    content_in_progress = [
        t for t in tasks_in_progress if t.task_type == "content"
    ]

    # --- Regroupement des contenus du jour par étapes ---
    content_by_stage = {
        "idea": [],
        "to_film": [],
        "to_edit": [],
        "scheduled": [],
        "published": [],
        "none": [],
    }

    for t in content_tasks:
        stage = t.creator_stage or "none"
        if stage not in content_by_stage:
            stage = "none"
        content_by_stage[stage].append(t)

    # --- Compteurs ---
    total_today = len(tasks_today)
    total_general = len(general_tasks)
    total_content = len(content_tasks)

    # --- ENVOI DU TEMPLATE ---
    return render_template(
        "today.html",
        today=today_date,
        general_tasks=general_tasks,
        general_in_progress=general_in_progress,
        content_by_stage=content_by_stage,
        content_in_progress=content_in_progress,  # <-- IMPORTANT
        total_today=total_today,
        total_general=total_general,
        total_content=total_content,
    )

# ---------- CALENDRIER (mois / semaine) ----------
@main_bp.route("/calendar")
@login_required
def calendar_view():
    view = request.args.get("view", "week")

    project_id = request.args.get("project_id", type=int)
    priority = request.args.get("priority") or None
    status = request.args.get("status") or None
    task_type = request.args.get("task_type") or None
    platform = request.args.get("platform") or None

    # Tâches de l'utilisateur avec une date (calendrier éditorial)
    base_query = (
        Task.query.join(Project)
        .filter(
            Project.owner_id == current_user.id,
            Task.due_date.isnot(None),
        )
    )

    if project_id:
        base_query = base_query.filter(Task.project_id == project_id)
    if priority:
        base_query = base_query.filter(Task.priority == priority)
    if status:
        base_query = base_query.filter(Task.status == status)
    if task_type:
        base_query = base_query.filter(Task.task_type == task_type)
    if platform:
        base_query = base_query.filter(Task.platform == platform)

    tasks = base_query.all()

    projects = (
        Project.query.filter_by(owner_id=current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )

    today = date.today()

    # -----------------------
    # Vue hebdomadaire
    # -----------------------
    if view == "week":
        week_start_str = request.args.get("week_start")
        if week_start_str:
            try:
                week_start = datetime.strptime(week_start_str, "%Y-%m-%d").date()
            except ValueError:
                week_start = today - timedelta(days=today.weekday())
        else:
            # Lundi de la semaine actuelle
            week_start = today - timedelta(days=today.weekday())

        week_days = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            day_tasks = [
                t for t in tasks
                if t.due_date is not None and t.due_date.date() == d
            ]
            week_days.append({"date": d, "tasks": day_tasks})

        prev_week_start = week_start - timedelta(days=7)
        next_week_start = week_start + timedelta(days=7)

        return render_template(
            "calendar.html",
            view="week",
            projects=projects,
            week_days=week_days,
            week_start=week_start,
            prev_week_start=prev_week_start,
            next_week_start=next_week_start,
            current_filters={
                "project_id": project_id,
                "priority": priority,
                "status": status,
                "task_type": task_type,
                "platform": platform,
            },
        )

    # -----------------------
    # Vue mensuelle (par défaut)
    # -----------------------
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    first_day = date(year, month, 1)
    _, days_in_month = pycal.monthrange(year, month)
    last_day = date(year, month, days_in_month)

    # On commence le calendrier le lundi de la semaine du 1er
    start = first_day - timedelta(days=first_day.weekday())

    weeks = []
    current = start
    # 6 lignes max (classique calendrier)
    for _ in range(6):
        week = []
        for _ in range(7):
            d = current
            day_tasks = [
                t for t in tasks
                if t.due_date is not None and t.due_date.date() == d
            ]
            week.append(
                {
                    "date": d,
                    "tasks": day_tasks,
                    "is_current_month": (d.month == month),
                }
            )
            current += timedelta(days=1)
        weeks.append(week)

    # Mois précédent / suivant
    if month == 1:
        prev_month = 12
        prev_month_year = year - 1
    else:
        prev_month = month - 1
        prev_month_year = year

    if month == 12:
        next_month = 1
        next_month_year = year + 1
    else:
        next_month = month + 1
        next_month_year = year

    return render_template(
        "calendar.html",
        view="month",
        projects=projects,
        weeks=weeks,
        year=year,
        month=month,
        prev_month=prev_month,
        prev_month_year=prev_month_year,
        next_month=next_month,
        next_month_year=next_month_year,
        current_filters={
            "project_id": project_id,
            "priority": priority,
            "status": status,
            "task_type": task_type,
            "platform": platform,
        },
    )


# ---------- PROFIL ----------
@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not name or not email:
            flash("Le nom et l’adresse e-mail sont obligatoires.", "error")
            return redirect(url_for("main.profile"))

        # Vérifier si l'email est déjà utilisé par un autre user
        existing = User.query.filter(
            User.email == email,
            User.id != current_user.id
        ).first()
        if existing:
            flash("Cette adresse e-mail est déjà utilisée par un autre compte.", "error")
            return redirect(url_for("main.profile"))

        current_user.name = name
        current_user.email = email
        db.session.commit()

        flash("Profil mis à jour avec succès.", "success")
        return redirect(url_for("main.profile"))

    return render_template("profile.html")


# ---------- CHANGER LE MOT DE PASSE ----------
@main_bp.route("/profile/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_password or not new_password or not confirm_password:
            flash("Tous les champs sont obligatoires.", "error")
            return redirect(url_for("main.change_password"))

        if not current_user.check_password(current_password):
            flash("Le mot de passe actuel est incorrect.", "error")
            return redirect(url_for("main.change_password"))

        if new_password != confirm_password:
            flash("La confirmation du mot de passe ne correspond pas.", "error")
            return redirect(url_for("main.change_password"))

        if len(new_password) < 6:
            flash("Le nouveau mot de passe doit contenir au moins 6 caractères.", "error")
            return redirect(url_for("main.change_password"))

        current_user.set_password(new_password)
        db.session.commit()
        flash("Mot de passe modifié avec succès.", "success")
        return redirect(url_for("main.profile"))

    return render_template("change_password.html")


# ---------- CRÉER UN PROJET ----------
@main_bp.route("/project/new", methods=["GET", "POST"])
@login_required
def create_project():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        if not name:
            flash("Le nom du projet est obligatoire.", "error")
            return redirect(url_for("main.create_project"))

        project = Project(
            name=name,
            description=description,
            owner_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()

        flash("Projet créé avec succès.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("create_project.html")


# ---------- PAGE PROJET (+ Kanban) ----------
@main_bp.route("/project/<int:project_id>")
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)

    # sécurité : vérifier que le projet appartient au user
    if project.owner_id != current_user.id:
        flash("Accès non autorisé à ce projet.", "error")
        return redirect(url_for("main.dashboard"))

    tasks_todo = [t for t in project.tasks if t.status == "todo"]
    tasks_in_progress = [t for t in project.tasks if t.status == "in_progress"]
    tasks_done = [t for t in project.tasks if t.status == "done"]

    return render_template(
        "project_detail.html",
        project=project,
        tasks_todo=tasks_todo,
        tasks_in_progress=tasks_in_progress,
        tasks_done=tasks_done,
    )


# ---------- AJOUTER UNE TÂCHE ----------
@main_bp.route("/project/<int:project_id>/task/add", methods=["POST"])
@login_required
def add_task(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash("Accès non autorisé à ce projet.", "error")
        return redirect(url_for("main.dashboard"))

    title = request.form.get("title")
    description = request.form.get("description")
    priority = request.form.get("priority") or "medium"
    due_date_str = request.form.get("due_date")

    # 🔥 Nouveaux champs
    task_type = request.form.get("task_type") or "general"  # general / content
    platform = request.form.get("platform") or None
    creator_stage = request.form.get("creator_stage") or None

    if not title:
        flash("Le titre de la tâche est obligatoire.", "error")
        return redirect(url_for("main.project_detail", project_id=project_id))

    # Si ce n'est pas une tâche de contenu, on vide les champs créateur
    if task_type != "content":
        platform = None
        creator_stage = None

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        except ValueError:
            flash("Format de date invalide, la date limite a été ignorée.", "error")
            due_date = None

    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        status="todo",
        priority=priority,
        due_date=due_date,
        task_type=task_type,
        platform=platform,
        creator_stage=creator_stage,
    )
    db.session.add(task)
    db.session.commit()

    flash("Tâche ajoutée.", "success")
    return redirect(url_for("main.project_detail", project_id=project_id))

# ---------- CHANGER LE STATUT D’UNE TÂCHE ----------
@main_bp.route("/task/<int:task_id>/status/<string:new_status>", methods=["POST"])
@login_required
def update_task_status(task_id, new_status):
    task = Task.query.get_or_404(task_id)
    project = task.project

    if project.owner_id != current_user.id:
        flash("Accès non autorisé à ce projet.", "error")
        return redirect(url_for("main.dashboard"))

    if new_status not in ["todo", "in_progress", "done"]:
        flash("Statut invalide.", "error")
        return redirect(url_for("main.project_detail", project_id=project.id))

    task.status = new_status
    db.session.commit()

    if new_status == "done":
        flash("Tâche marquée comme terminée ✅", "success")
    elif new_status == "in_progress":
        flash("Tâche passée en cours.", "info")
    else:
        flash("Tâche remise en à faire.", "info")

    return redirect(request.referrer or url_for("main.calendar_view", view="week"))


# ---------- CHANGER L'ÉTAPE CRÉATEUR D’UNE TÂCHE ----------
@main_bp.route("/task/<int:task_id>/creator_stage/<string:new_stage>", methods=["POST"])
@login_required
def update_creator_stage(task_id, new_stage):
    allowed_stages = ["idea", "to_film", "to_edit", "scheduled", "published", "none"]

    if new_stage not in allowed_stages:
        flash("Étape de contenu invalide.", "error")
        return redirect(request.referrer or url_for("main.creator_dashboard"))

    task = Task.query.get_or_404(task_id)
    project = task.project

    # sécurité : le projet doit t'appartenir
    if project.owner_id != current_user.id:
        flash("Accès non autorisé à cette tâche.", "error")
        return redirect(url_for("main.dashboard"))

    if task.task_type != "content":
        flash("Cette tâche n’est pas un contenu.", "error")
        return redirect(request.referrer or url_for("main.creator_dashboard"))

    task.creator_stage = new_stage
    db.session.commit()

    flash("Étape du contenu mise à jour.", "success")
    return redirect(request.referrer or url_for("main.creator_pipeline"))



# ---------- SUPPRIMER UNE TÂCHE ----------
@main_bp.route("/task/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project

    if project.owner_id != current_user.id:
        flash("Accès non autorisé à ce projet.", "error")
        return redirect(url_for("main.dashboard"))

    db.session.delete(task)
    db.session.commit()
    flash("Tâche supprimée.", "success")
    return redirect(url_for("main.project_detail", project_id=project.id))


# ---------- SUPPRIMER UN PROJET ----------
@main_bp.route("/project/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()

    # On supprime d’abord les tâches liées (au cas où la cascade n’est pas config)
    for task in project.tasks:
        db.session.delete(task)

    db.session.delete(project)
    db.session.commit()
    flash("Projet supprimé avec toutes ses tâches.", "success")
    return redirect(url_for("main.dashboard"))


# ---------- MODIFIER UNE TÂCHE ----------
@main_bp.route("/task/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project

    if project.owner_id != current_user.id:
        flash("Accès non autorisé à ce projet.", "error")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        priority = request.form.get("priority") or "medium"
        due_date_str = request.form.get("due_date")

        task_type = request.form.get("task_type") or "general"
        platform = request.form.get("platform") or None
        creator_stage = request.form.get("creator_stage") or None

        if not title:
            flash("Le titre de la tâche est obligatoire.", "error")
            return redirect(url_for("main.edit_task", task_id=task.id))

        if task_type != "content":
            platform = None
            creator_stage = None

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                flash("Format de date invalide, la date limite a été ignorée.", "error")

        task.title = title
        task.description = description
        task.priority = priority
        task.due_date = due_date
        task.task_type = task_type
        task.platform = platform
        task.creator_stage = creator_stage

        db.session.commit()
        flash("Tâche mise à jour.", "success")
        return redirect(url_for("main.project_detail", project_id=project.id))

    return render_template("edit_task.html", task=task, project=project)

# ---------- PRICING ----------
@main_bp.route("/pricing")
def pricing():
    return render_template("pricing.html")


@main_bp.route("/upgrade_creator", methods=["POST"])
@login_required
def upgrade_creator():
    # Plus tard : ici tu brancheras Stripe / paiement réel.
    current_user.user_type = "creator"
    db.session.commit()

    flash("Ton compte est maintenant en mode Créateur 🚀", "success")
    return redirect(url_for("main.creator_dashboard"))


# ---------- ANALYTICS ----------

@main_bp.route("/analytics", methods=["GET"])
@login_required
def analytics():
    from datetime import date, timedelta

    today = date.today()

    # ----- Base query : tâches de l'utilisateur -----
    base_query = (
        Task.query
        .join(Project)
        .filter(Project.owner_id == current_user.id)
    )

    # ----- Stats semaine / mois -----
    # Début de la semaine (lundi)
    start_week = today - timedelta(days=today.weekday())
    # Début du mois
    start_month = today.replace(day=1)

    week_completed = (
        base_query
        .filter(
            Task.status == "done",
            Task.updated_at >= start_week,
        )
        .count()
    )

    month_completed = (
        base_query
        .filter(
            Task.status == "done",
            Task.updated_at >= start_month,
        )
        .count()
    )

    week_general = (
        base_query
        .filter(
            Task.status == "done",
            Task.updated_at >= start_week,
            Task.task_type != "content",
        )
        .count()
    )

    week_content = (
        base_query
        .filter(
            Task.status == "done",
            Task.updated_at >= start_week,
            Task.task_type == "content",
        )
        .count()
    )

    # ----- Heatmap 12 derniers mois -----
    start_date = today - timedelta(days=364)

    completed_tasks = (
        base_query
        .filter(
            Task.status == "done",
            Task.updated_at >= start_date,
        )
        .all()
    )

    heatmap_dict = {}
    for t in completed_tasks:
        d = t.updated_at.date()
        heatmap_dict[d] = heatmap_dict.get(d, 0) + 1

    ordered_days = []
    for i in range(365):
        d = start_date + timedelta(days=i)
        ordered_days.append(
            {
                "date": d,
                "count": heatmap_dict.get(d, 0, ),
            }
        )

        # ---------- INSIGHT ENGINE (12 derniers mois) ----------
    today = date.today()
    one_year_ago = today - timedelta(days=365)

    # Toutes les tâches terminées du user sur les 12 derniers mois
    done_tasks = (
        Task.query
        .join(Project)
        .filter(
            Project.owner_id == current_user.id,
            Task.status == "done",
            Task.updated_at.isnot(None),
            Task.updated_at >= datetime.combine(one_year_ago, datetime.min.time()),
        )
        .all()
    )

    from collections import Counter

    best_day_name = None
    best_day_count = 0
    most_active_hour = None
    most_active_hour_count = 0

    if done_tasks:
        day_counter = Counter()
        hour_counter = Counter()

        for t in done_tasks:
            d = t.updated_at
            if not d:
                continue
            day_counter[d.weekday()] += 1      # 0 = lundi, 6 = dimanche
            hour_counter[d.hour] += 1          # 0–23

        if day_counter:
            best_day_idx, best_day_count = max(day_counter.items(), key=lambda x: x[1])
            day_labels = [
                "lundi", "mardi", "mercredi",
                "jeudi", "vendredi", "samedi", "dimanche"
            ]
            best_day_name = day_labels[best_day_idx]

        if hour_counter:
            best_hour, most_active_hour_count = max(hour_counter.items(), key=lambda x: x[1])
            most_active_hour = best_hour

    # Performance mois courant vs mois précédent
    this_month_start = date(today.year, today.month, 1)
    this_month_start_dt = datetime.combine(this_month_start, datetime.min.time())

    if today.month == 1:
        prev_month = 12
        prev_year = today.year - 1
    else:
        prev_month = today.month - 1
        prev_year = today.year

    prev_month_start = date(prev_year, prev_month, 1)
    # fin du mois précédent = début du mois courant
    prev_month_start_dt = datetime.combine(prev_month_start, datetime.min.time())
    prev_month_end_dt = this_month_start_dt

    this_month_done = (
        Task.query
        .join(Project)
        .filter(
            Project.owner_id == current_user.id,
            Task.status == "done",
            Task.updated_at >= this_month_start_dt,
        )
        .count()
    )

    prev_month_done = (
        Task.query
        .join(Project)
        .filter(
            Project.owner_id == current_user.id,
            Task.status == "done",
            Task.updated_at >= prev_month_start_dt,
            Task.updated_at < this_month_start_dt,
        )
        .count()
    )

    # Messages d'insight
    if best_day_name:
        productivity_message = (
            f"Tu termines le plus de tâches le {best_day_name} "
            f"({best_day_count} tâche(s) terminée(s) sur les 12 derniers mois)."
        )
    else:
        productivity_message = (
            "Pas encore assez de tâches terminées pour analyser ton jour le plus productif."
        )

    if most_active_hour is not None:
        next_hour = (most_active_hour + 1) % 24
        timing_message = (
            f"Tu es le plus actif entre {most_active_hour:02d}h et {next_hour:02d}h. "
            "C’est un bon créneau pour placer tes tâches importantes."
        )
    else:
        timing_message = (
            "Difficile d’identifier une heure forte pour l’instant. Continue à utiliser TaskFlow et je t’indiquerai ton meilleur créneau."
        )

    if prev_month_done == 0 and this_month_done == 0:
        trend_message = (
            "Aucune tâche terminée sur les deux derniers mois. Tu peux commencer léger avec 1–2 petites tâches par jour."
        )
    elif prev_month_done == 0 and this_month_done > 0:
        trend_message = (
            f"Ce mois-ci, tu as déjà terminé {this_month_done} tâche(s) alors que le mois dernier il n’y en avait aucune. Gros boost de productivité 💥"
        )
    else:
        delta = this_month_done - prev_month_done
        if prev_month_done > 0:
            delta_percent = (delta / prev_month_done) * 100
        else:
            delta_percent = 0

        if delta > 0:
            trend_message = (
                f"Tu as terminé {this_month_done} tâche(s) ce mois-ci "
                f"contre {prev_month_done} le mois dernier (≈ {delta_percent:+.0f}% ). "
                "Tu es en progression, continue comme ça 👏"
            )
        elif delta < 0:
            trend_message = (
                f"Tu as terminé {this_month_done} tâche(s) ce mois-ci "
                f"contre {prev_month_done} le mois dernier (≈ {delta_percent:+.0f}% ). "
                "Légère baisse de rythme — pense à regrouper tes tâches importantes sur tes meilleurs jours."
            )
        else:
            trend_message = (
                f"Tu as terminé autant de tâches ce mois-ci ({this_month_done}) que le mois dernier. "
                "Rythme stable, tu peux te challenger un peu plus si tu veux 💪"
            )

    return render_template(
        "analytics.html",
        today=today,
        week_completed=week_completed,
        month_completed=month_completed,
        week_general=week_general,
        week_content=week_content,
        heatmap=ordered_days,
        productivity_message=productivity_message,
        timing_message=timing_message,
        trend_message=trend_message,
        this_month_done=this_month_done,
        prev_month_done=prev_month_done,
    )

@main_bp.route("/task/<int:task_id>/drawer")
@login_required
def task_drawer(task_id):
    task = (
        Task.query.join(Project)
        .filter(Task.id == task_id, Project.owner_id == current_user.id)
        .first_or_404()
    )

    return render_template("partials/task_drawer.html", task=task)

# ----- Pour le déplacement de tache 

@main_bp.route("/task/<int:task_id>/move_date", methods=["POST"])
@login_required
def move_task_date(task_id):
    task = (
        Task.query.join(Project)
        .filter(Task.id == task_id, Project.owner_id == current_user.id)
        .first_or_404()
    )

    data = request.get_json(silent=True) or {}
    due_date_str = data.get("due_date")
    if not due_date_str:
        return jsonify({"error":"missing due_date"}), 400

    try:
        # task.due_date est probablement un DateTime → on set à midi pour éviter les timezone issues
        d = datetime.strptime(due_date_str, "%Y-%m-%d")
        task.due_date = d
        db.session.commit()
        return jsonify({"ok": True})
    except ValueError:
        return jsonify({"error":"bad date"}), 400



@main_bp.route("/task/<int:task_id>")
@login_required
def task_detail(task_id):
    task = (
        Task.query.join(Project)
        .filter(Task.id == task_id, Project.owner_id == current_user.id)
        .first_or_404()
    )

    return render_template("task_detail.html", task=task)