"""
Markdown 讲解报告生成器
将诊断结果组装为结构清晰的 Markdown 格式报告
"""
from dataclasses import dataclass, field
from typing import Optional


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
        parts.append(f"# 讲解报告：{self.problem_title}\n")
        if self.project_info:
            parts.append(f"> {self.project_info}\n")

        # 按顺序收集所有已设置的章节
        sections = [
            self.ast_section,
            self.diagnosis_section,
            self.fix_section,
            self.sandbox_section,
            self.variant_section,
            *self.extra_sections,
        ]

        for sec in sections:
            if sec is None:
                continue
            parts.append(f"## {sec.title}\n")
            if sec.content.strip():
                parts.append(f"{sec.content.strip()}\n")

        report = "\n".join(parts)
        # 清理多余空行（3个以上换行压缩为2个）
        while "\n\n\n" in report:
            report = report.replace("\n\n\n", "\n\n")
        return report
