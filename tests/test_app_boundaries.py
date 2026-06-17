from pathlib import Path


def test_app_keeps_business_implementation_in_services():
    app_source = Path("app.py").read_text(encoding="utf-8")

    forbidden_markers = [
        "get_leetcode_problem",
        "search_leetcode_problems",
        "MarkdownReportBuilder",
        "LLMDiagnosis",
        "SandboxRunner",
        "VariantGenerator",
    ]

    for marker in forbidden_markers:
        assert marker not in app_source
