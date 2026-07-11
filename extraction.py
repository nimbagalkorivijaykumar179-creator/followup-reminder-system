"""
Commitment Extraction Agent.

Takes raw unstructured text (meeting transcript, email, chat log) and uses
an LLM to extract structured follow-up commitments: owner, task, deadline,
and priority.
"""
import json
import os
from datetime import date

from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

EXTRACTION_SYSTEM_PROMPT = """You are a commitment-extraction engine. Given a
meeting transcript, email, or chat log, identify every follow-up commitment
someone made (things like "I'll send X by Friday" or "let me check with the
team next week").

Return ONLY a JSON array, no preamble, no markdown fences. Each item must have:
- "owner": the person who made the commitment (string)
- "task": a short description of what they committed to do (string)
- "deadline": an ISO date (YYYY-MM-DD) if a specific or clearly inferable date
  is mentioned, otherwise null
- "deadline_hint": the original vague phrase if deadline is null (e.g. "next week"),
  otherwise null
- "priority": "high", "medium", or "low" based on urgency/language used

If there are no commitments, return an empty array [].
Today's date is {today} — use it to resolve relative dates like "Friday" or "next week".
"""


def extract_commitments(text: str) -> list[dict]:
    """Call the LLM to extract structured commitments from raw text."""
    today = date.today().isoformat()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=EXTRACTION_SYSTEM_PROMPT.format(today=today),
        messages=[{"role": "user", "content": text}],
    )

    raw = response.content[0].text.strip()
    # Defensive cleanup in case the model wraps output in code fences
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        commitments = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return nothing rather than crash the pipeline;
        # in production, log this for review.
        commitments = []

    return commitments


import re
from datetime import timedelta

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

_COMMITMENT_PATTERNS = re.compile(
    r"\b(i'll|i will|let me|i'm going to|i am going to)\b", re.IGNORECASE
)

_URGENT_WORDS = ("urgent", "asap", "critical", "immediately")
_LOW_PRIORITY_WORDS = ("no rush", "whenever", "no hurry", "not urgent")


def _resolve_deadline(sentence: str, today: date) -> tuple[str | None, str | None]:
    """Best-effort resolution of simple deadline phrases to an ISO date."""
    lower = sentence.lower()

    if "tomorrow" in lower:
        return (today + timedelta(days=1)).isoformat(), None

    if "next week" in lower:
        return None, "next week"

    for i, day_name in enumerate(_WEEKDAYS):
        if day_name in lower:
            days_ahead = (i - today.weekday()) % 7
            days_ahead = days_ahead or 7  # "Friday" means the upcoming one, not today
            return (today + timedelta(days=days_ahead)).isoformat(), None

    return None, None


def _infer_priority(sentence: str) -> str:
    lower = sentence.lower()
    if any(word in lower for word in _URGENT_WORDS):
        return "high"
    if any(word in lower for word in _LOW_PRIORITY_WORDS):
        return "low"
    return "medium"


def _split_into_sentences(text: str) -> list[str]:
    """
    Split into sentences, tolerant of transcripts where a single sentence is
    word-wrapped across multiple lines (a blank line marks a new paragraph/turn).
    """
    chunks = []
    for paragraph in re.split(r"\n\s*\n", text):
        joined = " ".join(line.strip() for line in paragraph.split("\n") if line.strip())
        if not joined:
            continue
        chunks.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", joined) if s.strip())
    return chunks


def extract_commitments_mock(text: str) -> list[dict]:
    """
    Offline fallback for local dev/demo without an API key. No external calls,
    no cost — parses speaker labels, splits multi-sentence lines, and resolves
    simple deadline words (tomorrow / weekday names / "next week") into real
    dates. Good enough for a convincing demo; swap to extract_commitments()
    once ANTHROPIC_API_KEY has credits.
    """
    today = date.today()
    results = []
    current_owner = "Unknown"

    for sentence in _split_into_sentences(text):
        # Detect a "Name: ..." speaker label and update the current owner.
        speaker_match = re.match(r"^([A-Za-z][\w\s]{0,30}):\s*(.*)$", sentence)
        if speaker_match:
            current_owner = speaker_match.group(1).strip()
            sentence = speaker_match.group(2).strip()

        if not sentence:
            continue

        if _COMMITMENT_PATTERNS.search(sentence):
            deadline, deadline_hint = _resolve_deadline(sentence, today)
            results.append(
                {
                    "owner": current_owner,
                    "task": sentence,
                    "deadline": deadline,
                    "deadline_hint": deadline_hint,
                    "priority": _infer_priority(sentence),
                }
            )

    return results
