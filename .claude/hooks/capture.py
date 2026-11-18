#!/usr/bin/env python3
"""8x agent capture: append each prompt and its final response to .agent-logs/.

Runs from .claude/settings.json on UserPromptSubmit and Stop. Stdlib only.
Never blocks the session: always exits 0, errors go to .agent-logs/capture-errors.log.
"""

import json
import os
import re
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # non-POSIX: run without the lock
    fcntl = None

AUTHOR = "Azadak12"
PROJECT = "fanthom"
TOOL = "claude-code"

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = Path(os.environ.get("CAPTURE_LOG_DIR") or ROOT / ".agent-logs")
FIELDS = [
    "session_id", "date", "author", "model", "tool", "project",
    "total_exchanges", "first_prompt_time", "last_prompt_time",
]
NO_TEXT = "(no text content in the final message)"


def utc_now():
    dt = datetime.now(timezone.utc)
    return dt, dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def transcript_entries(path):
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if isinstance(e, dict) and not e.get("isSidechain"):
                    yield e
    except (OSError, TypeError):
        return


def last_model(path):
    model = None
    for e in transcript_entries(path):
        if e.get("type") == "assistant":
            m = (e.get("message") or {}).get("model")
            if m and m != "<synthetic>":
                model = m
    return model


def final_text_from_transcript(path):
    """Text blocks of the assistant entries after the last user entry."""
    parts = []
    for e in reversed(list(transcript_entries(path))):
        if e.get("type") == "user":
            break
        if e.get("type") == "assistant":
            content = (e.get("message") or {}).get("content")
            if isinstance(content, list):
                texts = [b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text"]
                if any(texts):
                    parts.insert(0, "\n".join(texts))
    return "\n\n".join(parts)


def parse(text):
    end = text.index("\n---\n", 3)
    front = {}
    for line in text[4:end].split("\n"):
        k, _, v = line.partition(": ")
        front[k] = v
    return front, text[end + 5:]


def render_front(front):
    return "---\n" + "".join(f"{k}: {front[k]}\n" for k in FIELDS) + "---\n"


def entry(kind, num, sid8, ts, model, body):
    return (f"[LOG_ENTRY type={kind} num={num} session={sid8}]\n"
            f"timestamp: {ts}\nmodel: {model}\n\n{body}\n\n\n")


def write_atomic(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def log_error(msg):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _, ts = utc_now()
    with open(LOG_DIR / "capture-errors.log", "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def find_session_file(sid):
    matches = sorted(LOG_DIR.glob(f"*_{sid}.md"))
    return matches[0] if matches else None


def handle_prompt(p, sid):
    prompt = p.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        return
    dt, ts = utc_now()
    model = last_model(p.get("transcript_path")) or os.environ.get("ANTHROPIC_MODEL") or "unknown"
    sid8 = sid[:8]
    path = find_session_file(sid)
    if path is None:
        path = LOG_DIR / f"{dt.strftime('%Y-%m-%d_%H-%M-%S')}_{sid}.md"
        front = {
            "session_id": sid, "date": dt.strftime("%Y-%m-%d"), "author": AUTHOR,
            "model": model, "tool": TOOL, "project": PROJECT, "total_exchanges": "0",
            "first_prompt_time": ts, "last_prompt_time": ts,
        }
        rest = (f"\n# Session Log - {front['date']}\n\n"
                f"Session: `{sid8}` | Project: `{PROJECT}` | Author: `{AUTHOR}`\n\n---\n\n")
    else:
        front, rest = parse(path.read_text(encoding="utf-8"))
    num = int(front["total_exchanges"]) + 1
    front.update(model=model, total_exchanges=str(num), last_prompt_time=ts)
    write_atomic(path, render_front(front) + rest + entry("PROMPT", num, sid8, ts, model, prompt))


def handle_stop(p, sid):
    path = find_session_file(sid)
    if path is None:
        log_error(f"session={sid[:8]} Stop with no captured prompt in this session: skipped")
        return
    front, rest = parse(path.read_text(encoding="utf-8"))
    num = int(front["total_exchanges"])
    transcript = p.get("transcript_path")
    body = p.get("last_assistant_message") or final_text_from_transcript(transcript) or NO_TEXT
    model = last_model(transcript) or front["model"]
    _, ts = utc_now()
    front["model"] = model
    write_atomic(path, render_front(front) + rest + entry("RESPONSE", num, sid[:8], ts, model, body))


def main():
    p = json.loads(sys.stdin.read())
    sid = re.sub(r"[^A-Za-z0-9_-]", "", str(p.get("session_id") or "")) or "unknown"
    event = p.get("hook_event_name")
    if event not in ("UserPromptSubmit", "Stop"):
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(Path(tempfile.gettempdir()) / "fanthom-capture.lock", "w") as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)
        (handle_prompt if event == "UserPromptSubmit" else handle_stop)(p, sid)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            log_error(traceback.format_exc().strip().replace("\n", " | "))
        except Exception:
            pass
    sys.exit(0)
