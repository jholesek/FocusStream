# Focus Stream ⚡

A lightweight, flow-state task tracker and focus timer built with **FastAPI**, **SQLAlchemy (SQLite)**, **HTMX**, and **Tailwind CSS (via CDN)**.

---

## 🚀 Features

- **Interactive Pomodoro & Focus Timer**: 25m focus blocks, 5m short breaks, 15m long breaks with audio notifications, progress bar, and HTMX server synchronization (`POST /timer/start`).
- **Focus Session Tracker**:
  - Record completed focus sessions with task description, duration, and energy ratings (`POST /sessions`).
  - View today's focus session log and aggregate daily metrics (`GET /sessions/today`).
  - `FocusSession` model tracking task name, duration in minutes, completion timestamps, and energy level.
- **Dynamic HTMX Task Management**:
  - Add tasks to the stream without page reload.
  - Category tags (Deep Work, Coding, Learning, Writing, Admin).
  - Target vs. completed focus session counters (`completed / target ⚡`).
  - Toggle completion status with reactive strike-through styling.
  - Delete tasks with confirmation and smooth DOM removal.
  - Filter stream by **All**, **Active**, and **Completed**.
- **Real-Time Out-of-Band (OOB) Metrics**: Total stream items, completed tasks, focus blocks logged, and completion percentage update automatically via HTMX out-of-band swaps.
- **SQLite Database**: Persisted locally via SQLAlchemy with automatic table migrations on startup.
- **Zero Build Step Frontend**: Powered by Tailwind CSS CDN and HTMX CDN.

---

## 🛠️ Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy 2.0](https://www.sqlalchemy.org/), [Uvicorn](https://www.uvicorn.org/)
- **Templates**: [Jinja2](https://jinja.palletsprojects.com/)
- **Frontend Interactivity**: [HTMX](https://htmx.org/) (CDN)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) (CDN)
- **Database**: SQLite (default `focus_stream.db`)

---

## 📦 Project Structure

```text
FocusStream/
├── app/
│   ├── __init__.py
│   ├── database.py       # SQLAlchemy engine & session management
│   ├── models.py         # FocusTask & FocusSession SQLAlchemy models
│   ├── main.py           # FastAPI routes & HTMX partial handlers
│   ├── static/
│   │   └── js/
│   │       └── timer.js  # Focus session timer with audio chimes
│   └── templates/
│       ├── base.html     # HTML skeleton with Tailwind & HTMX CDNs
│       ├── index.html    # Main dashboard view
│       └── partials/
│           ├── stats.html          # Real-time metrics card
│           ├── task_row.html       # Single task item row
│           ├── task_list.html      # Task stream list & empty state
│           ├── task_delete.html    # Out-of-band delete response
│           ├── timer_status.html   # Active timer indicator & quick logger
│           ├── session_row.html    # Single completed session item row
│           └── session_list.html   # Today's focus sessions log
├── tests/
│   ├── __init__.py
│   └── test_app.py       # Pytest test suite covering endpoints & HTMX flows
├── requirements.txt      # Project dependencies
├── .gitignore            # Python, SQLite & OS ignore rules
└── README.md
```

---

## ⚡ Quickstart

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/jholesek/FocusStream.git
cd FocusStream

python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🧪 Running Tests

To run the automated test suite:

```bash
pip install pytest httpx
pytest
```

---

## 📄 License

MIT
