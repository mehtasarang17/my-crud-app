from sqlalchemy import or_
from ..models import MyTask

def apply_task_search(query, q: str):
    q = (q or "").strip()
    if not q:
        return query

    words = [w for w in q.split() if w]
    if not words:
        return query

    conditions = [MyTask.content.ilike(f"%{w}%") for w in words]
    return query.filter(or_(*conditions))
