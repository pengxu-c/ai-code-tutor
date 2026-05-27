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
) -> tuple[str, str]:
    """
    执行完整的诊断流程

    Returns:
        (markdown_report, status_message)
    """
    start_time = time.time()

    # 参数校验
    if not code.strip():
        return "", "请输入需要诊断的代码。"

    # 如果用户配置了 API Key，动态更新
    if api_key and api_key.strip():
        llm_diagnosis.api_key = api_key.strip()
        variant_generator.llm.api_key = api_key.strip()

    # 构建报告
    title = _infer_problem_title(problem_desc)
    builder = MarkdownReportBuilder(problem_title=title)
    builder.set_project_info("项目4", "AI编程题讲解机器人")

    status_parts = []

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
            builder.add_variant_problems([v["description"] for v in variants])
            status_parts.append(f"变式训练生成完成（{len(variants)} 题）")
        except Exception as e:
            logger.error(f"变式题生成异常: {e}")
            status_parts.append(f"变式题生成失败: {e}")

    # 生成报告
    report = builder.build()
    elapsed = time.time() - start_time
    status = f"诊断完成（耗时 {elapsed:.1f}s）：" + " → ".join(status_parts)

    logger.info(status)
    return report, status


# ======================================================================
#  辅助功能
# ======================================================================
def search_leetcode(keyword: str, difficulty: str) -> tuple[list[list[str]], str]:
    """在线检索 LeetCode 题目。"""
    try:
        rows = search_leetcode_problems(keyword=keyword, difficulty=difficulty, limit=20)
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


def load_leetcode_template(slug_or_url: str, language: str) -> tuple[object, str, str, str, str]:
    """从 LeetCode 在线导入题目模板。"""
    try:
        problem = get_leetcode_problem(slug_or_url, language_slug=get_leetcode_slug(language))
        examples = problem.get("examples", [])
        test_in = str(examples[0].get("input", "")) if examples else ""
        test_out = str(examples[0].get("output", "")) if examples else ""
        desc = _format_leetcode_description(problem)
        status = f"已导入 LeetCode 题目：{problem.get('title', '')}"
        if problem.get("paid_only"):
            status += "（会员题，题面可能不完整）"
        code_update = gr.update(
            value=problem.get("starter_code", ""),
            language=get_gradio_language(language),
        )
        return code_update, desc, test_in, test_out, status
    except Exception as e:
        return gr.update(language=get_gradio_language(language)), "", "", "", f"LeetCode 导入失败：{str(e)}"


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


# ======================================================================
#  Gradio 界面构建
# ======================================================================
def build_ui():
    """构建 Gradio 交互界面"""

    # 自定义 CSS
    custom_css = """
    .main-title {
        text-align: center;
        margin-bottom: 10px;
    }
    .status-bar {
        padding: 10px;
        border-radius: 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    footer {
        display: none !important;
    }
    """

    with gr.Blocks(
        title=GRADIO_TITLE,
    ) as demo:

        # ==================== 页头 ====================
        gr.Markdown(
            """
            # 🤖 AI 编程题讲解机器人
            ### 错解代码诊断与变式训练系统

            上传你的编程题错解代码，AI 自动完成 **结构分析 → 错误诊断 → 修复建议 → 变式训练**
            """
        )

        # ==================== 配置区 ====================
        with gr.Accordion("⚙️ 配置", open=False):
            api_key_input = gr.Textbox(
                label="DeepSeek API Key（留空则使用环境变量 DEEPSEEK_API_KEY）",
                type="password",
                placeholder="sk-...",
            )

        # ==================== 主界面 ====================
        with gr.Row():
            # ---- 左侧：输入区 ----
            with gr.Column(scale=1):
                gr.Markdown("### 📝 输入")

                language_selector = gr.Dropdown(
                    choices=get_language_choices(),
                    value="Python3",
                    label="编程语言",
                )

                with gr.Accordion("🌐 LeetCode 在线题库", open=False):
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
                    leetcode_search_btn = gr.Button("检索 LeetCode", variant="secondary")
                    leetcode_search_status = gr.Markdown(value="")
                    leetcode_results = gr.Dataframe(
                        headers=["编号", "标题", "难度", "标签", "Slug", "会员题"],
                        value=[],
                        label="检索结果",
                        interactive=False,
                    )
                    leetcode_slug_input = gr.Textbox(
                        label="题目链接或 Slug",
                        placeholder="例：two-sum 或 https://leetcode.cn/problems/two-sum/",
                    )
                    leetcode_import_btn = gr.Button("导入题目到输入区", variant="primary")

                # 题目描述
                problem_desc_input = gr.Textbox(
                    label="题目描述",
                    placeholder="请输入题目描述，例如：给定一个整数数组 nums 和一个目标值 target...",
                    lines=4,
                )

                # 代码输入
                code_input = gr.Code(
                    label="你的代码",
                    language=get_gradio_language("Python3"),
                    lines=12,
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
            with gr.Column(scale=1):
                gr.Markdown("### 📊 诊断结果")

                status_output = gr.Markdown(
                    label="状态",
                    value="等待输入...",
                    elem_classes=["status-bar"],
                )

                report_output = gr.Markdown(
                    label="讲解报告",
                    value="诊断报告将在此处显示...",
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
            outputs=[report_output, status_output],
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

        # LeetCode 在线检索
        leetcode_search_btn.click(
            fn=search_leetcode,
            inputs=[leetcode_keyword, leetcode_difficulty],
            outputs=[leetcode_results, leetcode_search_status],
        )

        # LeetCode 在线导入
        leetcode_import_btn.click(
            fn=load_leetcode_template,
            inputs=[leetcode_slug_input, language_selector],
            outputs=[code_input, problem_desc_input, test_input, test_expected, status_output],
        )

        # ==================== 页脚 ====================
        gr.Markdown(
            """
            ---
            **技术栈：** DeepSeek-Coder · Python AST · 沙箱隔离执行 · Gradio

            **项目4：AI编程题讲解机器人 — 错解代码诊断与变式训练系统**
            """
        )


    demo.launch(
        server_name=GRADIO_SERVER_NAME,
        server_port=GRADIO_SERVER_PORT,
        share=GRADIO_SHARE,
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="purple"),
        css=custom_css,
    )


# ======================================================================
#  启动
# ======================================================================
if __name__ == "__main__":
    build_ui()
