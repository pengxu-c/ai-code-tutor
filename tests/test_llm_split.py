from analyzer.llm_diagnosis import LLMDiagnosis


class CapturingLLM(LLMDiagnosis):
    def __init__(self):
        super().__init__(api_key="sk-test")
        self.messages = []

    def _call_llm(self, messages, **kwargs):
        self.messages = messages
        return "\n".join(
            [
                "### 1. 错误定位",
                "未发现导致失败的错误",
                "",
                "### 3. 修复建议",
                "无需修复",
            ]
        )


def test_split_diagnosis_response_moves_fix_sections():
    response = "\n".join(
        [
            "### 1. Error Location",
            "LOCATION_CONTENT",
            "",
            "### 2. Cause Analysis",
            "CAUSE_CONTENT",
            "",
            "### 3. \u4fee\u590d\u5efa\u8bae",
            "FIX_CONTENT",
            "",
            "### 4. Knowledge Summary",
            "SUMMARY_CONTENT",
        ]
    )

    error_analysis, fix_suggestion = LLMDiagnosis()._split_diagnosis_response(response)

    assert "LOCATION_CONTENT" in error_analysis
    assert "CAUSE_CONTENT" in error_analysis
    assert "FIX_CONTENT" not in error_analysis
    assert "SUMMARY_CONTENT" not in error_analysis
    assert "FIX_CONTENT" in fix_suggestion
    assert "SUMMARY_CONTENT" in fix_suggestion


def test_split_diagnosis_response_keeps_text_when_fix_heading_missing():
    response = """### 1. Error Location
LOCATION_CONTENT

### 2. Cause Analysis
CAUSE_CONTENT
"""

    error_analysis, fix_suggestion = LLMDiagnosis()._split_diagnosis_response(response)

    assert error_analysis == response.strip()
    assert fix_suggestion == ""


def test_diagnose_prompt_includes_validation_results_and_no_fabrication_rule():
    llm = CapturingLLM()

    llm.diagnose(
        code="print('ok')",
        test_cases=[{"input": "", "expected": "ok"}],
        validation_results=[
            {
                "input": "",
                "expected": "ok",
                "actual": "ok",
                "passed": True,
                "error": "",
            }
        ],
    )

    combined_prompt = "\n".join(message["content"] for message in llm.messages)

    assert "沙箱验证结果" in combined_prompt
    assert "用例1：通过" in combined_prompt
    assert "不要臆造错误" in combined_prompt
    assert "未发现导致失败的错误" in combined_prompt
