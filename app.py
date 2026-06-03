"""
AI 编程题讲解机器人 - 主程序入口
错解代码诊断与变式训练系统

功能：
  1. 用户输入错解代码 + 题目描述 + 报错信息
  2. AST 自动分析代码结构
  3. LLM 智能诊断错误原因并给出修复建议
  4. 沙箱安全运行代码验证测试用例
  5. 自动生成变式训练题
  6. 输出完整的 Markdown 讲解报告
"""
import os
import sys
import json
import re
import socket
import time
import traceback

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr

from config import (
    GRADIO_SERVER_NAME,
    GRADIO_SERVER_PORT,
    GRADIO_SHARE,
    GRADIO_THEME,
    GRADIO_TITLE,
    GRADIO_DESCRIPTION,
    REPORT_INCLUDE_AST,
    REPORT_INCLUDE_SANDBOX,
    REPORT_INCLUDE_VARIANT,
)
from utils.logger import setup_logger
from utils.markdown_builder import MarkdownReportBuilder
from analyzer.ast_analyzer import ASTAnalyzer
from analyzer.llm_diagnosis import LLMDiagnosis
from analyzer.sandbox import SandboxRunner
from generator.variant import VariantGenerator
from database import (
    get_leetcode_problem,
    search_leetcode_problems,
)
from utils.languages import (
    get_gradio_language,
    get_language_choices,
    get_leetcode_slug,
    is_python_language,
)

# ==================== 初始化 ====================
logger = setup_logger(__name__)
ast_analyzer = ASTAnalyzer()
llm_diagnosis = LLMDiagnosis()
sandbox_runner = SandboxRunner()
variant_generator = VariantGenerator()

# ======================================================================
#  核心诊断流程
# ======================================================================
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
    start_time = time.time()

    # 参数校验
    if not code.strip():
        return "", "请输入需要诊断的代码。", gr.update(choices=[], value=None), []

    # 如果用户配置了 API Key，动态更新
    if api_key and api_key.strip():
        llm_diagnosis.api_key = api_key.strip()
        variant_generator.llm.api_key = api_key.strip()

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
                ast_report = ast_analyzer.analyze(code)
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

    # ------------------------------------------------------------------
    # 第 2 步：LLM 智能诊断
    # ------------------------------------------------------------------
    try:
        # 构造测试用例
        test_cases = []
        if test_input.strip() and test_expected.strip():
            test_cases.append({"input": test_input, "expected": test_expected})

        diag_result = llm_diagnosis.diagnose(
            code=code,
            problem_desc=problem_desc,
            error_info=error_info,
            test_cases=test_cases if test_cases else None,
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
    # 第 3 步：沙箱运行验证
    # ------------------------------------------------------------------
    if REPORT_INCLUDE_SANDBOX and test_input.strip():
        if is_python_language(language):
            try:
                results = sandbox_runner.run_tests(
                    code=code,
                    test_cases=[{"input": test_input, "expected": test_expected}],
                )
                builder.add_sandbox_results([{
                    "input": r.input_data,
                    "expected": r.expected_output,
                    "actual": r.actual_output,
                    "passed": r.passed,
                    "error": r.error,
                } for r in results])
                status_parts.append("沙箱运行验证完成")
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

            variants = variant_generator.generate(
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
    return (
        report,
        status,
        gr.update(choices=variant_choices, value=variant_choices[0] if variant_choices else None),
        generated_variants,
    )


# ======================================================================
#  辅助功能
# ======================================================================
def search_leetcode(
    keyword: str,
    difficulty: str,
    leetcode_session: str = "",
    leetcode_csrf_token: str = "",
) -> tuple[list[list[str]], str]:
    """在线检索 LeetCode 题目。"""
    try:
        rows = search_leetcode_problems(
            keyword=keyword,
            difficulty=difficulty,
            limit=20,
            leetcode_session=leetcode_session,
            csrf_token=leetcode_csrf_token,
        )
        table = [
            [
                r.get("id", ""),
                r.get("title", ""),
                r.get("difficulty", ""),
                ", ".join(r.get("tags", [])),
                r.get("slug", ""),
                "是" if r.get("paid_only") else "否",
            ]
            for r in rows
        ]
        return table, f"已检索到 {len(table)} 道题。复制最后一列 slug 到下方即可导入。"
    except Exception as e:
        return [], f"LeetCode 检索失败：{str(e)}"


def fill_slug_from_result(results: list[list[str]], evt: gr.SelectData) -> object:
    """点击检索结果表格时，把对应行的 Slug 填入输入框。"""
    slug = ""

    if evt and isinstance(evt.value, str) and _looks_like_slug(evt.value):
        slug = evt.value

    if not slug and evt and evt.index is not None:
        row_index = _extract_dataframe_row_index(evt.index)
        if row_index is not None:
            try:
                row = results.iloc[row_index].tolist() if hasattr(results, "iloc") else results[row_index]
                slug = str(row[4]) if len(row) > 4 else ""
            except (TypeError, IndexError, KeyError, AttributeError):
                slug = ""

    return slug if slug else gr.update()


def _extract_dataframe_row_index(index) -> int | None:
    """Extract row index from the different shapes Gradio can emit."""
    if isinstance(index, int):
        return index
    if isinstance(index, (list, tuple)) and index:
        first = index[0]
        return first if isinstance(first, int) else None
    if isinstance(index, dict):
        for key in ("row", "index"):
            value = index.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, (list, tuple)) and value and isinstance(value[0], int):
                return value[0]
    return None


def _looks_like_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value.strip()))


