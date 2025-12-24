from flask import Blueprint, render_template, request, redirect
from ..extensions import db
from ..models import Project

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if name:
            db.session.add(Project(name=name))
            db.session.commit()
        return redirect("/dashboard")

    projects = Project.query.order_by(Project.created.desc()).all()
    return render_template("dashboard.html", projects=projects)

@dashboard_bp.route("/projects/<int:project_id>/rename", methods=["POST"])
def rename_project(project_id):
    p = Project.query.get_or_404(project_id)
    new_name = (request.form.get("name") or "").strip()
    if new_name:
        p.name = new_name
        db.session.commit()
    return redirect("/dashboard")

@dashboard_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):
    p = Project.query.get_or_404(project_id)
    db.session.delete(p) 
    db.session.commit()
    return redirect("/dashboard")
