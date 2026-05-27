"""
变式题生成模块
基于 LLM 和题库，为编程题生成同类型的变式训练题
"""
import json
import random
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.llm_diagnosis import LLMDiagnosis
from database import load_problems, get_problem_by_title
from config import REPORT_MAX_VARIANT_COUNT


class VariantGenerator:
    """
    变式题生成器

    支持两种模式：
    1. LLM 模式：使用大语言模型生成全新变式题（需要 API Key）
    2. 题库模式：从本地题库中筛选同类题目作为变式题（离线可用）

    用法:
        gen = VariantGenerator()
        variants = gen.generate(problem_desc="两数之和", tags=["数组", "哈希表"])
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        prefer_llm: bool = True,
    ):
        self.llm = LLMDiagnosis(api_key=api_key, base_url=base_url)
        self.prefer_llm = prefer_llm

    def generate(
        self,
        problem_desc: str,
        code: str = "",
        tags: Optional[list[str]] = None,
        difficulty: Optional[str] = None,
        count: int = REPORT_MAX_VARIANT_COUNT,
    ) -> list[dict]:
        """
        生成变式题

        Args:
            problem_desc: 原题描述
            code: 原题参考代码
            tags: 题目标签（如 ["数组", "哈希表", "双指针"]）
            difficulty: 题目难度（简单/中等/困难）
            count: 生成数量

        Returns:
            变式题列表，每项包含 {"title", "description", "difficulty", "hint"}
        """
        variants = []

        # 策略1：尝试从本地题库中获取同类题目
        db_variants = self._get_from_database(tags=tags, difficulty=difficulty, count=count)
        variants.extend(db_variants)

        # 如果题库中已有足够的变式题，且不强制使用 LLM
        if len(variants) >= count and not self.prefer_llm:
            return variants[:count]

        # 策略2：使用 LLM 生成更多变式题
        remaining = count - len(variants)
        if remaining > 0 and self.prefer_llm:
            try:
                llm_variants = self.llm.generate_variants(
                    problem_desc=problem_desc,
                    code=code,
                    count=remaining,
                )
                for v_text in llm_variants:
                    variants.append({
                        "title": self._extract_title(v_text),
                        "description": v_text,
                        "difficulty": difficulty or "中等",
                        "hint": "",
                        "source": "llm",
                    })
            except Exception:
                pass  # LLM 生成失败时忽略，使用题库结果

        return variants[:count]

    def _get_from_database(
        self,
        tags: Optional[list[str]] = None,
        difficulty: Optional[str] = None,
        count: int = 3,
    ) -> list[dict]:
        """从题库中获取匹配的题目"""
        problems = load_problems()

        # 如果提供了标签，按标签匹配
        if tags:
            scored = []
            for p in problems:
                p_tags = set(p.get("tags", []))
                overlap = len(p_tags & set(tags))
                if overlap > 0:
                    scored.append((overlap, p))
            scored.sort(key=lambda x: -x[0])
            problems = [p for _, p in scored]

        # 按难度筛选
        if difficulty:
            filtered = [p for p in problems if p.get("difficulty") == difficulty]
            if filtered:
                problems = filtered

        # 随机选取（如果题目太多）
        if len(problems) > count:
            problems = random.sample(problems, count)

        return [
            {
                "title": p.get("title", "未知"),
                "description": self._format_problem_description(p),
                "difficulty": p.get("difficulty", "中等"),
                "hint": p.get("hint", ""),
                "source": "database",
            }
            for p in problems
        ]

    @staticmethod
    def _extract_title(variant_text: str) -> str:
        """从 LLM 生成的变式题文本中提取标题"""
        for line in variant_text.split("\n"):
            line = line.strip()
            if line.startswith("**题目名称") or line.startswith("题目名称"):
                # 提取 **题目名称：** xxx
                if "：" in line:
                    return line.split("：", 1)[1].strip().rstrip("*")
                elif ":" in line:
                    return line.split(":", 1)[1].strip().rstrip("*")
        return "变式练习"

    @staticmethod
    def _format_problem_description(problem: dict) -> str:
        """格式化题库中的题目为 Markdown 描述"""
        parts = []
        parts.append(f"**{problem.get('title', '')}**")
        parts.append(f"难度：{problem.get('difficulty', '未知')}")

        desc = problem.get("description", "")
        if desc:
            parts.append(f"\n{desc}")

        examples = problem.get("examples", [])
        if examples:
            parts.append("\n**示例：**")
            for i, ex in enumerate(examples, 1):
                parts.append(f"- 输入：`{ex.get('input', '')}`")
                parts.append(f"- 输出：`{ex.get('output', '')}`")

        constraints = problem.get("constraints", [])
        if constraints:
            parts.append("\n**限制条件：**")
            for c in constraints:
                parts.append(f"- {c}")

        hint = problem.get("hint", "")
        if hint:
            parts.append(f"\n**提示：** {hint}")

        return "\n".join(parts)
