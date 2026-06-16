from types import SimpleNamespace

from services import diagnosis_service
from services.diagnosis_service import (
    _DiagnosisDependencies,
    _get_code_explanation_with_dependencies,
    _run_diagnosis_with_dependencies,
)


class FakeASTAnalyzer:
    def __init__(self):
        self.calls = []

    def analyze(self, code):
        self.calls.append(code)
        return "AST_OK"


class FakeLLM:
    def __init__(self, *, diagnose_error=None, explain_error=None):
        self.api_key = ""
        self.diagnose_error = diagnose_error
        self.explain_error = explain_error
        self.diagnose_calls = []
        self.explain_calls = []

    def diagnose(self, **kwargs):
        self.diagnose_calls.append(kwargs)
        if self.diagnose_error:
            raise self.diagnose_error
        return {
            "error_analysis": "ERROR_ANALYSIS",
            "fix_suggestion": "FIX_SUGGESTION",
        }

    def explain_code(self, code, language):
        self.explain_calls.append({"code": code, "language": language})
        if self.explain_error:
            raise self.explain_error
        return "EXPLANATION_OK"


class FakeSandboxRunner:
    def __init__(self):
        self.calls = []

    def run_tests(self, code, test_cases):
        self.calls.append({"code": code, "test_cases": test_cases})
        return [
            SimpleNamespace(
                input_data=test_cases[0]["input"],
                expected_output=test_cases[0]["expected"],
                actual_output=test_cases[0]["expected"],
                passed=True,
                error="",
            )
        ]


class FakeVariantGenerator:
    def __init__(self):
        self.llm = SimpleNamespace(api_key="")
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return [
            {
                "title": "变式 A",
                "description": "VARIANT_DESCRIPTION",
                "difficulty": "中等",
                "source": "fake",
            }
        ]


def make_deps(**overrides):
    deps = {
        "ast_analyzer": FakeASTAnalyzer(),
        "llm_diagnosis": FakeLLM(),
        "sandbox_runner": FakeSandboxRunner(),
        "variant_generator": FakeVariantGenerator(),
    }
    deps.update(overrides)
    return _DiagnosisDependencies(**deps)


def run_with_deps(deps, **overrides):
    args = {
        "code": "print('ok')",
        "language": "Python3",
        "problem_desc": "# 两数之和\n数组 哈希",
        "error_info": "NameError",
        "test_input": "[]",
        "test_expected": "ok",
        "generate_variants": True,
        "api_key": "sk-test-key",
    }
    args.update(overrides)
    return _run_diagnosis_with_dependencies(deps, **args)


def force_report_flags(monkeypatch):
    monkeypatch.setattr(diagnosis_service, "REPORT_INCLUDE_AST", True)
    monkeypatch.setattr(diagnosis_service, "REPORT_INCLUDE_SANDBOX", True)
    monkeypatch.setattr(diagnosis_service, "REPORT_INCLUDE_VARIANT", True)
    monkeypatch.setattr(
        diagnosis_service,
        "save_report_history",
        lambda report, title, language, status: ("fake-report.md", {"choices": ["history-1"], "value": "history-1"}),
    )


def test_run_diagnosis_empty_code_returns_empty_report(monkeypatch):
    force_report_flags(monkeypatch)
    report, status, variant_update, variants, report_file, history_update = run_with_deps(make_deps(), code="   ")

    assert report == ""
    assert status == "请输入需要诊断的代码。"
    assert variant_update["choices"] == []
    assert variant_update["value"] is None
    assert variants == []
    assert report_file is None
    assert history_update["__type__"] == "update"


