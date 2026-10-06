import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from app.database.base import Base

def generate_uuid() -> str:
    """Generate deterministic or random string UUID."""
    return str(uuid.uuid4())

class TimestampMixin:
    """Standard created_at and updated_at timestamps in UTC."""
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
