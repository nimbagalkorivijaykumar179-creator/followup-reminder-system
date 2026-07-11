# Smart Follow-up Reminder System

An agentic AI system that extracts follow-up commitments from unstructured
text (meeting transcripts, emails, chat logs), tracks them, and sends
smart, non-annoying reminders — escalating when ignored.

See `PRD.md` for full product requirements and architecture.

## Quick start

```bash
pip install -r requirements.txt

# Optional: for real LLM-based extraction (otherwise falls back to a naive
# keyword-based mock extractor so the demo still runs without a key)
export ANTHROPIC_API_KEY=your_key_here

uvicorn app.main:app --reload
```

Then visit `http://localhost:8000/docs` for interactive API docs.

## Try it end-to-end

```bash
# 1. Extract commitments from the sample transcript
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$(cat mock_data/sample_transcript.txt)\"}"

# 2. List pending commitments
curl http://localhost:8000/commitments?status=pending

# 3. Mark one as done
curl -X POST http://localhost:8000/commitments/1/complete

# 4. Manually trigger the daily reminder check (normally cron/loop-driven)
curl -X POST http://localhost:8000/scheduler/run
```

## What's implemented (MVP)

- [x] Commitment extraction agent (LLM-based, with offline mock fallback)
- [x] Structured storage (SQLite via SQLAlchemy)
- [x] Scheduler agent — decides when to remind (lead day / due / overdue)
- [x] Escalation logic — priority bump after repeated ignored reminders
- [x] REST API for extraction, listing, completion, and manual scheduler trigger

## Next steps (good tasks to hand to an Antigravity agent one at a time)

1. "Add a Slack webhook notifier in `app/scheduler.py`'s `notify()` function,
   replacing the print statement, using an env var `SLACK_WEBHOOK_URL`."
2. "Add a background loop using the `schedule` library that calls
   `run_daily_check()` once every 24 hours when the app starts."
3. "Add a `Monitoring Agent` that re-checks the original source text (or a
   linked follow-up email thread) to see if a commitment looks resolved
   before firing a reminder."
4. "Build a simple React dashboard that lists commitments grouped by status,
   calling the existing `/commitments` endpoint."
5. "Write pytest tests for `extraction.py` and `scheduler.py`, mocking the
   Anthropic client."
6. Stretch: tie this into the Meeting Scheduler project — auto-feed meeting
   transcripts into `/extract` when a meeting ends.

## Project structure

```
followup-reminder-system/
├── PRD.md
├── README.md
├── requirements.txt
├── mock_data/
│   └── sample_transcript.txt
└── app/
    ├── main.py          # FastAPI app + endpoints
    ├── db.py             # SQLAlchemy models
    ├── extraction.py      # Commitment Extraction Agent (LLM)
    └── scheduler.py        # Scheduler / Notifier / Escalation Agent
```
