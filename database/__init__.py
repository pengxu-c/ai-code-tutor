# database 包
import json
import os
from typing import Dict, List, Optional

from .leetcode_client import LeetCodeClient

_PROBLEMS_DB_PATH = os.path.join(os.path.dirname(__file__), "problems.json")
_LEETCODE_CLIENT = LeetCodeClient()


def load_problems() -> List[Dict]:
    """加载题库"""
    if os.path.exists(_PROBLEMS_DB_PATH):
        with open(_PROBLEMS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_problem_by_title(title: str) -> Optional[Dict]:
    """根据标题获取题目"""
    problems = load_problems()
    for p in problems:
        if p.get("title") == title:
            return p
    return None


def get_problems_by_difficulty(difficulty: str) -> List[Dict]:
    """根据难度获取题目列表"""
    problems = load_problems()
    return [p for p in problems if p.get("difficulty") == difficulty]


def get_all_titles() -> List[str]:
    """获取所有题目标题"""
    return [p.get("title", "") for p in load_problems() if p.get("title")]


def get_leetcode_problem(
    slug_or_url: str,
    language_slug: str = "python3",
    leetcode_session: str = "",
    csrf_token: str = "",
) -> Dict:
    """在线获取单道 LeetCode 题目。"""
    return _LEETCODE_CLIENT.fetch_problem(
        slug_or_url,
        language_slug=language_slug,
        leetcode_session=leetcode_session,
        csrf_token=csrf_token,
    )


def search_leetcode_problems(
    keyword: str = "",
    difficulty: str = "",
    limit: int = 20,
    leetcode_session: str = "",
    csrf_token: str = "",
) -> List[Dict]:
    """在线检索 LeetCode 题目列表。"""
    return _LEETCODE_CLIENT.search(
        keyword=keyword,
        difficulty=difficulty,
        limit=limit,
        leetcode_session=leetcode_session,
        csrf_token=csrf_token,
    )
