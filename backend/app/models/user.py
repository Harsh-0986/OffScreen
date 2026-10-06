"""User table (SPEC §16, §18). Intentionally small — no social graph."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), default="Curious human")

    total_points: Mapped[int] = mapped_column(Integer, default=0)
    discoveries_count: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    completed_challenges: Mapped[int] = mapped_column(Integer, default=0)
    outdoor_minutes_estimate: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    challenges: Mapped[list[Challenge]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    discoveries: Mapped[list[Discovery]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[list[UserPreference]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )

    def to_public_dict(self) -> dict:
        """The shape returned by GET /api/profile."""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "total_points": self.total_points,
            "discoveries_count": self.discoveries_count,
            "current_streak": self.current_streak,
            "completed_challenges": self.completed_challenges,
            "outdoor_minutes_estimate": self.outdoor_minutes_estimate,
            "favorite_categories": {p.category: p.weight for p in self.preferences},
        }