def test_run_diagnosis_python_success_path_calls_all_dependencies(monkeypatch):
    force_report_flags(monkeypatch)
    deps = make_deps()

    report, status, variant_update, variants, report_file, history_update = run_with_deps(deps)

    assert deps.ast_analyzer.calls == ["print('ok')"]
    assert deps.llm_diagnosis.api_key == "sk-test-key"
    assert deps.variant_generator.llm.api_key == "sk-test-key"
    assert deps.llm_diagnosis.diagnose_calls[0]["test_cases"] == [{"input": "[]", "expected": "ok"}]
    assert deps.llm_diagnosis.diagnose_calls[0]["validation_results"] == [
        {
            "input": "[]",
            "expected": "ok",
            "actual": "ok",
            "passed": True,
            "error": "",
        }
    ]
    assert deps.sandbox_runner.calls[0]["test_cases"] == [{"input": "[]", "expected": "ok"}]
    assert deps.variant_generator.calls[0]["tags"] == ["数组", "哈希表"]
    assert "AST_OK" in report
    assert "ERROR_ANALYSIS" in report
    assert "FIX_SUGGESTION" in report
    assert "VARIANT_DESCRIPTION" in report
    assert "AST 结构分析完成" in status
    assert "LLM 智能诊断完成" in status
    assert "沙箱运行验证完成" in status
    assert "变式训练生成完成（1 题）" in status
    assert variant_update["choices"] == ["1. 变式 A（中等）"]
    assert variant_update["value"] == "1. 变式 A（中等）"
    assert variants == [
        {
            "title": "变式 A",
            "description": "VARIANT_DESCRIPTION",
            "difficulty": "中等",
            "source": "fake",
        }
    ]
    assert report_file == "fake-report.md"
    assert history_update == {"choices": ["history-1"], "value": "history-1"}


def test_run_diagnosis_non_python_skips_ast_and_sandbox(monkeypatch):
    force_report_flags(monkeypatch)
    deps = make_deps()

    report, status, variant_update, variants, report_file, history_update = run_with_deps(
        deps,
        language="Java",
        generate_variants=False,
    )

    assert deps.ast_analyzer.calls == []
    assert deps.sandbox_runner.calls == []
    assert deps.llm_diagnosis.diagnose_calls[0]["language"] == "Java"
    assert "Python AST 结构分析仅支持 Python3 代码" in report
    assert "当前沙箱运行暂仅支持 Python3" in report
    assert "已跳过 AST（Java）" in status
    assert "已跳过沙箱（Java）" in status
    assert variant_update["choices"] == []
    assert variants == []
    assert report_file == "fake-report.md"
    assert history_update == {"choices": ["history-1"], "value": "history-1"}


def test_run_diagnosis_llm_exception_goes_into_report(monkeypatch):
    force_report_flags(monkeypatch)
    deps = make_deps(llm_diagnosis=FakeLLM(diagnose_error=RuntimeError("llm down")))

    report, status, variant_update, variants, report_file, history_update = run_with_deps(
        deps,
        test_input="",
        test_expected="",
        generate_variants=False,
    )

    assert "LLM 诊断失败：llm down" in report
    assert "请检查 API Key 配置是否正确" in report
    assert "LLM 诊断失败: llm down" in status
    assert variant_update["choices"] == []
    assert variants == []
    assert report_file == "fake-report.md"
    assert history_update == {"choices": ["history-1"], "value": "history-1"}


def test_get_code_explanation_uses_api_key_and_handles_errors():
    deps = make_deps(llm_diagnosis=FakeLLM())

    assert _get_code_explanation_with_dependencies(deps, "", "Python3", "") == "请先输入代码。"
    assert _get_code_explanation_with_dependencies(deps, "print(1)", "Python3", "sk-page") == "EXPLANATION_OK"
    assert deps.llm_diagnosis.api_key == "sk-page"
    assert deps.llm_diagnosis.explain_calls == [{"code": "print(1)", "language": "Python3"}]

    failing_deps = make_deps(llm_diagnosis=FakeLLM(explain_error=RuntimeError("explain down")))
    assert (
        _get_code_explanation_with_dependencies(failing_deps, "print(1)", "Python3", "")
        == "解释失败：explain down"
    )
