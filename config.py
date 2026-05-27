"""
项目配置文件
AI编程题讲解机器人：错解代码诊断与变式训练系统
"""
import os

# ==================== 模型配置 ====================
# DeepSeek API 配置（建议通过环境变量 DEEPSEEK_API_KEY 或界面输入）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-coder")
# 用于诊断的模型（可使用更强大的通用模型）
DIAGNOSIS_MODEL = os.getenv("DIAGNOSIS_MODEL", "deepseek-chat")
# 用于变式题生成的模型
VARIANT_MODEL = os.getenv("VARIANT_MODEL", "deepseek-chat")

# ==================== 沙箱配置 ====================
SANDBOX_TIMEOUT = 10          # 代码执行超时时间（秒）
SANDBOX_MAX_MEMORY = 256      # 最大内存限制（MB）
SANDBOX_MAX_OUTPUT = 65536    # 最大输出长度（字符）

# ==================== Gradio 配置 ====================
GRADIO_SERVER_NAME = "127.0.0.1"
GRADIO_SERVER_PORT = 7860
GRADIO_SHARE = True          # 是否创建公开分享链接
GRADIO_THEME = "soft"
GRADIO_TITLE = "AI 编程题讲解机器人"
GRADIO_DESCRIPTION = "上传错解代码，AI 自动诊断错误并生成变式训练题"

# ==================== 题库配置 ====================
# join路径拼接：数据库文件路径
PROBLEMS_DB_PATH = os.path.join(os.path.dirname(__file__), "database", "problems.json")

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "app.log")

# ==================== 报告配置 ====================
REPORT_INCLUDE_AST = True          # 报告中是否包含 AST 分析
REPORT_INCLUDE_SANDBOX = True      # 报告中是否包含沙箱运行结果
REPORT_INCLUDE_VARIANT = True      # 报告中是否包含变式题
REPORT_MAX_VARIANT_COUNT = 3       # 生成变式题的最大数量