def import_generated_variant(selected_variant: str, variants: list[dict], language: str) -> tuple[object, object, object, object, str]:
    """把生成的变式题导入左侧输入区。"""
    index = _parse_variant_index(selected_variant)
    if index is None or not variants or index >= len(variants):
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "请先生成变式题，并选择要导入的题目。",
        )

    variant = variants[index]
    description = variant.get("description", "")
    title = variant.get("title", "")
    if title and title not in description:
        description = f"# {title}\n\n{description}"

    return (
        gr.update(value="", language=get_gradio_language(language)),
        description,
        "",
        "",
        f"已导入变式题：{title or selected_variant}",
    )


def load_leetcode_template(
    slug_or_url: str,
    language: str,
    leetcode_session: str = "",
    leetcode_csrf_token: str = "",
) -> tuple[object, str, str, str, str]:
    """从 LeetCode 在线导入题目模板。"""
    try:
        problem = get_leetcode_problem(
            slug_or_url,
            language_slug=get_leetcode_slug(language),
            leetcode_session=leetcode_session,
            csrf_token=leetcode_csrf_token,
        )
        examples = problem.get("examples", [])
        test_in = str(examples[0].get("input", "")) if examples else ""
        test_out = str(examples[0].get("output", "")) if examples else ""
        desc = _format_leetcode_description(problem)
        status = f"已导入 LeetCode 题目：{problem.get('title', '')}"
        if (leetcode_session or leetcode_csrf_token) and status.startswith("已导入"):
            status += "（已使用 LeetCode 登录态）"
        if problem.get("paid_only"):
            status += "（会员题，题面可能不完整）"
        code_update = gr.update(
            value=problem.get("starter_code", ""),
            language=get_gradio_language(language),
        )
        return code_update, desc, test_in, test_out, status
    except Exception as e:
        return gr.update(language=get_gradio_language(language)), "", "", "", f"LeetCode 导入失败：{str(e)}"


def load_leetcode_template_and_switch(
    slug_or_url: str,
    language: str,
    leetcode_session: str = "",
    leetcode_csrf_token: str = "",
) -> tuple[object, str, str, str, str, object]:
    """导入 LeetCode 题目，并切回输入与诊断页。"""
    code, desc, test_in, test_out, status = load_leetcode_template(
        slug_or_url,
        language,
        leetcode_session=leetcode_session,
        leetcode_csrf_token=leetcode_csrf_token,
    )
    target_tab = "input" if status.startswith("已导入") else "library"
    return code, desc, test_in, test_out, status, gr.update(selected=target_tab)


def apply_language_change(language: str, current_code: str) -> object:
    """更新代码编辑器语言高亮，保留用户当前代码。"""
    return gr.update(value=current_code, language=get_gradio_language(language))


def _format_leetcode_description(problem: dict) -> str:
    """把在线题目转换成当前报告系统使用的题目描述。"""
    parts = [
        f"# {problem.get('title', 'LeetCode 题目')}",
        f"- 难度：{problem.get('difficulty', '未知')}",
    ]
    tags = problem.get("tags", [])
    if tags:
        parts.append(f"- 标签：{', '.join(tags)}")
    if problem.get("leetcode_url"):
        parts.append(f"- 来源：{problem['leetcode_url']}")
    if problem.get("paid_only"):
        parts.append("- 注意：该题可能为会员题，在线接口返回的题面可能不完整。")
    parts.append("")
    parts.append(problem.get("description", ""))
    return "\n".join(parts).strip()


