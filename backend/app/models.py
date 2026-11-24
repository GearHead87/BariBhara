"""Imports every ORM model so `Base.metadata` knows all tables (used by Alembic)."""

from app.core.database import Base
from app.modules.users.models import Role, User

__all__ = ["Base", "Role", "User"]
