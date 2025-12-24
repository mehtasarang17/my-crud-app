from datetime import datetime
from .extensions import db

class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship(
        "MyTask",
        backref="project",
        cascade="all, delete-orphan",
        lazy=True
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created": self.created.isoformat() if self.created else None
        }

class MyTask(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Integer, default=0)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "completed": int(self.completed),
            "created": self.created.isoformat() if self.created else None,
            "project_id": self.project_id,
        }
