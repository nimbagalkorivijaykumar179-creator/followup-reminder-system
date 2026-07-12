"""
Smart Follow-up Reminder System — FastAPI app.

Endpoints:
  POST /extract                    -> extract commitments from raw text, save to DB
  GET  /commitments                -> list commitments (optional ?status= filter)
  POST /commitments/{id}/complete  -> mark a commitment as done
  POST /scheduler/run              -> manually trigger the daily reminder check
"""
import os
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import init_db, get_db, Commitment
from app.extraction import extract_commitments, extract_commitments_mock
from app.scheduler import run_daily_check

app = FastAPI(title="Smart Follow-up Reminder System")

USE_MOCK = os.environ.get("ANTHROPIC_API_KEY") is None


@app.on_event("startup")
def on_startup():
    init_db()


class ExtractRequest(BaseModel):
    text: str


class CommitmentOut(BaseModel):
    id: int
    owner: str
    task: str
    deadline: Optional[str]
    priority: str
    status: str
    reminder_count: int

    class Config:
        from_attributes = True


@app.post("/extract", response_model=list[CommitmentOut])
def extract(req: ExtractRequest, db: Session = Depends(get_db)):
    """Extract commitments from raw text and persist them."""
    extractor = extract_commitments_mock if USE_MOCK else extract_commitments
    found = extractor(req.text)

    saved = []
    for item in found:
        commitment = Commitment(
            source_text=req.text,
            owner=item.get("owner", "Unknown"),
            task=item["task"],
            deadline=item.get("deadline"),
            priority=item.get("priority", "medium"),
        )
        db.add(commitment)
        db.flush()
        saved.append(commitment)

    db.commit()
    for c in saved:
        db.refresh(c)
    return saved


@app.get("/commitments", response_model=list[CommitmentOut])
def list_commitments(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Commitment)
    if status:
        query = query.filter(Commitment.status == status)
    return query.order_by(Commitment.created_at.desc()).all()


@app.post("/commitments/{commitment_id}/complete", response_model=CommitmentOut)
def complete_commitment(commitment_id: int, db: Session = Depends(get_db)):
    commitment = db.query(Commitment).filter(Commitment.id == commitment_id).first()
    if not commitment:
        raise HTTPException(status_code=404, detail="Commitment not found")
    commitment.status = "done"
    db.commit()
    db.refresh(commitment)
    return commitment


@app.post("/scheduler/run")
def trigger_scheduler():
    """Manually trigger the daily reminder check (normally run on a cron/loop)."""
    return run_daily_check()


@app.get("/")
def root():
    return {
        "message": "Smart Follow-up Reminder System is running.",
        "mode": "mock extraction (no ANTHROPIC_API_KEY set)" if USE_MOCK else "live LLM extraction",
    }
