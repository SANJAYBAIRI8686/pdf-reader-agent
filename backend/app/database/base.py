import re
from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    Automatically generates table names in snake_case format.
    """
    
    @declared_attr
    @classmethod
    def __tablename__(cls) -> str:
        # Convert CamelCase class name to snake_case table name
        name = cls.__name__
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
