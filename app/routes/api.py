from flask import Blueprint, request, jsonify, Response
from flasgger import swag_from
from sqlalchemy import or_
from ..extensions import db
from ..models import MyTask
from ..services.search import apply_task_search
from ..services.csv_io import parse_tasks_csv, tasks_to_csv

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/tasks", methods=["GET"])
@swag_from({
    "tags": ["Tasks"],
    "parameters": [
        {"name": "q", "in": "query", "required": False, "type": "string"},
        {"name": "page", "in": "query", "required": False, "type": "integer", "default": 1},
        {"name": "per_page", "in": "query", "required": False, "type": "integer", "default": 5},
    ],
    "responses": {200: {"description": "Paginated list (optionally filtered by q)"}}
})
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
@swag_from({
    "tags": ["Tasks"],
    "parameters": [{
        "name": "body",
        "in": "body",
        "required": True,
        "schema": {
            "type": "object",
            "required": ["content"],
            "properties": {
                "content": {"type": "string"},
                "completed": {"type": "integer", "default": 0}
            }
        }
    }],
    "responses": {201: {"description": "Task created"}, 400: {"description": "Invalid payload"}}
})
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
@swag_from({
    "tags": ["Tasks"],
    "parameters": [{"name": "id", "in": "path", "required": True, "type": "integer"}],
    "responses": {200: {"description": "Get one task"}, 404: {"description": "Not found"}}
})
def get_task(id: int):
    task = MyTask.query.get_or_404(id)
    return jsonify(task.to_dict()), 200


@api_bp.route("/tasks/<int:id>", methods=["PUT"])
@swag_from({
    "tags": ["Tasks"],
    "parameters": [
        {"name": "id", "in": "path", "required": True, "type": "integer"},
        {"name": "body", "in": "body", "required": True,
         "schema": {"type": "object", "properties": {
             "content": {"type": "string"},
             "completed": {"type": "integer"}
         }}}
    ],
    "responses": {200: {"description": "Updated"}, 400: {"description": "Invalid payload"}, 404: {"description": "Not found"}}
})
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
@swag_from({
    "tags": ["Tasks"],
    "parameters": [{"name": "id", "in": "path", "required": True, "type": "integer"}],
    "responses": {204: {"description": "Deleted"}, 404: {"description": "Not found"}}
})
def delete_task(id: int):
    task = MyTask.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return "", 204

#Import .csv
@api_bp.route("/tasks/import-csv", methods=["POST"])
@swag_from({
    "tags": ["Tasks"],
    "consumes": ["multipart/form-data"],
    "parameters": [
        {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": True,
            "description": "CSV file. Supports header: content,completed OR single-column rows."
        }
    ],
    "responses": {
        200: {"description": "Import summary"},
        400: {"description": "Bad request"},
        500: {"description": "DB insert failed"}
    }
})
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

    return jsonify({
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors
    }), 200


#Export .csv
@api_bp.route("/tasks/export-csv", methods=["GET"])
@swag_from({
    "tags": ["Tasks"],
    "parameters": [
        {"name": "q", "in": "query", "required": False, "type": "string", "description": "Optional search filter"}
    ],
    "produces": ["text/csv"],
    "responses": {
        200: {"description": "CSV file download"}
    }
})
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

