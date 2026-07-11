# Product Requirements Document
## Smart Follow-up Reminder System (Agentic AI)

**Author:** [Your Name], GenAI/Agentic AI Intern
**Status:** Draft v1

---

## 1. Problem Statement

After meetings, emails, and conversations, people make informal commitments —
"I'll send that by Friday," "let me circle back next week" — that are rarely
tracked systematically. Existing reminder apps require manual entry. This
project builds an agent that **automatically extracts commitments from
unstructured text** (meeting transcripts, emails, chat logs), tracks them,
and **proactively reminds the right person at the right time**, while
avoiding unnecessary nagging when a task is already done.

## 2. Goals

- Automatically detect follow-up commitments from raw text (no manual entry)
- Assign owner, task description, deadline, and priority to each commitment
- Schedule reminders intelligently (not just "at the deadline")
- Detect if a commitment appears already resolved before reminding
- Escalate when a reminder is repeatedly ignored
- Demonstrate autonomous, multi-step agent behavior (not a single LLM call)

## 3. Non-Goals (v1)

- Real Gmail/Slack OAuth integration (mocked for demo; real integration is a stretch goal)
- Multi-user auth/permissions system
- Mobile app / native notifications (webhook + console log is sufficient for MVP)

## 4. User Stories

| As a... | I want... | So that... |
|---|---|---|
| Meeting attendee | commitments I make in a meeting to be captured automatically | I don't have to manually write down every action item |
| Manager | overdue commitments from my team surfaced to me | nothing falls through the cracks |
| Individual user | reminders only when something is actually still pending | I'm not nagged about things I already did |

## 5. System Architecture

```
Raw text (transcript/email)
        │
        ▼
┌─────────────────────────┐
│ Commitment Extraction    │  LLM-based: pulls {owner, task, deadline, priority}
│ Agent                    │
└───────────┬──────────────┘
            ▼
┌─────────────────────────┐
│ Storage (SQLite)         │  commitments table: status = pending/done/escalated
└───────────┬──────────────┘
            ▼
┌─────────────────────────┐
│ Scheduler Agent           │  runs periodically (cron/loop), decides WHEN to nudge
│ (daily check)             │  e.g. 1 day before deadline, day-of, overdue
└───────────┬──────────────┘
            ▼
┌─────────────────────────┐
│ Monitoring Agent          │  (v2) checks if task already resolved before firing
└───────────┬──────────────┘
            ▼
┌─────────────────────────┐
│ Notifier Agent             │  sends reminder (console/Slack webhook/email)
└───────────┬──────────────┘
            ▼
┌─────────────────────────┐
│ Escalation logic           │  if ignored N times → raise priority / notify manager
└─────────────────────────┘
```

## 6. Core Data Model

```
Commitment
- id
- source_text (original sentence/snippet)
- owner (person responsible)
- task (what needs to be done)
- deadline (parsed date, nullable if vague — "soon", "next week")
- priority (low/medium/high — inferred by LLM)
- status (pending/done/escalated)
- reminder_count
- created_at
- last_reminded_at
```

## 7. MVP Scope (what "done" looks like for the internship demo)

1. `/extract` endpoint: POST a transcript/email → returns extracted commitments, saved to DB
2. `/commitments` endpoint: list all commitments with status/filtering
3. `/commitments/{id}/complete` endpoint: mark done
4. Scheduler loop: checks daily, prints/sends reminders for due & overdue items
5. Basic escalation: after 2 ignored reminders, priority bumped + flagged
6. Simple demo script with a sample transcript showing the full pipeline running end-to-end

## 8. Stretch Goals

- Real Slack webhook notifications
- Gmail integration for real email scanning
- Simple React dashboard showing pending/overdue follow-ups
- "Smart timing" — remind right after a related calendar event instead of a fixed offset
- Tie into the Meeting Scheduler project: meeting ends → transcript auto-fed into extraction

## 9. Tech Stack

- **Backend:** Python, FastAPI
- **LLM:** Claude or Gemini API (commitment extraction + priority inference)
- **DB:** SQLite (via SQLAlchemy) — easy to swap for Postgres later
- **Scheduler:** simple loop / `schedule` library (cron-like, no need for Celery at MVP scale)
- **Notification:** console output + optional Slack webhook

## 10. Success Metrics (for demo/eval)

- % of commitments correctly extracted from a sample transcript set (precision/recall vs. hand-labeled)
- Reminder fires within the correct time window
- No reminders fired for already-completed items (false positive rate)
