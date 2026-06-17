from utils.markdown_builder import MarkdownReportBuilder


def test_report_navigation_and_collapsible_sections():
    builder = MarkdownReportBuilder(problem_title="????")
    builder.set_project_info("??4", "AI????????")
    builder.add_error_diagnosis("### ????\n??", "### ????\n??")

    report = builder.build()

    assert 'class="report-nav"' in report
    assert '<details class="report-section" open>' in report
    assert 'id="section-' in report
    assert 'href="#section-' in report
    assert 'report-section-summary' in report
