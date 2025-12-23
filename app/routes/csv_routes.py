from flask import Blueprint, request, redirect, Response
from ..extensions import db
from ..models import MyTask
from ..services.csv_io import parse_tasks_csv, tasks_to_csv

csv_bp = Blueprint("csv", __name__)

@csv_bp.route("/import-csv", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return "No file part found", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    if not file.filename.lower().endswith(".csv"):
        return "Please upload a .csv file", 400

    tasks_to_insert, inserted, skipped, errors = parse_tasks_csv(file)

    if tasks_to_insert:
        try:
            db.session.bulk_save_objects(tasks_to_insert)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"DB insert failed: {e}", 500

    return redirect(f"/?imported={inserted}&skipped={skipped}&errors={errors}")


@csv_bp.route("/export-csv", methods=["GET"])
def export_csv():
    tasks = MyTask.query.order_by(MyTask.created.desc()).all()
    csv_data, filename = tasks_to_csv(tasks)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
