from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import FocusTask


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Focus Stream",
    description="A lightweight flow-state task & pomodoro tracker built with FastAPI, SQLite, HTMX, and Tailwind CSS.",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")


def calculate_stats(db: Session):
    tasks = db.query(FocusTask).all()
    total = len(tasks)
    completed = sum(1 for t in tasks if t.is_completed)
    total_pomodoros = sum(t.completed_pomodoros for t in tasks)
    completion_rate = round((completed / total) * 100) if total > 0 else 0
    return {
        "total": total,
        "completed": completed,
        "total_pomodoros": total_pomodoros,
        "completion_rate": completion_rate,
    }


def query_tasks(db: Session, filter_mode: str = "all"):
    query = db.query(FocusTask)
    if filter_mode == "active":
        query = query.filter(FocusTask.is_completed == False)
    elif filter_mode == "completed":
        query = query.filter(FocusTask.is_completed == True)

    # Order: active first, then newest first
    return query.order_by(FocusTask.is_completed.asc(), FocusTask.id.desc()).all()


@app.get("/health")
def health_check():
    return {"status": "ok", "app": "Focus Stream"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    tasks = query_tasks(db, filter_mode="all")
    stats = calculate_stats(db)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "tasks": tasks,
            "stats": stats,
            "active_filter": "all",
        },
    )


@app.get("/tasks", response_class=HTMLResponse)
def list_tasks(
    request: Request,
    filter: str = "all",
    db: Session = Depends(get_db),
):
    tasks = query_tasks(db, filter_mode=filter)
    stats = calculate_stats(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/task_list.html",
        context={
            "tasks": tasks,
            "stats": stats,
        },
    )


@app.post("/tasks", response_class=HTMLResponse)
def create_task(
    request: Request,
    title: str = Form(...),
    category: str = Form("Deep Work"),
    pomodoros: int = Form(1),
    db: Session = Depends(get_db),
):
    cleaned_title = title.strip()
    if not cleaned_title:
        raise HTTPException(status_code=400, detail="Task title cannot be empty")

    new_task = FocusTask(
        title=cleaned_title,
        category=category,
        pomodoros=max(1, pomodoros),
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    tasks = query_tasks(db, filter_mode="all")
    stats = calculate_stats(db)

    return templates.TemplateResponse(
        request=request,
        name="partials/task_list.html",
        context={
            "tasks": tasks,
            "stats": stats,
        },
    )


@app.post("/tasks/{task_id}/toggle", response_class=HTMLResponse)
def toggle_task(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.query(FocusTask).filter(FocusTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.is_completed = not task.is_completed
    task.completed_at = datetime.now(timezone.utc) if task.is_completed else None
    db.commit()
    db.refresh(task)

    stats = calculate_stats(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/task_row.html",
        context={
            "task": task,
            "stats": stats,
        },
    )


@app.post("/tasks/{task_id}/pomodoro", response_class=HTMLResponse)
def log_pomodoro(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.query(FocusTask).filter(FocusTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.completed_pomodoros += 1
    db.commit()
    db.refresh(task)

    stats = calculate_stats(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/task_row.html",
        context={
            "task": task,
            "stats": stats,
        },
    )


@app.delete("/tasks/{task_id}", response_class=HTMLResponse)
def delete_task(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
):
    task = db.query(FocusTask).filter(FocusTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    stats = calculate_stats(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/task_delete.html",
        context={
            "stats": stats,
        },
    )
