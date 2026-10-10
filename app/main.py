from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import FocusSession, FocusTask, utc_now


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


async def get_payload(request: Request) -> dict:
    data = {}
    data.update(dict(request.query_params))
    try:
        form = await request.form()
        data.update(dict(form))
    except Exception:
        pass
    try:
        json_data = await request.json()
        if isinstance(json_data, dict):
            data.update(json_data)
    except Exception:
        pass
    return data


def query_sessions(db: Session, today_only: bool = True):
    query = db.query(FocusSession)
    if today_only:
        now = datetime.now(timezone.utc)
        start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
        query = query.filter(FocusSession.completed_at >= start_of_today)
    return query.order_by(FocusSession.completed_at.desc(), FocusSession.id.desc()).all()


def calculate_session_stats(sessions):
    total = len(sessions)
    total_minutes = sum(s.duration_minutes for s in sessions)
    rated_sessions = [s for s in sessions if s.energy_rating is not None]
    avg_energy = (
        round(sum(s.energy_rating for s in rated_sessions) / len(rated_sessions), 1)
        if rated_sessions
        else 0
    )
    return {
        "total": total,
        "total_minutes": total_minutes,
        "avg_energy": avg_energy,
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "app": "Focus Stream"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    tasks = query_tasks(db, filter_mode="all")
    stats = calculate_stats(db)
    sessions = query_sessions(db, today_only=True)
    session_stats = calculate_session_stats(sessions)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "tasks": tasks,
            "stats": stats,
            "sessions": sessions,
            "session_stats": session_stats,
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


# =====================================================================
# Focus Session & Timer HTMX Endpoints
# =====================================================================

@app.post("/timer/start", response_class=HTMLResponse)
@app.post("/sessions/start", response_class=HTMLResponse)
@app.get("/timer/start", response_class=HTMLResponse)
async def start_timer(
    request: Request,
    task_name: Optional[str] = Form(None),
    duration_minutes: Optional[int] = Form(None),
):
    payload = await get_payload(request)
    name = (
        payload.get("task_name")
        or payload.get("title")
        or payload.get("task")
        or task_name
        or "Focus Session"
    )
    if isinstance(name, str):
        name = name.strip() or "Focus Session"

    duration = (
        payload.get("duration_minutes")
        or payload.get("duration")
        or duration_minutes
        or 25
    )
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        duration = 25

    if (
        request.headers.get("accept") == "application/json"
        or (request.headers.get("content-type") == "application/json" and not request.headers.get("hx-request"))
    ):
        return JSONResponse(
            content={
                "status": "started",
                "task_name": name,
                "duration_minutes": duration,
                "started_at": utc_now().isoformat(),
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/timer_status.html",
        context={
            "task_name": name,
            "duration_minutes": duration,
            "started_at": utc_now(),
        },
    )


@app.post("/sessions", response_class=HTMLResponse)
@app.post("/sessions/complete", response_class=HTMLResponse)
@app.post("/sessions/record", response_class=HTMLResponse)
@app.post("/timer/complete", response_class=HTMLResponse)
async def record_session(
    request: Request,
    task_name: Optional[str] = Form(None),
    duration_minutes: Optional[int] = Form(None),
    energy_rating: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    payload = await get_payload(request)
    name = (
        payload.get("task_name")
        or payload.get("title")
        or payload.get("task")
        or task_name
        or "Focus Session"
    )
    if isinstance(name, str):
        name = name.strip() or "Focus Session"

    duration = (
        payload.get("duration_minutes")
        or payload.get("duration")
        or duration_minutes
        or 25
    )
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        duration = 25

    energy = payload.get("energy_rating") or payload.get("rating") or energy_rating
    if energy is not None:
        try:
            energy = int(energy)
        except (ValueError, TypeError):
            energy = 3
    else:
        energy = 3

    completed_str = payload.get("completed_at")
    completed_dt = utc_now()
    if completed_str:
        if isinstance(completed_str, datetime):
            completed_dt = completed_str
        elif isinstance(completed_str, str):
            try:
                completed_dt = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
            except Exception:
                completed_dt = utc_now()

    new_session = FocusSession(
        task_name=name,
        duration_minutes=max(1, duration),
        energy_rating=energy,
        completed_at=completed_dt,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    if (
        request.headers.get("accept") == "application/json"
        or (request.headers.get("content-type") == "application/json" and not request.headers.get("hx-request"))
    ):
        return JSONResponse(
            content=jsonable_encoder(new_session.to_dict()),
            status_code=status.HTTP_201_CREATED,
        )

    sessions = query_sessions(db, today_only=True)
    session_stats = calculate_session_stats(sessions)
    return templates.TemplateResponse(
        request=request,
        name="partials/session_list.html",
        context={
            "sessions": sessions,
            "session_stats": session_stats,
            "new_session": new_session,
        },
    )


@app.get("/sessions/today", response_class=HTMLResponse)
@app.get("/sessions", response_class=HTMLResponse)
@app.get("/sessions/log", response_class=HTMLResponse)
@app.get("/sessions/today/log", response_class=HTMLResponse)
def get_today_sessions(
    request: Request,
    filter: str = "today",
    all: bool = False,
    db: Session = Depends(get_db),
):
    today_only = not (all or filter == "all")
    sessions = query_sessions(db, today_only=today_only)
    session_stats = calculate_session_stats(sessions)

    if (
        request.headers.get("accept") == "application/json"
        and not request.headers.get("hx-request")
    ):
        return JSONResponse(content=jsonable_encoder([s.to_dict() for s in sessions]))

    return templates.TemplateResponse(
        request=request,
        name="partials/session_list.html",
        context={
            "sessions": sessions,
            "session_stats": session_stats,
        },
    )

