from flask import Flask, render_template, request, redirect, jsonify
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flasgger import Swagger, swag_from

app = Flask(__name__)

Scss(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SWAGGER"] = {
    "title": "Task API",
    "uiversion": 3
}

swagger = Swagger(app)

db = SQLAlchemy(app)

class MyTask(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Integer, default=0)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return{
            "id": self.id,
            "content": self.content,
            "completed": int(self.completed),
            "created": self.created.isoformat() if self.created else None
        }
    
with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        current_task = request.form['content']
        new_task = MyTask(content=current_task)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return f"Error:{e}"
    else:
        tasks = MyTask.query.order_by(MyTask.created).all()
        return render_template("index.html",tasks=tasks)
            
@app.route("/delete/<int:id>")
def delete(id:int):
    delete_tasks = MyTask.query.get_or_404(id)
    try:
        db.session.delete(delete_tasks)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        return f"Error{e}"
    
@app.route("/update/<int:id>", methods=["GET","POST"])
def update(id:int):
    update_task = MyTask.query.get_or_404(id)
    if request.method == "POST":
        update_task.content = request.form['content']
        try:
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return f"Error{e}"
    else:
        return render_template("edit.html", update_task=update_task)
    
@app.route("/api/tasks", methods=["GET"])
@swag_from({
    "tags": ["Tasks"],
    "responses":{
        200:{
            "description": "List all tasks",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "content": {"type": "string"},
                        "completed": {"type": "integer"},
                        "created": {"type": "string"}
                    }
                }
            }
        }
    }
})

def api_list_tasks():
    tasks = MyTask.query.order_by(MyTask.created).all()
    return jsonify([t.to_dict() for t in tasks]), 200

@app.route("/api/tasks", methods=["POST"])
@swag_from({
    "tags": ["Tasks"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema":{
                "type": "object",
                "required": ["content"],
                "properties": {
                    "content": {"type":"string"},
                    "completed": {"type": "integer", "default": 0}
                }
            }
        }
    ],
    "responses":{
        201: {"description": "Task created"},
        400: {"description": "Invalid payload"}
    }
})

def api_create_task():
    data = request.get_json(silent=True) or {}
    content = data.get("content")
    if not content: 
        return jsonify({"error": "content is required"}),400
    
    completed = int(data.get("completed", 0))
    task = MyTask(content=content, completed=completed)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201

@app.route("/api/tasks/<int:id>", methods=["GET"])
@swag_from({
    "tags": ["Tasks"],
    "parameters": [{"name": "id", "in": "path", "required": True, "type": "integer"}],
    "responses": {
        200: {"description": "Get one task"},
        404: {"description": "Not found"}
    }
})
def api_get_task(id: int):
    task = MyTask.query.get_or_404(id)
    return jsonify(task.to_dict()), 200

@app.route("/api/tasks/<int:id>", methods=["PUT"])
@swag_from({
    "tags": ["Tasks"],
    "parameters": [
        {"name": "id", "in": "path", "required": True, "type": "integer"},
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "completed": {"type": "integer"}
                }
            }
        }
    ],
    "responses": {
        200: {"description": "Updated"},
        400: {"description": "Invalid payload"},
        404: {"description": "Not found"}
    }
})
def api_update_task(id: int):
    task = MyTask.query.get_or_404(id)
    data = request.get_json(silent=True) or {}

    if "content" in data:
        if not data["content"]:
            return jsonify({"error": "content cannot be empty"}), 400
        task.content = data["content"]

    if "completed" in data:
        task.completed = int(data["completed"])

    db.session.commit()
    return jsonify(task.to_dict()), 200


@app.route("/api/tasks/<int:id>", methods=["DELETE"])
@swag_from({
    "tags": ["Tasks"],
    "parameters": [{"name": "id", "in": "path", "required": True, "type": "integer"}],
    "responses": {
        204: {"description": "Deleted"},
        404: {"description": "Not found"}
    }
})
def api_delete_task(id: int):
    task = MyTask.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return "", 204
    
    

if __name__ == "__main__":
    app.run(debug=True)

