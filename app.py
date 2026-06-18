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
import socket

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr

from config import (
    GRADIO_SERVER_NAME,
    GRADIO_SERVER_PORT,
    GRADIO_SHARE,
    GRADIO_THEME,
    GRADIO_TITLE,
)
from utils.logger import setup_logger
from services.diagnosis_service import get_code_explanation, run_diagnosis
from services.history_service import list_report_history, load_report_history
from services.leetcode_service import (
    apply_language_change,
    fill_slug_from_result,
    load_leetcode_template_and_switch,
    search_leetcode,
)
from services.variant_service import import_generated_variant
from ui.assets import CODE_EXPAND_JS, CODE_FONT_JS, CUSTOM_CSS, CUSTOM_HEAD
from utils.languages import (
    get_gradio_language,
    get_language_choices,
)

# ==================== 初始化 ====================
logger = setup_logger(__name__)


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

    with gr.Blocks(
        title=GRADIO_TITLE,
    ) as demo:
        generated_variants_state = gr.State([])

        gr.Image(
            value=os.path.join(os.path.dirname(__file__), "picture", "月.png"),
            elem_classes=["app-bg-holder"],
            show_label=False,
        )

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
                                label="字体大小",
                                scale=3,
                                elem_id="code-font-size",
                            )
                            code_expand = gr.Checkbox(
                                label="放大代码区",
                                value=False,
                                scale=1,
                                elem_id="code-expand-toggle",
                            )

                        with gr.Column(elem_classes=["code-editor-shell"]):
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

                        report_download = gr.File(
                            label="下载报告",
                            value=None,
                            interactive=False,
                        )

                        with gr.Row():
                            history_selector = gr.Dropdown(
                                choices=list_report_history(),
                                label="最近诊断历史",
                                scale=3,
                            )
                            open_history_btn = gr.Button(
                                "打开历史",
                                variant="secondary",
                                scale=1,
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

                    注：当前 Python3 支持 AST 结构分析和沙箱运行验证；其他语言会跳过 Python 专属步骤，并由大模型按所选语言给出诊断和修复代码。
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
            outputs=[
                report_output,
                status_output,
                variant_selector,
                generated_variants_state,
                report_download,
                history_selector,
            ],
        )

        # 代码解释按钮
        explain_btn.click(
            fn=get_code_explanation,
            inputs=[code_input, language_selector, api_key_input],
            outputs=[report_output],
        )

        open_history_btn.click(
            fn=load_report_history,
            inputs=[history_selector],
            outputs=[report_output, report_download],
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
            js=CODE_FONT_JS,
            show_progress="hidden",
        )
        code_expand.change(
            fn=None,
            inputs=[code_expand],
            outputs=None,
            js=CODE_EXPAND_JS,
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
        css=CUSTOM_CSS,
        head=CUSTOM_HEAD,
    )


# ======================================================================
#  启动
# ======================================================================
if __name__ == "__main__":
    build_ui()
