from flask import Blueprint, request, jsonify, Response
from sqlalchemy import or_
from ..extensions import db
from ..models import MyTask
from ..services.search import apply_task_search
from ..services.csv_io import parse_tasks_csv, tasks_to_csv

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/tasks", methods=["GET"])
def list_tasks():
    q = request.args.get("q", default="", type=str).strip()
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=5, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 5
    if per_page > 100:
        per_page = 100

    query = apply_task_search(MyTask.query, q)
    pagination = query.order_by(MyTask.created.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "q": q,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "items": [t.to_dict() for t in pagination.items]
    }), 200


@api_bp.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400

    completed = int(data.get("completed", 0))
    task = MyTask(content=content, completed=completed)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@api_bp.route("/tasks/<int:id>", methods=["GET"])
def get_task(id: int):
    task = MyTask.query.get_or_404(id)
    return jsonify(task.to_dict()), 200


@api_bp.route("/tasks/<int:id>", methods=["PUT"])
def update_task(id: int):
    task = MyTask.query.get_or_404(id)
    data = request.get_json(silent=True) or {}

    if "content" in data:
        content = (data["content"] or "").strip()
        if not content:
            return jsonify({"error": "content cannot be empty"}), 400
        task.content = content

    if "completed" in data:
        task.completed = int(data["completed"])

    db.session.commit()
    return jsonify(task.to_dict()), 200


@api_bp.route("/tasks/<int:id>", methods=["DELETE"])
def delete_task(id: int):
    task = MyTask.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return "", 204


@api_bp.route("/tasks/import-csv", methods=["POST"])
def api_import_csv():
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "no file selected"}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file"}), 400

    tasks_to_insert, inserted, skipped, errors = parse_tasks_csv(file)

    if tasks_to_insert:
        try:
            db.session.bulk_save_objects(tasks_to_insert)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"DB insert failed: {e}"}), 500

    return jsonify({"inserted": inserted, "skipped": skipped, "errors": errors}), 200


@api_bp.route("/tasks/export-csv", methods=["GET"])
def api_export_csv():
    q = request.args.get("q", default="", type=str).strip()

    query = MyTask.query
    if q:
        words = [w for w in q.split() if w]
        if words:
            conditions = [MyTask.content.ilike(f"%{w}%") for w in words]
            query = query.filter(or_(*conditions))

    tasks = query.order_by(MyTask.created.desc()).all()
    csv_data, filename = tasks_to_csv(tasks)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
