"""Discovery table (SPEC §18) — one row per submitted photograph."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class Discovery(Base):
    __tablename__ = "discoveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    challenge_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    image_path: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String(40), index=True)

    # "completed" is stored so the journal can show misses as well as wins.
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_feedback: Mapped[str] = mapped_column(Text, default="")
    ai_reasoning: Mapped[str] = mapped_column(Text, default="")
    interesting_detail: Mapped[str] = mapped_column(Text, default="")
    visual_description: Mapped[str] = mapped_column(Text, default="")
    tagline: Mapped[str] = mapped_column(String(80), default="")
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    challenge: Mapped[Challenge] = relationship(back_populates="discovery")  # noqa: F821
    user: Mapped[User] = relationship(back_populates="discoveries")  # noqa: F821

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "challenge_id": self.challenge_id,
            "image_path": self.image_path,
            # Always absolute-from-root. The journal and the submit response used
            # to disagree on the leading slash, which broke journal images.
            "image_url": f"/{self.image_path.lstrip('/')}",
            "title": self.title,
            "description": self.description,
            "score": self.score,
            "confidence": self.confidence,
            "category": self.category,
            "completed": self.completed,
            "ai_feedback": self.ai_feedback,
            "interesting_detail": self.interesting_detail,
            "visual_description": self.visual_description,
            "tagline": self.tagline,
            "points_awarded": self.points_awarded,
            "created_at": self.created_at.isoformat(),
        }
