"""Local report history and Markdown export helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import gradio as gr


MAX_HISTORY = 10
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = LOGS_DIR / "reports"
HISTORY_FILE = LOGS_DIR / "report_history.json"

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"LEETCODE_SESSION\s*=\s*[^;\s]+", re.IGNORECASE),
    re.compile(r"csrftoken\s*=\s*[^;\s]+", re.IGNORECASE),
]


def save_report_history(report: str, title: str, language: str, status: str) -> tuple[str | None, object]:
    """Save a report file and prepend it to local history."""
    if not (report or "").strip():
        return None, gr.update(choices=list_report_history(), value=None)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_report = _redact_sensitive_text(report)
    safe_status = _redact_sensitive_text(status)
    safe_title = (title or "自定义题目").strip() or "自定义题目"
    safe_language = (language or "Unknown").strip() or "Unknown"
    record_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    file_path = REPORTS_DIR / f"{_safe_filename(safe_title)}_{_safe_filename(safe_language)}_{record_id}.md"
    file_path.write_text(safe_report, encoding="utf-8")

    records = _read_history_records()
    record = {
        "id": record_id,
        "created_at": created_at,
        "title": safe_title,
        "language": safe_language,
        "status": safe_status,
        "report": safe_report,
        "file_path": str(file_path),
    }
    records.insert(0, record)
    records = records[:MAX_HISTORY]
    _write_history_records(records)

    choices = _history_choices(records)
    return str(file_path), gr.update(choices=choices, value=choices[0] if choices else None)


def list_report_history() -> list[str]:
    """Return dropdown choices for recent diagnosis reports."""
    return _history_choices(_read_history_records())


def load_report_history(choice: str) -> tuple[str, str | None]:
    """Load one history item for display and download."""
    if not choice:
        return "请选择一条历史记录。", None

    record_id = _choice_to_id(choice)
    for record in _read_history_records():
        if record.get("id") == record_id:
            file_path = record.get("file_path") or None
            if file_path and not Path(file_path).exists():
                file_path = _restore_report_file(record)
            return record.get("report", ""), file_path

    return "未找到对应的历史记录。", None


def _read_history_records() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [record for record in data if isinstance(record, dict)]


def _write_history_records(records: list[dict]) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(records[:MAX_HISTORY], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _history_choices(records: list[dict]) -> list[str]:
    choices = []
    for record in records[:MAX_HISTORY]:
        record_id = record.get("id", "")
        created_at = record.get("created_at", "")
        title = record.get("title", "自定义题目")
        language = record.get("language", "")
        choices.append(f"{created_at} | {title} | {language} | {record_id}")
    return choices


def _choice_to_id(choice: str) -> str:
    return (choice or "").rsplit("|", 1)[-1].strip()


def _restore_report_file(record: dict) -> str | None:
    report = record.get("report", "")
    if not report:
        return None
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REPORTS_DIR / (
        f"{_safe_filename(record.get('title', '自定义题目'))}_"
        f"{_safe_filename(record.get('language', 'Unknown'))}_"
        f"{record.get('id', uuid4().hex[:8])}.md"
    )
    file_path.write_text(report, encoding="utf-8")
    record["file_path"] = str(file_path)
    records = _read_history_records()
    for item in records:
        if item.get("id") == record.get("id"):
            item["file_path"] = str(file_path)
            break
    _write_history_records(records)
    return str(file_path)


def _safe_filename(value: str, limit: int = 64) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    value = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value, flags=re.UNICODE)
    value = value.strip("._-")
    return (value or "report")[:limit]


def _redact_sensitive_text(text: str) -> str:
    safe_text = text or ""
    for pattern in _SECRET_PATTERNS:
        safe_text = pattern.sub("[REDACTED]", safe_text)
    return safe_text
