from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class FocusTask(Base):
    __tablename__ = "focus_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(50), default="Deep Work", nullable=False)
    pomodoros = Column(Integer, default=1, nullable=False)
    completed_pomodoros = Column(Integer, default=0, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "pomodoros": self.pomodoros,
            "completed_pomodoros": self.completed_pomodoros,
            "is_completed": self.is_completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
