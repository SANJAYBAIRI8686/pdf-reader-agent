# Central models catalog.
# Imports Base and all models to ensure metadata registration before create_all() is run.

from app.database.base import Base
from app.models.user import User
from app.models.document import Document

__all__ = ["Base", "User", "Document"]
