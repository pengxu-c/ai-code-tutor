from ui.assets import CUSTOM_CSS, CUSTOM_HEAD


def test_custom_head_forces_light_color_scheme():
    assert 'colorScheme = "light"' in CUSTOM_HEAD
    assert "app-light-theme" in CUSTOM_HEAD


def test_ui_assets_do_not_reintroduce_dark_theme_logic():
    combined = f"{CUSTOM_HEAD}\n{CUSTOM_CSS}"

    assert "app-dark-theme" not in combined
    assert "prefers-color-scheme" not in combined
    assert "theme_mode" not in combined
    assert "body:not(.app-light-theme)" not in combined


def test_report_code_blocks_have_full_copy_enhancement():
    assert "enhanceReportCodeBlocks" in CUSTOM_HEAD
    assert "复制完整代码" in CUSTOM_HEAD
    assert 'pre.querySelector("code")' in CUSTOM_HEAD
    assert "dataset.rawCode" in CUSTOM_HEAD
    assert "normalizeReportCode" in CUSTOM_HEAD
    assert "decodeHtmlEntities" in CUSTOM_HEAD
    assert 'replace(/\\n{3,}/g, "\\n\\n")' in CUSTOM_HEAD
    assert ".report-code-copy" in CUSTOM_CSS
    assert "max-height: none" in CUSTOM_CSS
    assert "height: auto" in CUSTOM_CSS
    assert "min-height: 0" in CUSTOM_CSS
    assert "white-space: pre-wrap" in CUSTOM_CSS
    assert ".tok-keyword" in CUSTOM_CSS
    assert "button:not(.report-code-copy)" in CUSTOM_CSS
