"""Variant training helpers for generated problem imports."""

import gradio as gr

from utils.languages import get_gradio_language


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
