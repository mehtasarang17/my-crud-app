from flask import Blueprint, render_template, request, redirect
from ..extensions import db
from ..models import MyTask
from ..services.search import apply_task_search

ui_bp = Blueprint("ui", __name__)

@ui_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        current_task = request.form["content"]
        task = MyTask(content=current_task)
        db.session.add(task)
        db.session.commit()
        return redirect("/")

    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=5, type=int)
    q = request.args.get("q", default="", type=str).strip()

    if per_page < 1:
        per_page = 5
    if per_page > 100:
        per_page = 100

    query = apply_task_search(MyTask.query, q)
    pagination = query.order_by(MyTask.created.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "index.html",
        tasks=pagination.items,
        pagination=pagination,
        per_page=per_page,
        q=q
    )


@ui_bp.route("/delete/<int:id>")
def delete(id: int):
    task = MyTask.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect("/")


@ui_bp.route("/update/<int:id>", methods=["GET", "POST"])
def update(id: int):
    task = MyTask.query.get_or_404(id)
    if request.method == "POST":
        task.content = request.form["content"]
        db.session.commit()
        return redirect("/")
    return render_template("edit.html", update_task=task)
