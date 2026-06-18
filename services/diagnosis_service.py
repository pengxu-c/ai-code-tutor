"""Diagnosis and explanation workflows for the Gradio UI."""

from dataclasses import dataclass
import time

import gradio as gr

from analyzer.ast_analyzer import ASTAnalyzer
from analyzer.llm_diagnosis import LLMDiagnosis
from analyzer.sandbox import SandboxRunner
from config import REPORT_INCLUDE_AST, REPORT_INCLUDE_SANDBOX, REPORT_INCLUDE_VARIANT
from generator.variant import VariantGenerator
from services.history_service import save_report_history
from services.variant_service import _format_variant_choice, _normalize_variants
from utils.languages import is_python_language
from utils.logger import setup_logger
from utils.markdown_builder import MarkdownReportBuilder

logger = setup_logger(__name__)
ast_analyzer = ASTAnalyzer()
llm_diagnosis = LLMDiagnosis()
sandbox_runner = SandboxRunner()
variant_generator = VariantGenerator()


@dataclass
class _DiagnosisDependencies:
    ast_analyzer: ASTAnalyzer
    llm_diagnosis: LLMDiagnosis
    sandbox_runner: SandboxRunner
    variant_generator: VariantGenerator


def _get_dependencies() -> _DiagnosisDependencies:
    """Return the current service dependencies, keeping Gradio entrypoints simple."""
    return _DiagnosisDependencies(
        ast_analyzer=ast_analyzer,
        llm_diagnosis=llm_diagnosis,
        sandbox_runner=sandbox_runner,
        variant_generator=variant_generator,
    )


def run_diagnosis(
    code: str,
    language: str,
    problem_desc: str,
    error_info: str,
    test_input: str,
    test_expected: str,
    generate_variants: bool,
    api_key: str,
) -> tuple[str, str, object, list[dict]]:
    """
    执行完整的诊断流程

    Returns:
        (markdown_report, status_message)
    """
    return _run_diagnosis_with_dependencies(
        _get_dependencies(),
        code=code,
        language=language,
        problem_desc=problem_desc,
        error_info=error_info,
        test_input=test_input,
        test_expected=test_expected,
        generate_variants=generate_variants,
        api_key=api_key,
    )


