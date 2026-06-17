"""
Markdown 讲解报告生成器
将诊断结果组装为结构清晰的 Markdown 格式报告
"""
from dataclasses import dataclass, field
import html
import re
from typing import Optional

try:
    from markdown_it import MarkdownIt
except ImportError:  # pragma: no cover - Gradio normally provides markdown-it-py.
    MarkdownIt = None


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str = ""
    subsections: list = field(default_factory=list)


class MarkdownReportBuilder:
    """
    Markdown 格式讲解报告构建器

    用法:
        builder = MarkdownReportBuilder(problem_title="两数之和")
        builder.set_project_info("项目4", "AI编程题讲解机器人")
        builder.add_ast_analysis("函数: twoSum\\n变量: nums, target, ...")
        builder.add_error_diagnosis("问题出在...", "修复建议: ...")
        builder.add_sandbox_results([{"passed": True, ...}])
        builder.add_variant_problems(["变式题1", "变式题2"])
        report = builder.build()
    """

    def __init__(self, problem_title: str = "未知题目"):
        self.problem_title = problem_title
        self.project_info: str = ""
        self.ast_section: Optional[ReportSection] = None
        self.diagnosis_section: Optional[ReportSection] = None
        self.sandbox_section: Optional[ReportSection] = None
        self.variant_section: Optional[ReportSection] = None
        self.fix_section: Optional[ReportSection] = None
        self.extra_sections: list[ReportSection] = []
        self.enable_navigation = True
        self.enable_collapsible_sections = True
        self._markdown = MarkdownIt("commonmark", {"html": True}) if MarkdownIt else None

    # ---------- 设置项目信息 ----------
    def set_project_info(self, project_id: str, project_name: str):
        self.project_info = f"{project_id}：{project_name}"
        return self

    # ---------- AST 分析 ----------
    def add_ast_analysis(self, analysis_text: str):
        self.ast_section = ReportSection(
            title="一、代码结构分析（AST）",
            content=analysis_text,
        )
        return self

    # ---------- 错误诊断 ----------
    def add_error_diagnosis(self, error_analysis: str, fix_suggestion: str):
        self.diagnosis_section = ReportSection(
            title="二、错误诊断",
            content=error_analysis,
        )
        self.fix_section = ReportSection(
            title="三、修复建议",
            content=fix_suggestion,
        )
        return self

    # ---------- 沙箱运行 ----------
    def add_sandbox_results(self, results: list[dict], skipped_reason: str = ""):
        if not results:
            self.sandbox_section = ReportSection(
                title="四、运行验证",
                content=skipped_reason or "未执行沙箱测试。",
            )
            return self

        lines = []
        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        lines.append(f"**测试结果：{passed}/{total} 通过**\n")

        for i, r in enumerate(results, 1):
            status = "✅ 通过" if r.get("passed") else "❌ 未通过"
            lines.append(f"### 测试用例 {i} {status}")
            lines.append(f"- **输入：** `{r.get('input', '')}`")
            lines.append(f"- **预期输出：** `{r.get('expected', '')}`")
            lines.append(f"- **实际输出：** `{r.get('actual', '')}`")
            if r.get("error"):
                lines.append(f"- **错误信息：**\n```\n{r['error']}\n```")
            lines.append("")

        self.sandbox_section = ReportSection(
            title="四、运行验证（沙箱）",
            content="\n".join(lines),
        )
        return self

    # ---------- 变式训练 ----------
    def add_variant_problems(self, variants: list[str]):
        if not variants:
            return self

        lines = []
        for i, v in enumerate(variants, 1):
            lines.append(f"### 变式题 {i}\n{v}\n")

        self.variant_section = ReportSection(
            title="五、变式训练",
            content="\n".join(lines),
        )
        return self

    # ---------- 自定义章节 ----------
    def add_custom_section(self, title: str, content: str):
        self.extra_sections.append(ReportSection(title=title, content=content))
        return self

    # ---------- 构建最终报告 ----------
    def build(self) -> str:
        """组装所有章节，生成完整的 Markdown 报告"""
        parts = []

        # 封面
        parts.append('<a id="report-top"></a>')
        parts.append(f"# 讲解报告：{self.problem_title}\n")
        if self.project_info:
            parts.append(f"> {self.project_info}\n")

        # 按顺序收集所有已设置的章节
        sections = self._collect_sections()

        if self.enable_navigation and sections:
            parts.append(self._build_navigation(sections))

        for sec in sections:
            if sec is None:
                continue
            anchor = self._section_anchor(sec.title)
            content = self._add_subsection_anchors(sec.content.strip(), anchor)
            if self.enable_collapsible_sections:
                parts.append(self._build_collapsible_section(sec.title, self._render_markdown(content), anchor))
            else:
                parts.append(f'<a id="{anchor}"></a>')
                parts.append(f"## {sec.title}\n")
                if content:
                    parts.append(f"{content}\n")

        report = "\n".join(parts)
        # 清理多余空行（3个以上换行压缩为2个）
        while "\n\n\n" in report:
            report = report.replace("\n\n\n", "\n\n")
        return report

    def _collect_sections(self) -> list[ReportSection]:
        """按报告展示顺序收集已设置的章节。"""
        return [
            sec
            for sec in [
                self.ast_section,
                self.diagnosis_section,
                self.fix_section,
                self.sandbox_section,
                self.variant_section,
                *self.extra_sections,
            ]
            if sec is not None
        ]

    def _build_navigation(self, sections: list[ReportSection]) -> str:
        """生成报告目录，点击标题可跳转到对应章节。"""
        lines = [
            '<nav class="report-nav">',
            '<div class="report-nav-title">报告导航</div>',
            '<ul>',
            '<li><a href="#report-top">讲解报告</a></li>',
        ]
        for sec in sections:
            section_anchor = self._section_anchor(sec.title)
            lines.append(f'<li><a href="#{section_anchor}">{html.escape(sec.title)}</a>')
            subsections = self._extract_subsections(sec.content, section_anchor)
            if subsections:
                lines.append('<ul>')
                for title, anchor in subsections:
                    lines.append(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>')
                lines.append('</ul>')
            lines.append('</li>')
        lines.extend(['</ul>', '</nav>'])
        return "\n".join(lines)

    def _build_collapsible_section(self, title: str, content: str, anchor: str) -> str:
        """用 HTML details/summary 包装一级章节，实现收起和展开。"""
        lines = [
            f'<a id="{anchor}"></a>',
            '<details class="report-section" open>',
            f'<summary class="report-section-summary">{html.escape(title)}</summary>',
            "",
        ]
        if content:
            lines.append(content)
            lines.append("")
        lines.append("</details>")
        return "\n".join(lines)

    def _extract_subsections(self, content: str, section_anchor: str) -> list[tuple[str, str]]:
        """提取章节内容中的三级标题，用作目录的二级导航。"""
        subsections = []
        seen: set[str] = set()
        for match in re.finditer(r"^###\s+(.+)$", content or "", flags=re.MULTILINE):
            title = match.group(1).strip()
            if not title:
                continue
            anchor = self._unique_anchor(f"{section_anchor}-{self._slugify(title)}", seen)
            subsections.append((title, anchor))
        return subsections

    def _add_subsection_anchors(self, content: str, section_anchor: str) -> str:
        """在三级标题前插入锚点，供目录跳转。"""
        if not content:
            return ""

        seen: set[str] = set()

        def replace(match: re.Match) -> str:
            title = match.group(1).strip()
            anchor = self._unique_anchor(f"{section_anchor}-{self._slugify(title)}", seen)
            return f'<a id="{anchor}"></a>\n### {title}'

        return re.sub(r"^###\s+(.+)$", replace, content, flags=re.MULTILINE)

    def _section_anchor(self, title: str) -> str:
        return f"section-{self._slugify(title)}"

    def _slugify(self, text: str) -> str:
        """把中文/英文标题转换成稳定的页面锚点。"""
        text = re.sub(r"<[^>]+>", "", text or "")
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
        return "-".join(tokens) or "part"

    def _unique_anchor(self, anchor: str, seen: set[str]) -> str:
        if anchor not in seen:
            seen.add(anchor)
            return anchor

        suffix = 2
        while f"{anchor}-{suffix}" in seen:
            suffix += 1
        unique = f"{anchor}-{suffix}"
        seen.add(unique)
        return unique

    def _render_markdown(self, content: str) -> str:
        if not content or not self._markdown:
            return content
        return self._markdown.render(content).strip()
