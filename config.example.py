"""
项目配置文件示例。

首次运行时可以复制为 config.py，并通过环境变量或页面配置区域填写 API Key。
"""
import os

# ==================== 模型配置 ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-coder")
DIAGNOSIS_MODEL = os.getenv("DIAGNOSIS_MODEL", "deepseek-chat")
VARIANT_MODEL = os.getenv("VARIANT_MODEL", "deepseek-chat")

# ==================== 沙箱配置 ====================
SANDBOX_TIMEOUT = 10
SANDBOX_MAX_MEMORY = 256
SANDBOX_MAX_OUTPUT = 65536

# ==================== Gradio 配置 ====================
GRADIO_SERVER_NAME = "127.0.0.1"
GRADIO_SERVER_PORT = 7860
GRADIO_SHARE = os.getenv("GRADIO_SHARE", "false").lower() in ("1", "true", "yes", "on")
GRADIO_THEME = "soft"
GRADIO_TITLE = "AI 编程题讲解机器人"
GRADIO_DESCRIPTION = "上传错解代码，AI 自动诊断错误并生成变式训练题"

# ==================== 题库配置 ====================
PROBLEMS_DB_PATH = os.path.join(os.path.dirname(__file__), "database", "problems.json")
LEETCODE_GRAPHQL_URL = os.getenv("LEETCODE_GRAPHQL_URL", "https://leetcode.cn/graphql/")

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "app.log")

# ==================== 报告配置 ====================
REPORT_INCLUDE_AST = True
REPORT_INCLUDE_SANDBOX = True
REPORT_INCLUDE_VARIANT = True
REPORT_MAX_VARIANT_COUNT = 3
