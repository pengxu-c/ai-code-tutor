"""
日志工具模块
提供统一的日志配置和管理
"""
import logging
import os
import sys


def setup_logger(
    name: str = "ai_code_tutor",
    level: str = "INFO",
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    log_file: str | None = None,
) -> logging.Logger:
    """
    创建并配置日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 日志格式字符串
        log_file: 日志文件路径（为 None 则仅输出到控制台）

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 防止重复添加 handler
    if logger.handlers:
        return logger

    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler（如果指定了日志文件）
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
