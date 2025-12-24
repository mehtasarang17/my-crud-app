from flask import Blueprint, render_template, request, redirect
from sqlalchemy import or_
from ..extensions import db
from ..models import MyTask
from ..services.search import apply_task_search

ui_bp = Blueprint("ui", __name__)

@ui_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        content = request.form["content"].strip()
        if content:
            db.session.add(MyTask(content=content))
            db.session.commit()
        return redirect("/")

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 5, type=int)
    q = request.args.get("q", "", type=str).strip()
    sort = request.args.get("sort", "desc")

    if per_page < 1:
        per_page = 5
    if per_page > 100:
        per_page = 100

    query = MyTask.query

    if q:
        words = [w for w in q.split() if w]
        conditions = [MyTask.content.ilike(f"%{w}%") for w in words]
        query = query.filter(or_(*conditions))

    if sort == "asc":
        query = query.order_by(MyTask.created.asc())
    else:
        query = query.order_by(MyTask.created.desc())

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template(
        "index.html",
        tasks=pagination.items,
        pagination=pagination,
        per_page=per_page,
        q=q,
        sort=sort
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
