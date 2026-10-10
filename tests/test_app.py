import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

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
