from datetime import datetime, timezone, timedelta
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import FocusSession

from sqlalchemy.pool import StaticPool

# Use a test SQLite database in memory with StaticPool to share connection
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Focus Stream"}


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Focus Stream" in response.text
    assert "Tailwind CSS" in response.text
    assert "htmx.org" in response.text


def test_create_and_query_tasks(client):
    # Add a task
    response = client.post(
        "/tasks",
        data={"title": "Write documentation", "category": "Writing", "pomodoros": 2},
    )
    assert response.status_code == 200
    assert "Write documentation" in response.text
    assert "Writing" in response.text

    # List tasks
    list_resp = client.get("/tasks")
    assert list_resp.status_code == 200
    assert "Write documentation" in list_resp.text


def test_toggle_task(client):
    create_resp = client.post(
        "/tasks",
        data={"title": "Refactor codebase", "category": "Coding", "pomodoros": 3},
    )
    assert create_resp.status_code == 200

    # Toggle task 1
    toggle_resp = client.post("/tasks/1/toggle")
    assert toggle_resp.status_code == 200
    assert "line-through" in toggle_resp.text

    # Toggle back
    untoggle_resp = client.post("/tasks/1/toggle")
    assert untoggle_resp.status_code == 200
    assert "line-through" not in untoggle_resp.text


def test_log_pomodoro(client):
    client.post(
        "/tasks",
        data={"title": "Deep study session", "category": "Learning", "pomodoros": 4},
    )

    pomodoro_resp = client.post("/tasks/1/pomodoro")
    assert pomodoro_resp.status_code == 200
    assert "1/4" in pomodoro_resp.text


def test_delete_task(client):
    client.post(
        "/tasks",
        data={"title": "To be removed", "category": "Admin", "pomodoros": 1},
    )

    del_resp = client.delete("/tasks/1")
    assert del_resp.status_code == 200
    assert "stats-container" in del_resp.text

    # Confirm it's no longer in the list
    list_resp = client.get("/tasks")
    assert "To be removed" not in list_resp.text


def test_filter_tasks(client):
    client.post("/tasks", data={"title": "Task 1", "category": "Coding", "pomodoros": 1})
    client.post("/tasks", data={"title": "Task 2", "category": "Coding", "pomodoros": 1})
    client.post("/tasks/1/toggle")

    # Filter active
    active_resp = client.get("/tasks?filter=active")
    assert active_resp.status_code == 200
    assert "Task 2" in active_resp.text
    assert "Task 1" not in active_resp.text

    # Filter completed
    completed_resp = client.get("/tasks?filter=completed")
    assert completed_resp.status_code == 200
    assert "Task 1" in completed_resp.text
    assert "Task 2" not in completed_resp.text


def test_focus_session_model():
    session = FocusSession(
        task_name="Architectural Review",
        duration_minutes=45,
        energy_rating=5,
    )
    assert session.task_name == "Architectural Review"
    assert session.duration_minutes == 45
    assert session.energy_rating == 5
    d = session.to_dict()
    assert d["task_name"] == "Architectural Review"
    assert d["duration_minutes"] == 45
    assert d["energy_rating"] == 5


def test_start_timer_endpoint(client):
    # Form data
    resp = client.post(
        "/timer/start",
        data={"task_name": "API Refactor", "duration_minutes": 50},
    )
    assert resp.status_code == 200
    assert "API Refactor" in resp.text
    assert "50" in resp.text
    assert "Timer active" in resp.text

    # Default values
    resp_default = client.post("/timer/start")
    assert resp_default.status_code == 200
    assert "Focus Session" in resp_default.text
    assert "25" in resp_default.text

    # Alias /sessions/start
    resp_alias = client.post("/sessions/start", data={"task_name": "Alias Test", "duration_minutes": 20})
    assert resp_alias.status_code == 200
    assert "Alias Test" in resp_alias.text


def test_record_completed_session(client):
    resp = client.post(
        "/sessions",
        data={
            "task_name": "Writing Documentation",
            "duration_minutes": 35,
            "energy_rating": 4,
        },
    )
    assert resp.status_code == 200
    assert "Writing Documentation" in resp.text
    assert "35m" in resp.text
    assert "4" in resp.text

    # Verify session is persisted in db
    db = TestingSessionLocal()
    saved = db.query(FocusSession).filter(FocusSession.task_name == "Writing Documentation").first()
    assert saved is not None
    assert saved.duration_minutes == 35
    assert saved.energy_rating == 4
    assert saved.completed_at is not None
    db.close()


def test_fetch_today_sessions_log(client):
    # Initial empty state
    empty_resp = client.get("/sessions/today")
    assert empty_resp.status_code == 200
    assert "No focus sessions logged today" in empty_resp.text

    # Add a session today
    client.post(
        "/sessions",
        data={"task_name": "Today Sprint", "duration_minutes": 25, "energy_rating": 5},
    )

    # Add a session from yesterday directly into db
    db = TestingSessionLocal()
    yesterday_session = FocusSession(
        task_name="Yesterday Work",
        duration_minutes=60,
        energy_rating=3,
        completed_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(yesterday_session)
    db.commit()
    db.close()

    # Query today's sessions
    today_resp = client.get("/sessions/today")
    assert today_resp.status_code == 200
    assert "Today Sprint" in today_resp.text
    assert "Yesterday Work" not in today_resp.text
    assert "5" in today_resp.text

    # Verify /sessions alias
    alias_resp = client.get("/sessions")
    assert alias_resp.status_code == 200
    assert "Today Sprint" in alias_resp.text


def test_index_page_with_sessions(client):
    client.post(
        "/sessions",
        data={"task_name": "Full Stack Flow", "duration_minutes": 50, "energy_rating": 4},
    )
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Full Stack Flow" in resp.text
    assert "Today's Focus Log" in resp.text


def test_json_endpoints(client):
    # Test JSON timer start
    start_resp = client.post(
        "/timer/start",
        json={"task_name": "JSON Flow", "duration_minutes": 25},
    )
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "started"
    assert start_data["task_name"] == "JSON Flow"

    # Test JSON session record
    rec_resp = client.post(
        "/sessions",
        json={"task_name": "API Documentation", "duration_minutes": 30, "energy_rating": 4},
    )
    assert rec_resp.status_code == 201
    rec_data = rec_resp.json()
    assert rec_data["task_name"] == "API Documentation"
    assert rec_data["duration_minutes"] == 30
    assert rec_data["energy_rating"] == 4

    # Test JSON fetch today sessions
    log_resp = client.get("/sessions/today", headers={"accept": "application/json"})
    assert log_resp.status_code == 200
    log_data = log_resp.json()
    assert any(s["task_name"] == "API Documentation" for s in log_data)


