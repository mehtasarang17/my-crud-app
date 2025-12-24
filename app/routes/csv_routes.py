from flask import Blueprint, request, redirect, Response
from datetime import datetime
import io, csv

from ..extensions import db
from ..models import MyTask, Project
from ..services.csv_io import parse_tasks_csv, tasks_to_csv  # if you already have these

csv_bp = Blueprint("csv", __name__)

# ✅ IMPORT for a specific project
@csv_bp.route("/projects/<int:project_id>/import-csv", methods=["POST"])
def import_csv_ui(project_id: int):
    # ensure project exists
    Project.query.get_or_404(project_id)

    if "file" not in request.files:
        return "No file part found", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    if not file.filename.lower().endswith(".csv"):
        return "Please upload a .csv file", 400

    # parse CSV -> list[MyTask], inserted, skipped, errors
    tasks_to_insert, inserted, skipped, errors = parse_tasks_csv(file, project_id=project_id)

    if tasks_to_insert:
        try:
            db.session.bulk_save_objects(tasks_to_insert)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"DB insert failed: {e}", 500

    return redirect(f"/projects/{project_id}?imported={inserted}&skipped={skipped}&errors={errors}")


@csv_bp.route("/projects/<int:project_id>/export-csv", methods=["GET"])
def export_csv_ui(project_id: int):
    Project.query.get_or_404(project_id)

    q = request.args.get("q", "", type=str).strip()
    per_page = request.args.get("per_page", 5, type=int)
    sort = request.args.get("sort", "desc", type=str)

    # guardrails
    if per_page < 1:
        per_page = 5
    if per_page > 100:
        per_page = 100

    query = MyTask.query.filter(MyTask.project_id == project_id)

    # same search logic as UI
    if q:
        from sqlalchemy import or_
        words = [w for w in q.split() if w]
        if words:
            conditions = [MyTask.content.ilike(f"%{w}%") for w in words]
            query = query.filter(or_(*conditions))

    # same sort logic as UI
    if sort == "asc":
        query = query.order_by(MyTask.created.asc())
    else:
        query = query.order_by(MyTask.created.desc())

    # ✅ only first page
    pagination = query.paginate(page=1, per_page=per_page, error_out=False)
    tasks = pagination.items

    csv_data, filename = tasks_to_csv(tasks)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

