import json
from pathlib import Path

from services import history_service
from services.history_service import (
    list_report_history,
    load_report_history,
    save_report_history,
)


def use_temp_history(monkeypatch, tmp_path):
    logs_dir = tmp_path / "logs"
    reports_dir = logs_dir / "reports"
    history_file = logs_dir / "report_history.json"
    monkeypatch.setattr(history_service, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(history_service, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(history_service, "HISTORY_FILE", history_file)
    return logs_dir, reports_dir, history_file


def test_save_report_history_keeps_recent_10_records(monkeypatch, tmp_path):
    _, _, history_file = use_temp_history(monkeypatch, tmp_path)

    latest_file = None
    latest_update = None
    for i in range(12):
        latest_file, latest_update = save_report_history(
            report=f"# Report {i}",
            title=f"题目 {i}",
            language="Python3",
            status=f"status {i}",
        )

    records = json.loads(history_file.read_text(encoding="utf-8"))
    choices = list_report_history()

    assert len(records) == 10
    assert len(choices) == 10
    assert records[0]["title"] == "题目 11"
    assert records[-1]["title"] == "题目 2"
    assert Path(latest_file).exists()
    assert latest_update["choices"] == choices
    assert latest_update["value"] == choices[0]


def test_save_report_history_redacts_sensitive_values(monkeypatch, tmp_path):
    _, _, history_file = use_temp_history(monkeypatch, tmp_path)

    report_file, _ = save_report_history(
        report="token sk-1234567890abcdef LEETCODE_SESSION=secret-session; csrftoken=secret-csrf",
        title="敏感题",
        language="Python3",
        status="status sk-abcdef1234567890",
    )

    history_text = history_file.read_text(encoding="utf-8")
    report_text = Path(report_file).read_text(encoding="utf-8")

    assert "sk-1234567890abcdef" not in history_text
    assert "secret-session" not in history_text
    assert "secret-csrf" not in history_text
    assert "[REDACTED]" in history_text
    assert "secret-session" not in report_text


def test_corrupt_history_json_returns_empty_list(monkeypatch, tmp_path):
    logs_dir, _, history_file = use_temp_history(monkeypatch, tmp_path)
    logs_dir.mkdir(parents=True)
    history_file.write_text("{not json", encoding="utf-8")

    assert list_report_history() == []
    assert load_report_history("missing") == ("未找到对应的历史记录。", None)


def test_load_report_history_returns_report_and_restores_missing_file(monkeypatch, tmp_path):
    _, _, _ = use_temp_history(monkeypatch, tmp_path)
    report_file, update = save_report_history(
        report="# 历史报告",
        title="历史题",
        language="Python3",
        status="ok",
    )
    Path(report_file).unlink()

    report, restored_file = load_report_history(update["choices"][0])

    assert report == "# 历史报告"
    assert restored_file is not None
    assert Path(restored_file).exists()
    assert Path(restored_file).read_text(encoding="utf-8") == "# 历史报告"


def test_safe_filename_handles_chinese_spaces_and_symbols():
    assert history_service._safe_filename("两数之和 / Python: 测试?") == "两数之和_Python_测试"
    assert history_service._safe_filename("   ***   ") == "report"