def _infer_problem_title(problem_desc: str) -> str:
    """从自定义/在线题目描述中推断报告标题。"""
    for line in (problem_desc or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or "自定义题目"
        if stripped:
            return stripped[:40]
    return "自定义题目"


def _normalize_variants(variants: list[dict]) -> list[dict]:
    """保留生成结果中导入所需的稳定字段。"""
    normalized = []
    for i, variant in enumerate(variants, 1):
        title = variant.get("title") or _extract_variant_title(variant.get("description", "")) or f"变式题 {i}"
        normalized.append({
            "title": title,
            "description": variant.get("description", ""),
            "difficulty": variant.get("difficulty", ""),
            "source": variant.get("source", ""),
        })
    return normalized


def _format_variant_choice(index: int, variant: dict) -> str:
    title = variant.get("title") or f"变式题 {index}"
    difficulty = variant.get("difficulty")
    suffix = f"（{difficulty}）" if difficulty else ""
    return f"{index}. {title}{suffix}"


def _parse_variant_index(selected_variant: str) -> int | None:
    if not selected_variant:
        return None
    prefix = selected_variant.split(".", 1)[0].strip()
    if not prefix.isdigit():
        return None
    return int(prefix) - 1


def _extract_variant_title(description: str) -> str:
    for line in (description or "").splitlines():
        stripped = line.strip().strip("*# ")
        if not stripped:
            continue
        if "题目名称" in stripped and "：" in stripped:
            return stripped.split("：", 1)[1].strip().strip("*")
        return stripped[:40]
    return ""


def get_code_explanation(code: str, language: str, api_key: str) -> str:
    """生成代码解释"""
    if not code.strip():
        return "请先输入代码。"
    if api_key and api_key.strip():
        llm_diagnosis.api_key = api_key.strip()
    try:
        return llm_diagnosis.explain_code(code, language=language)
    except Exception as e:
        return f"解释失败：{str(e)}"


def _find_available_port(preferred_port: int, host: str = "127.0.0.1", retries: int = 10) -> int:
    """Return preferred_port if available, otherwise try the next few ports."""
    for port in range(preferred_port, preferred_port + retries + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    return preferred_port


# ======================================================================
#  Gradio 界面构建
# ======================================================================
def build_ui():
    """构建 Gradio 交互界面"""

    code_font_js = """
    (fontSize) => {
        const size = Number(fontSize) || 14;
        document.documentElement.style.setProperty("--code-editor-font-size", `${size}px`);
    }
    """
    code_expand_js = """
    (expanded) => {
        const height = expanded ? "560px" : "300px";
        document.documentElement.style.setProperty("--code-editor-min-height", height);
        document.body.classList.toggle("code-area-expanded", Boolean(expanded));
    }
    """
    theme_mode_js = """
    (mode) => {
        const applyTheme = (selectedMode) => {
            const normalized = selectedMode || "跟随系统";
            document.body.dataset.themeMode = normalized;
            const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
            const dark = normalized === "深色" || (normalized === "跟随系统" && prefersDark);
            const targets = [document.documentElement, document.body];
            for (const target of targets) {
                target.classList.toggle("app-light-theme", !dark);
                target.classList.toggle("app-dark-theme", dark);
            }
            document.documentElement.style.colorScheme = dark ? "dark" : "light";
        };
        applyTheme(mode);
        if (!window.__aiCodeTutorThemeListener && window.matchMedia) {
            const media = window.matchMedia("(prefers-color-scheme: dark)");
            media.addEventListener("change", () => {
                if (document.body.dataset.themeMode === "跟随系统") {
                    applyTheme("跟随系统");
                }
            });
            window.__aiCodeTutorThemeListener = true;
        }
    }
    """
    custom_head = """
    <script>
    (() => {
        const applySystemTheme = () => {
            const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
            const targets = [document.documentElement, document.body];
            for (const target of targets) {
                target.classList.toggle("app-light-theme", !prefersDark);
                target.classList.toggle("app-dark-theme", prefersDark);
            }
            document.documentElement.style.colorScheme = prefersDark ? "dark" : "light";
        };
        applySystemTheme();
        if (window.matchMedia) {
            window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
                if (!document.body.dataset.themeMode || document.body.dataset.themeMode === "跟随系统") {
                    applySystemTheme();
                }
            });
        }
    })();
    </script>
    """

    # 自定义 CSS
    custom_css = """
    :root {
        --code-editor-font-size: 14px;
        --code-editor-min-height: 300px;
        --app-bg: #f4f7fb;
        --app-bg-soft: #eef6f6;
        --app-surface: #ffffff;
        --app-surface-muted: #f8fafc;
        --app-border: #dbe3ee;
        --app-border-strong: #bfd4ef;
        --app-text: #102033;
        --app-text-muted: #5b6b7f;
        --app-primary: #2563eb;
        --app-primary-strong: #1d4ed8;
        --app-indigo: #4338ca;
        --app-teal: #0f766e;
        --app-amber: #b45309;
        --app-rose: #be123c;
        --app-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
        --app-shadow-soft: 0 10px 26px rgba(15, 23, 42, 0.06);
        --app-font-sans: "Inter", "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
        --app-font-mono: "JetBrains Mono", "Cascadia Code", "Fira Code", "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    }
    body {
        background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 28rem),
            linear-gradient(180deg, #f8fbff 0%, var(--app-bg) 46%, #eef2f7 100%) !important;
        color: var(--app-text);
        font-family: var(--app-font-sans);
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
    }
    .gradio-container,
    .gradio-container * {
        font-family: var(--app-font-sans);
    }
    code,
    pre,
    .cm-editor,
    .cm-content,
    .cm-gutters {
        font-family: var(--app-font-mono) !important;
    }
    .main-title {
        text-align: center;
        margin-bottom: 10px;
    }
    .app-light-theme,
    .app-light-theme .gradio-container {
        color-scheme: light;
        --body-background-fill: #f8fafc;
        --body-text-color: #0f172a;
        --block-background-fill: #ffffff;
        --block-border-color: #e5e7eb;
        --input-background-fill: #ffffff;
        --input-border-color: #d1d5db;
        --button-secondary-background-fill: #f8fafc;
    }
    .app-dark-theme,
    .app-dark-theme .gradio-container {
        --app-bg: #0b1120;
        --app-bg-soft: #102033;
        --app-surface: #111827;
        --app-surface-muted: #0f172a;
        --app-border: #334155;
        --app-border-strong: #475569;
        --app-text: #e5e7eb;
        --app-text-muted: #a7b4c6;
        --app-primary: #60a5fa;
        --app-primary-strong: #93c5fd;
        --app-indigo: #a5b4fc;
        --app-teal: #5eead4;
        --app-amber: #fbbf24;
        --app-rose: #fb7185;
        --app-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
        --app-shadow-soft: 0 10px 26px rgba(0, 0, 0, 0.22);
        color-scheme: dark;
        --body-background-fill: #0f172a;
        --body-text-color: #e5e7eb;
        --block-background-fill: #111827;
        --block-border-color: #334155;
        --input-background-fill: #0b1220;
        --input-border-color: #475569;
        --button-secondary-background-fill: #1f2937;
    }
    .app-dark-theme .gradio-container,
    .app-dark-theme .main-tabs,
    .app-dark-theme .section-panel {
        background: var(--app-bg);
        color: #e5e7eb;
    }
    body.app-dark-theme,
    html.app-dark-theme body {
        background:
            radial-gradient(circle at top left, rgba(94, 234, 212, 0.10), transparent 28rem),
            linear-gradient(180deg, #0f172a 0%, #0b1120 54%, #111827 100%) !important;
    }
    .app-dark-theme .report-view .report-nav {
        background: var(--app-surface-muted);
        border-color: var(--app-border);
    }
    .app-dark-theme .report-view .report-nav-title,
    .app-dark-theme .report-view .report-section-summary {
        color: #dbeafe;
    }
    .app-dark-theme .report-view .report-nav a,
    .app-dark-theme .report-view .report-section-summary:hover {
        color: #93c5fd;
    }
    .status-bar {
        padding: 14px 16px;
        border-radius: 8px;
        background:
            linear-gradient(135deg, rgba(29, 78, 216, 0.96) 0%, rgba(15, 118, 110, 0.98) 100%),
            #1d4ed8;
        color: #ffffff !important;
        box-shadow: var(--app-shadow-soft);
        font-weight: 750;
        letter-spacing: 0;
        text-shadow: 0 1px 1px rgba(15, 23, 42, 0.28);
    }
    .status-bar,
    .status-bar *,
    .status-bar p,
    .status-bar span,
    .status-bar strong,
    .status-bar em,
    .status-bar a {
        color: #ffffff !important;
    }
    .status-bar p {
        margin: 0 !important;
        font-size: 1.03rem;
        line-height: 1.6;
    }
    .gradio-container {
        max-width: 1680px !important;
        padding: 24px !important;
        background: transparent !important;
    }
    .app-header {
        border: 1px solid rgba(191, 212, 239, 0.78);
        border-radius: 8px;
        padding: 22px 26px 20px;
        margin-bottom: 18px;
        background:
            linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.90)),
            linear-gradient(90deg, rgba(37, 99, 235, 0.08), rgba(15, 118, 110, 0.10));
        box-shadow: var(--app-shadow);
    }
    .app-header h1 {
        margin: 0 0 6px !important;
        color: var(--app-primary-strong);
        font-size: clamp(2rem, 3.2vw, 3rem);
        font-weight: 900;
        letter-spacing: 0;
    }
    .app-header h3,
    .app-header p {
        margin-top: 6px !important;
        color: var(--app-text-muted);
        font-weight: 600;
    }
    .app-dark-theme .app-header {
        background:
            linear-gradient(135deg, rgba(17, 24, 39, 0.98), rgba(15, 23, 42, 0.94)),
            linear-gradient(90deg, rgba(96, 165, 250, 0.10), rgba(94, 234, 212, 0.09));
        border-color: var(--app-border);
    }
    .config-panel {
        border: 1px solid var(--app-border) !important;
        border-radius: 8px !important;
        margin-bottom: 18px !important;
        background: rgba(255, 255, 255, 0.78) !important;
        box-shadow: var(--app-shadow-soft);
        overflow: hidden;
    }
    .app-dark-theme .config-panel {
        background: rgba(17, 24, 39, 0.82) !important;
    }
    .main-tabs .tab-nav {
        border-bottom: 1px solid var(--app-border);
        margin-bottom: 16px;
    }
    .main-tabs button[role="tab"] {
        border-radius: 8px 8px 0 0 !important;
        font-weight: 700 !important;
    }
    .main-tabs button[aria-selected="true"] {
        color: var(--app-primary) !important;
        border-bottom-color: var(--app-primary) !important;
    }
    .work-panel,
    .result-panel,
    .library-panel,
    .guide-panel {
        border: 1px solid var(--app-border);
        border-radius: 8px;
        padding: 16px;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: var(--app-shadow-soft);
    }
    .result-panel {
        background: rgba(255, 255, 255, 0.94);
    }
    .app-dark-theme .work-panel,
    .app-dark-theme .result-panel,
    .app-dark-theme .library-panel,
    .app-dark-theme .guide-panel {
        background: rgba(17, 24, 39, 0.88);
        border-color: var(--app-border);
    }
    .panel-heading h3 {
        margin-top: 0 !important;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--app-border);
        color: var(--app-indigo);
        font-weight: 850;
    }
    .section-panel {
        border: 1px solid var(--app-border);
        border-radius: 8px;
        padding: 16px;
        background: var(--app-surface);
    }
    label,
    .wrap label,
    .block label {
        color: var(--app-text) !important;
        font-weight: 750 !important;
    }
    input,
    textarea,
    select {
        border-radius: 8px !important;
    }
    .form,
    .block {
        border-color: var(--app-border) !important;
    }
    button {
        border-radius: 8px !important;
    }
    button.primary {
        background: linear-gradient(135deg, #2563eb, #0f766e) !important;
        border: none !important;
        box-shadow: 0 10px 20px rgba(37, 99, 235, 0.18);
    }
    button.secondary {
        border-color: var(--app-border-strong) !important;
        color: var(--app-primary) !important;
        background: var(--app-surface-muted) !important;
    }
    button:hover {
        transform: translateY(-1px);
        transition: transform 0.14s ease, box-shadow 0.14s ease;
    }
    .code-settings-row {
        align-items: end;
        padding: 10px 12px;
        margin: 10px 0 8px;
        border: 1px solid var(--app-border);
        border-radius: 8px;
        background: var(--app-surface-muted);
    }
    #code-input .cm-editor,
    #code-input .cm-content,
    #code-input .cm-gutters,
    #code-input textarea,
    #code-input pre,
    #code-input code {
        font-size: var(--code-editor-font-size) !important;
    }
    #code-input .cm-editor {
        min-height: var(--code-editor-min-height) !important;
    }
    #code-input .cm-scroller {
        min-height: var(--code-editor-min-height) !important;
    }
    #code-input {
        transition: min-height 0.2s ease;
    }
    #code-input > label,
    #code-input .label-wrap {
        border-radius: 8px 8px 0 0 !important;
    }
    #code-input .cm-editor {
        border-radius: 0 0 8px 8px;
        border-color: var(--app-border) !important;
    }
    .code-area-expanded #code-input {
        width: 100%;
    }
    .report-view .report-nav {
        border: 1px solid var(--app-border-strong);
        border-radius: 8px;
        padding: 12px 14px;
        margin: 12px 0 18px;
        background: linear-gradient(180deg, #f8fbff, #eef6ff);
    }
    .report-view .report-nav-title {
        font-weight: 700;
        margin-bottom: 6px;
        color: var(--app-indigo);
    }
    .report-view .report-nav ul {
        margin: 0;
        padding-left: 18px;
    }
    .report-view .report-nav li {
        margin: 4px 0;
    }
    .report-view .report-nav a {
        color: var(--app-primary);
        text-decoration: none;
        font-weight: 650;
    }
    .report-view .report-nav a:hover {
        text-decoration: underline;
    }
    .report-view .report-section {
        border-top: 1px solid var(--app-border);
        padding: 10px 0 14px;
        scroll-margin-top: 16px;
    }
    .report-view .report-section-summary {
        cursor: pointer;
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.35;
        color: var(--app-indigo);
        list-style-position: inside;
    }
    .report-view .report-section-summary:hover {
        color: var(--app-primary);
    }
    .report-view .report-section[open] .report-section-summary {
        margin-bottom: 10px;
    }
    .report-view a[id] {
        scroll-margin-top: 16px;
    }
    .report-view pre {
        border-radius: 8px !important;
        border: 1px solid var(--app-border);
        background: #f8fafc !important;
    }
    .report-view code {
        border-radius: 6px;
        padding: 1px 4px;
        color: #0f4f78;
        background: #eef6ff;
        font-weight: 650;
    }
    .report-view h1,
    .report-view h2,
    .report-view h3,
    .report-view h4 {
        color: var(--app-indigo);
        font-weight: 850;
    }
    .report-view strong {
        color: var(--app-primary-strong);
        font-weight: 850;
    }
    .report-view li::marker {
        color: var(--app-teal);
    }
    .report-view p,
    .report-view li {
        color: var(--app-text);
        line-height: 1.82;
    }
    .app-dark-theme .report-view pre {
        background: #0b1220 !important;
    }
    .app-dark-theme .report-view code {
        color: #bfdbfe;
        background: #172554;
    }
    .library-panel .dataframe,
    .library-panel table {
        border-radius: 8px !important;
        overflow: hidden;
    }
    .footer-note {
        color: var(--app-text-muted);
        text-align: center;
        margin-top: 20px;
    }
    footer {
        display: none !important;
    }
    """

    with gr.Blocks(
        title=GRADIO_TITLE,
    ) as demo:
        generated_variants_state = gr.State([])

        # ==================== 页头 ====================
        gr.Markdown(
            """
            # 🤖 AI 编程题讲解机器人
            ### 错解代码诊断与变式训练系统

            上传你的编程题错解代码，AI 自动完成 **结构分析 → 错误诊断 → 修复建议 → 变式训练**
            """,
            elem_classes=["app-header"],
        )

        # ==================== 配置区 ====================
        with gr.Accordion("⚙️ 配置", open=False, elem_classes=["config-panel"]):
            api_key_input = gr.Textbox(
                label="DeepSeek API Key（留空则使用内置默认DeepSeek API）",
                type="password",
                placeholder="sk-...",
            )
            theme_mode = gr.Dropdown(
                choices=["跟随系统", "浅色", "深色"],
                value="跟随系统",
                label="页面主题",
            )
            leetcode_session_input = gr.Textbox(
                label="LeetCode Session（会员题导入，可留空）",
                type="password",
                placeholder="LEETCODE_SESSION 的值，或完整 Cookie 字符串",
            )
            leetcode_csrf_input = gr.Textbox(
                label="LeetCode CSRF Token（会员题导入，可留空）",
                type="password",
                placeholder="csrftoken 的值",
            )

        # ==================== 主界面 ====================
        with gr.Tabs(selected="input", elem_classes=["main-tabs"]) as main_tabs:
            with gr.Tab("输入与诊断", id="input"):
                with gr.Row():
                    # ---- 左侧：输入区 ----
                    with gr.Column(scale=1, elem_classes=["work-panel"]):
                        gr.Markdown("### 📝 输入", elem_classes=["panel-heading"])

                        language_selector = gr.Dropdown(
                            choices=get_language_choices(),
                            value="Python3",
                            label="编程语言",
                        )

                        # 题目描述
                        problem_desc_input = gr.Textbox(
                            label="题目描述",
                            placeholder="请输入题目描述，例如：给定一个整数数组 nums 和一个目标值 target...",
                            lines=4,
                        )

                        # 代码输入
                        with gr.Row(elem_classes=["code-settings-row"]):
                            code_font_size = gr.Slider(
                                minimum=12,
                                maximum=24,
                                step=1,
                                value=14,
                                label="代码字体大小",
                                scale=3,
                            )
                            code_expand = gr.Checkbox(
                                label="放大代码区",
                                value=False,
                                scale=1,
                            )

                        code_input = gr.Code(
                            label="你的代码",
                            language=get_gradio_language("Python3"),
                            lines=12,
                            elem_id="code-input",
                        )

                        # 报错信息
                        error_input = gr.Textbox(
                            label="报错信息 / 运行结果",
                            placeholder="粘贴报错信息或运行结果...",
                            lines=3,
                        )

                        # 测试用例
                        with gr.Row():
                            test_input = gr.Textbox(
                                label="测试输入",
                                placeholder="例：nums=[2,7,11,15], target=9",
                                scale=1,
                            )
                            test_expected = gr.Textbox(
                                label="期望输出",
                                placeholder="例：[0,1]",
                                scale=1,
                            )

                        # 选项
                        gen_variants = gr.Checkbox(
                            label="生成变式训练题",
                            value=True,
                        )

                        # 按钮
                        with gr.Row():
                            diagnose_btn = gr.Button(
                                "🔍 开始诊断",
                                variant="primary",
                                size="lg",
                            )
                            explain_btn = gr.Button(
                                "📖 代码解释",
                                variant="secondary",
                            )

                    # ---- 右侧：输出区 ----
                    with gr.Column(scale=1, elem_classes=["result-panel"]):
                        gr.Markdown("### 📊 诊断结果", elem_classes=["panel-heading"])

                        status_output = gr.Markdown(
                            label="状态",
                            value="等待输入...",
                            elem_classes=["status-bar"],
                        )

                        report_output = gr.Markdown(
                            label="讲解报告",
                            value="诊断报告将在此处显示...",
                            elem_classes=["report-view"],
                        )

                        with gr.Row():
                            variant_selector = gr.Dropdown(
                                choices=[],
                                label="生成的变式题",
                                scale=3,
                            )
                            import_variant_btn = gr.Button(
                                "导入变式题",
                                variant="secondary",
                                scale=1,
                            )

            with gr.Tab("题库", id="library"):
                with gr.Column(elem_classes=["library-panel"]):
                    gr.Markdown("### 📚 LeetCode 在线题库", elem_classes=["panel-heading"])
                    with gr.Row():
                        leetcode_keyword = gr.Textbox(
                            label="关键词",
                            placeholder="例：two sum / 两数之和 / binary search",
                            scale=2,
                        )
                        leetcode_difficulty = gr.Dropdown(
                            choices=["全部", "简单", "中等", "困难"],
                            value="全部",
                            label="难度",
                            scale=1,
                        )
                    with gr.Row():
                        leetcode_search_btn = gr.Button("🔍 检索 LeetCode", variant="secondary")
                    leetcode_search_status = gr.Markdown(value="")
                    leetcode_results = gr.Dataframe(
                        headers=["编号", "标题", "难度", "标签", "Slug", "会员题"],
                        value=[],
                        label="检索结果",
                        interactive=False,
                        type="array",
                    )
                    leetcode_slug_input = gr.Textbox(
                        label="题目链接或 Slug",
                        placeholder="例：two-sum 或 https://leetcode.cn/problems/two-sum/",
                    )
                    leetcode_import_btn = gr.Button("导入题目到输入区", variant="primary")

            with gr.Tab("使用指南", id="guide"):
                with gr.Column(elem_classes=["guide-panel"]):
                    gr.Markdown(
                        """
                    ### ℹ️ 使用指南

                    1. 在“题库”中检索 LeetCode 题目，复制结果里的 Slug，或直接粘贴题目链接并导入到输入区。
                    2. 在“输入与诊断”中选择编程语言，补充错解代码、报错信息和测试用例。
                    3. 点击“开始诊断”生成结构分析、错误诊断、修复建议、运行验证和变式训练。
                    4. 诊断后可以在右侧选择生成的变式题，并点击“导入变式题”继续练习。

                    当前 Python3 支持 AST 结构分析和沙箱运行验证；其他语言会跳过 Python 专属步骤，并由大模型按所选语言给出诊断和修复代码。
                        """
                    )

        # ==================== 事件绑定 ====================
        # 诊断按钮
        diagnose_btn.click(
            fn=run_diagnosis,
            inputs=[
                code_input,
                language_selector,
                problem_desc_input,
                error_input,
                test_input,
                test_expected,
                gen_variants,
                api_key_input,
            ],
            outputs=[report_output, status_output, variant_selector, generated_variants_state],
        )

        # 代码解释按钮
        explain_btn.click(
            fn=get_code_explanation,
            inputs=[code_input, language_selector, api_key_input],
            outputs=[report_output],
        )

        # 切换语言 → 更新编辑器高亮
        language_selector.change(
            fn=apply_language_change,
            inputs=[language_selector, code_input],
            outputs=[code_input],
        )

        # 代码区显示设置
        code_font_size.change(
            fn=None,
            inputs=[code_font_size],
            outputs=None,
            js=code_font_js,
            show_progress="hidden",
        )
        code_expand.change(
            fn=None,
            inputs=[code_expand],
            outputs=None,
            js=code_expand_js,
            show_progress="hidden",
        )
        theme_mode.change(
            fn=None,
            inputs=[theme_mode],
            outputs=None,
            js=theme_mode_js,
            show_progress="hidden",
        )
        # LeetCode 在线检索
        leetcode_search_btn.click(
            fn=search_leetcode,
            inputs=[leetcode_keyword, leetcode_difficulty, leetcode_session_input, leetcode_csrf_input],
            outputs=[leetcode_results, leetcode_search_status],
        )

        # 点击检索结果中的任意单元格 → 自动填充该行 Slug
        leetcode_results.select(
            fn=fill_slug_from_result,
            inputs=[leetcode_results],
            outputs=[leetcode_slug_input],
        )

        # LeetCode 在线导入
        leetcode_import_btn.click(
            fn=load_leetcode_template_and_switch,
            inputs=[leetcode_slug_input, language_selector, leetcode_session_input, leetcode_csrf_input],
            outputs=[code_input, problem_desc_input, test_input, test_expected, status_output, main_tabs],
        )

        # 生成的变式题 → 一键导入输入区
        import_variant_btn.click(
            fn=import_generated_variant,
            inputs=[variant_selector, generated_variants_state, language_selector],
            outputs=[code_input, problem_desc_input, test_input, test_expected, status_output],
        )

        # ==================== 页脚 ====================
        gr.Markdown(
            """
            ---
            **技术栈：** DeepSeek-Coder · Python AST · 沙箱隔离执行 · Gradio

            **项目4：AI编程题讲解机器人 — 错解代码诊断与变式训练系统**
            """,
            elem_classes=["footer-note"],
        )
    launch_port = _find_available_port(GRADIO_SERVER_PORT, GRADIO_SERVER_NAME)
    if launch_port != GRADIO_SERVER_PORT:
        logger.warning(
            "端口 %s 已被占用，自动改用端口 %s。访问地址：http://%s:%s",
            GRADIO_SERVER_PORT,
            launch_port,
            GRADIO_SERVER_NAME,
            launch_port,
        )

    demo.launch(
        server_name=GRADIO_SERVER_NAME,
        server_port=launch_port,
        share=GRADIO_SHARE,
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="purple"),
        css=custom_css,
        head=custom_head,
    )


# ======================================================================
#  启动
# ======================================================================
if __name__ == "__main__":
    build_ui()
