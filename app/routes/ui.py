from flask import Blueprint, render_template, request, redirect
from sqlalchemy import or_

from ..extensions import db
from ..models import MyTask, Project

ui_bp = Blueprint("ui", __name__)

# Option A: "/" redirects to dashboard
@ui_bp.route("/", methods=["GET"])
def home():
    return redirect("/dashboard")


# Dashboard: list/create projects
@ui_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if name:
            db.session.add(Project(name=name))
            db.session.commit()
        return redirect("/dashboard")

    projects = Project.query.order_by(Project.created.desc()).all()
    return render_template("dashboard.html", projects=projects)


# Rename project
@ui_bp.route("/projects/<int:project_id>/rename", methods=["POST"])
def rename_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    new_name = (request.form.get("name") or "").strip()
    if new_name:
        project.name = new_name
        db.session.commit()
    return redirect("/dashboard")


# Delete project (cascades delete tasks because of relationship cascade)
@ui_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return redirect("/dashboard")


# Project Tasks page (your current todo UI)
@ui_bp.route("/projects/<int:project_id>", methods=["GET", "POST"])
def project_tasks(project_id: int):
    project = Project.query.get_or_404(project_id)

    # Create task
    if request.method == "POST":
        content = (request.form.get("content") or "").strip()
        if content:
            db.session.add(MyTask(content=content, project_id=project_id))
            db.session.commit()
        return redirect(f"/projects/{project_id}")

    # List tasks (search + pagination + sort)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 5, type=int)
    q = request.args.get("q", "", type=str).strip()
    sort = request.args.get("sort", "desc", type=str)

    # guardrails
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 5
    if per_page > 100:
        per_page = 100

    query = MyTask.query.filter(MyTask.project_id == project_id)

    # Multi-word search (matches any word)
    if q:
        words = [w for w in q.split() if w]
        conditions = [MyTask.content.ilike(f"%{w}%") for w in words]
        query = query.filter(or_(*conditions))

    # Sorting
    if sort == "asc":
        query = query.order_by(MyTask.created.asc())
    else:
        query = query.order_by(MyTask.created.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "index.html",
        project=project,
        project_id=project_id,
        tasks=pagination.items,
        pagination=pagination,
        per_page=per_page,
        q=q,
        sort=sort,
    )


# Delete a task (project-scoped)
@ui_bp.route("/projects/<int:project_id>/delete/<int:task_id>", methods=["GET"])
def delete_task(project_id: int, task_id: int):
    task = MyTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return redirect(f"/projects/{project_id}")


# Update task (project-scoped)
@ui_bp.route("/projects/<int:project_id>/update/<int:task_id>", methods=["GET", "POST"])
def update_task(project_id: int, task_id: int):
    task = MyTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()

    if request.method == "POST":
        content = (request.form.get("content") or "").strip()
        if content:
            task.content = content
            db.session.commit()
        return redirect(f"/projects/{project_id}")

    return render_template("edit.html", update_task=task, project_id=project_id)