def _run_diagnosis_with_dependencies(
    deps: _DiagnosisDependencies,
    code: str,
    language: str,
    problem_desc: str,
    error_info: str,
    test_input: str,
    test_expected: str,
    generate_variants: bool,
    api_key: str,
) -> tuple[str, str, object, list[dict], str | None, object]:
    """Run diagnosis with injectable dependencies for service-level tests."""
    start_time = time.time()

    # 参数校验
    if not code.strip():
        return "", "请输入需要诊断的代码。", gr.update(choices=[], value=None), [], None, gr.update()

    # 如果用户配置了 API Key，动态更新
    if api_key and api_key.strip():
        deps.llm_diagnosis.api_key = api_key.strip()
        if hasattr(deps.variant_generator, "llm"):
            deps.variant_generator.llm.api_key = api_key.strip()

    # 构建报告
    title = _infer_problem_title(problem_desc)
    builder = MarkdownReportBuilder(problem_title=title)
    builder.set_project_info("项目4", "AI编程题讲解机器人")

    status_parts = []
    generated_variants = []

    # ------------------------------------------------------------------
    # 第 1 步：AST 结构分析
    # ------------------------------------------------------------------
    if REPORT_INCLUDE_AST:
        if is_python_language(language):
            try:
                ast_report = deps.ast_analyzer.analyze(code)
                builder.add_ast_analysis(ast_report)
                status_parts.append("AST 结构分析完成")
            except Exception as e:
                logger.error(f"AST 分析异常: {e}")
                status_parts.append(f"AST 分析失败: {e}")
        else:
            builder.add_ast_analysis(
                f"当前选择的编程语言为 **{language}**。\n\n"
                "Python AST 结构分析仅支持 Python3 代码，因此本次跳过 AST 分析。"
            )
            status_parts.append(f"已跳过 AST（{language}）")

    # 构造测试用例
    test_cases = []
    if test_input.strip() and test_expected.strip():
        test_cases.append({"input": test_input, "expected": test_expected})

    sandbox_results = []

    # ------------------------------------------------------------------
    # 第 2 步：沙箱运行验证
    # ------------------------------------------------------------------
    if REPORT_INCLUDE_SANDBOX and test_cases:
        if is_python_language(language):
            try:
                results = deps.sandbox_runner.run_tests(
                    code=code,
                    test_cases=test_cases,
                )
                sandbox_results = [{
                    "input": r.input_data,
                    "expected": r.expected_output,
                    "actual": r.actual_output,
                    "passed": r.passed,
                    "error": r.error,
                } for r in results]
                builder.add_sandbox_results(sandbox_results)
                passed = sum(1 for r in sandbox_results if r.get("passed"))
                status_parts.append(f"沙箱运行验证完成（{passed}/{len(sandbox_results)} 通过）")
            except Exception as e:
                logger.error(f"沙箱运行异常: {e}")
                builder.add_sandbox_results([])
                status_parts.append(f"沙箱运行失败: {e}")
        else:
            builder.add_sandbox_results(
                [],
                skipped_reason=f"当前沙箱运行暂仅支持 Python3，已跳过 {language} 代码执行验证。",
            )
            status_parts.append(f"已跳过沙箱（{language}）")

    # ------------------------------------------------------------------
    # 第 3 步：LLM 智能诊断
    # ------------------------------------------------------------------
    try:
        diag_result = deps.llm_diagnosis.diagnose(
            code=code,
            problem_desc=problem_desc,
            error_info=error_info,
            test_cases=test_cases if test_cases else None,
            validation_results=sandbox_results if sandbox_results else None,
            language=language,
        )
        builder.add_error_diagnosis(
            error_analysis=diag_result["error_analysis"],
            fix_suggestion=diag_result["fix_suggestion"],
        )
        status_parts.append("LLM 智能诊断完成")
    except Exception as e:
        logger.error(f"LLM 诊断异常: {e}")
        builder.add_error_diagnosis(
            error_analysis=f"LLM 诊断失败：{str(e)}\n\n请检查 API Key 配置是否正确。",
            fix_suggestion="",
        )
        status_parts.append(f"LLM 诊断失败: {e}")

    # ------------------------------------------------------------------
    # 第 4 步：变式训练
    # ------------------------------------------------------------------
    if REPORT_INCLUDE_VARIANT and generate_variants:
        try:
            # 从题目描述推断标签
            tags = []
            if "数组" in problem_desc or "array" in problem_desc.lower():
                tags.append("数组")
            if "链表" in problem_desc or "linked list" in problem_desc.lower():
                tags.append("链表")
            if "树" in problem_desc or "tree" in problem_desc.lower():
                tags.append("树")
            if "哈希" in problem_desc or "hash" in problem_desc.lower():
                tags.append("哈希表")
            if "动态规划" in problem_desc or "dp" in problem_desc.lower():
                tags.append("动态规划")
            if "递归" in problem_desc or "recursion" in problem_desc.lower():
                tags.append("递归")
            if "二分" in problem_desc or "binary" in problem_desc.lower():
                tags.append("二分查找")
            if "栈" in problem_desc or "stack" in problem_desc.lower():
                tags.append("栈")
            if "双指针" in problem_desc or "two pointer" in problem_desc.lower():
                tags.append("双指针")

            variants = deps.variant_generator.generate(
                problem_desc=problem_desc or code,
                code=code,
                tags=tags if tags else None,
                count=3,
            )
            generated_variants = _normalize_variants(variants)
            builder.add_variant_problems([v["description"] for v in variants])
            status_parts.append(f"变式训练生成完成（{len(variants)} 题）")
        except Exception as e:
            logger.error(f"变式题生成异常: {e}")
            status_parts.append(f"变式题生成失败: {e}")

    # 生成报告
    report = builder.build()
    elapsed = time.time() - start_time
    status = f"诊断完成（耗时 {elapsed:.1f}s）：" + " → ".join(status_parts)
    variant_choices = [
        _format_variant_choice(i, variant)
        for i, variant in enumerate(generated_variants, 1)
    ]

    logger.info(status)
    report_file, history_update = save_report_history(
        report=report,
        title=title,
        language=language,
        status=status,
    )
    return (
        report,
        status,
        gr.update(choices=variant_choices, value=variant_choices[0] if variant_choices else None),
        generated_variants,
        report_file,
        history_update,
    )


def _infer_problem_title(problem_desc: str) -> str:
    """从自定义/在线题目描述中推断报告标题。"""
    for line in (problem_desc or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or "自定义题目"
        if stripped:
            return stripped[:40]
    return "自定义题目"


def get_code_explanation(code: str, language: str, api_key: str) -> str:
    """生成代码解释"""
    return _get_code_explanation_with_dependencies(
        _get_dependencies(),
        code=code,
        language=language,
        api_key=api_key,
    )


def _get_code_explanation_with_dependencies(
    deps: _DiagnosisDependencies,
    code: str,
    language: str,
    api_key: str,
) -> str:
    """Generate a code explanation with injectable dependencies for tests."""
    if not code.strip():
        return "请先输入代码。"
    if api_key and api_key.strip():
        deps.llm_diagnosis.api_key = api_key.strip()
    try:
        return deps.llm_diagnosis.explain_code(code, language=language)
    except Exception as e:
        return f"解释失败：{str(e)}"
