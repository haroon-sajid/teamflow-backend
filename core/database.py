from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os

# Use env DATABASE_URL with fallback to local sqlite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./teamflow.db")

# create engine that will be shared by the app
engine = create_engine(DATABASE_URL, echo=False)

def create_db_and_tables() -> None:
    """
    Create all DB tables from SQLModel metadata.
    Call this at startup.
    """
    SQLModel.metadata.create_all(engine)

# Dependency to get DB session for FastAPI route dependencies
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
