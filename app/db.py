"""Database setup and models for the Follow-up Reminder System."""
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./followups.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Commitment(Base):
    __tablename__ = "commitments"

    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(Text, nullable=False)
    owner = Column(String, nullable=False)
    task = Column(Text, nullable=False)
    deadline = Column(String, nullable=True)  # ISO date string, nullable if vague
    priority = Column(String, default="medium")  # low / medium / high
    status = Column(String, default="pending")  # pending / done / escalated
    reminder_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_reminded_at = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
