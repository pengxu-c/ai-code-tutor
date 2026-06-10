"""LeetCode search and import helpers for the Gradio UI."""

import re

import gradio as gr

from database import get_leetcode_problem, search_leetcode_problems
from database.leetcode_client import LeetCodeClient
from utils.languages import get_gradio_language, get_leetcode_slug


def normalize_leetcode_slug(value: str) -> str:
    """Normalize a LeetCode slug or problem URL for tests and UI helpers."""
    return LeetCodeClient.normalize_slug(value)


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


def load_leetcode_template(
    slug_or_url: str,
    language: str,
    leetcode_session: str = "",
    leetcode_csrf_token: str = "",
) -> tuple[object, str, str, str, str]:
    """从 LeetCode 在线导入题目模板。"""
    if not normalize_leetcode_slug(slug_or_url):
        return (
            gr.update(language=get_gradio_language(language)),
            "",
            "",
            "",
            "LeetCode 导入失败：请输入有效的题目 slug 或题目链接，例如 two-sum。",
        )

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
