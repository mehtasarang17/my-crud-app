from flask import Blueprint, request, jsonify, Response
from sqlalchemy import or_

from ..extensions import db
from ..models import Project, MyTask
from ..services.search import apply_task_search
from ..services.csv_io import parse_tasks_csv, tasks_to_csv

api_bp = Blueprint("api", __name__, url_prefix="/api")


# Projects CRUD (Dashboard API)

@api_bp.route("/projects", methods=["GET"])
def list_projects():
    projects = Project.query.order_by(Project.created.desc()).all()
    return jsonify([p.to_dict() for p in projects]), 200


@api_bp.route("/projects", methods=["POST"])
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    project = Project(name=name)
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@api_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    return jsonify(project.to_dict()), 200


@api_bp.route("/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name cannot be empty"}), 400

    project.name = name
    db.session.commit()
    return jsonify(project.to_dict()), 200


@api_bp.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id: int):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return "", 204


# Tasks CRUD (Project-scoped)

@api_bp.route("/projects/<int:project_id>/tasks", methods=["GET"])
def list_tasks(project_id: int):
    Project.query.get_or_404(project_id)

    q = request.args.get("q", "", type=str).strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 5, type=int)
    sort = request.args.get("sort", "desc", type=str)

    # guardrails
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 5
    if per_page > 100:
        per_page = 100

    query = MyTask.query.filter(MyTask.project_id == project_id)

    # your existing search helper (optional)
    query = apply_task_search(query, q)

    # sorting
    if sort == "asc":
        query = query.order_by(MyTask.created.asc())
    else:
        query = query.order_by(MyTask.created.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "project_id": project_id,
        "q": q,
        "sort": sort,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "items": [t.to_dict() for t in pagination.items]
    }), 200


@api_bp.route("/projects/<int:project_id>/tasks", methods=["POST"])
def create_task(project_id: int):
    Project.query.get_or_404(project_id)

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400

    completed = int(data.get("completed", 0))
    task = MyTask(content=content, completed=completed, project_id=project_id)

    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@api_bp.route("/projects/<int:project_id>/tasks/<int:task_id>", methods=["GET"])
def get_task(project_id: int, task_id: int):
    task = MyTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    return jsonify(task.to_dict()), 200


@api_bp.route("/projects/<int:project_id>/tasks/<int:task_id>", methods=["PUT"])
def update_task(project_id: int, task_id: int):
    task = MyTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    data = request.get_json(silent=True) or {}

    if "content" in data:
        content = (data.get("content") or "").strip()
        if not content:
            return jsonify({"error": "content cannot be empty"}), 400
        task.content = content

    if "completed" in data:
        task.completed = int(data.get("completed"))

    db.session.commit()
    return jsonify(task.to_dict()), 200


@api_bp.route("/projects/<int:project_id>/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(project_id: int, task_id: int):
    task = MyTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return "", 204


# CSV (Project-scoped)

@api_bp.route("/projects/<int:project_id>/tasks/import-csv", methods=["POST"])
def import_csv(project_id: int):
    Project.query.get_or_404(project_id)

    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "no file selected"}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file"}), 400

    tasks_to_insert, inserted, skipped, errors = parse_tasks_csv(file, project_id=project_id)

    if tasks_to_insert:
        try:
            db.session.bulk_save_objects(tasks_to_insert)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"DB insert failed: {e}"}), 500

    return jsonify({
        "project_id": project_id,
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors
    }), 200


@api_bp.route("/projects/<int:project_id>/tasks/export-csv", methods=["GET"])
def export_csv(project_id: int):
    Project.query.get_or_404(project_id)

    # export only first page (same as UI expectation)
    q = request.args.get("q", "", type=str).strip()
    per_page = request.args.get("per_page", 5, type=int)
    sort = request.args.get("sort", "desc", type=str)

    if per_page < 1:
        per_page = 5
    if per_page > 100:
        per_page = 100

    query = MyTask.query.filter(MyTask.project_id == project_id)
    query = apply_task_search(query, q)

    if sort == "asc":
        query = query.order_by(MyTask.created.asc())
    else:
        query = query.order_by(MyTask.created.desc())

    pagination = query.paginate(page=1, per_page=per_page, error_out=False)
    tasks = pagination.items

    csv_data, filename = tasks_to_csv(tasks)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
