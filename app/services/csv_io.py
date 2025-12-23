import csv
import io
from datetime import datetime
from ..models import MyTask

def parse_tasks_csv(file_storage):
    """
    Accepts Werkzeug FileStorage, returns (tasks_to_insert, inserted_count, skipped, errors)
    """
    stream = io.StringIO(file_storage.stream.read().decode("utf-8-sig"), newline=None)
    reader = csv.reader(stream)
    rows = list(reader)

    if not rows:
        return [], 0, 0, 0

    skipped = 0
    errors = 0
    tasks_to_insert = []

    first_row = [c.strip().lower() for c in rows[0]]
    has_header = "content" in first_row or "task" in first_row

    if has_header:
        stream.seek(0)
        dict_reader = csv.DictReader(stream)
        for r in dict_reader:
            try:
                content = (r.get("content") or r.get("task") or "").strip()
                if not content:
                    skipped += 1
                    continue

                completed_raw = (r.get("completed") or "0").strip().lower()
                completed = 1 if completed_raw in ("1", "true", "yes", "y") else 0
                tasks_to_insert.append(MyTask(content=content, completed=completed))
            except Exception:
                errors += 1
    else:
        for r in rows:
            try:
                if not r:
                    skipped += 1
                    continue
                content = (r[0] or "").strip()
                if not content:
                    skipped += 1
                    continue
                tasks_to_insert.append(MyTask(content=content))
            except Exception:
                errors += 1

    return tasks_to_insert, len(tasks_to_insert), skipped, errors


def tasks_to_csv(tasks):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "content", "completed", "created"])

    for t in tasks:
        writer.writerow([
            t.id,
            t.content,
            int(t.completed),
            t.created.isoformat() if t.created else ""
        ])

    return output.getvalue(), f"tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
