"""Frontend CSS and JavaScript assets for the Gradio UI."""

CODE_FONT_JS = """    (fontSize) => {
        const size = Number(fontSize) || 14;
        document.documentElement.style.setProperty("--code-editor-font-size", `${size}px`);
    }
"""

CODE_EXPAND_JS = """    (expanded) => {
        const height = expanded ? "560px" : "300px";
        document.documentElement.style.setProperty("--code-editor-min-height", height);
        document.body.classList.toggle("code-area-expanded", Boolean(expanded));
    }
"""

CUSTOM_HEAD = """<script>
(() => {
    const applyLightTheme = () => {
        const targets = [
            document.documentElement,
            document.body,
            ...document.querySelectorAll(".gradio-container")
        ].filter(Boolean);
        for (const target of targets) {
            target.classList.add("app-light-theme");
        }
        document.documentElement.style.colorScheme = "light";
    };
    const copyText = async (text) => {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
            return;
        }

        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        textarea.style.top = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
    };
    const escapeHtml = (value) => value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    const decodeHtmlEntities = (value) => {
        const textarea = document.createElement("textarea");
        textarea.innerHTML = value;
        return textarea.value;
    };
    const normalizeReportCode = (source) => decodeHtmlEntities(source)
        .replace(/\\r\\n/g, "\\n")
        .replace(/[ \\t]+\\n/g, "\\n")
        .replace(/\\n{3,}/g, "\\n\\n")
        .replace(/[ \\t]+$/g, "")
        .replace(/\\n+$/g, "");
    const codeKeywords = new Set([
        "and", "as", "assert", "async", "await", "break", "case", "catch", "class",
        "const", "continue", "def", "default", "del", "do", "elif", "else", "enum",
        "except", "export", "extends", "false", "False", "finally", "for", "from",
        "function", "if", "import", "in", "interface", "is", "lambda", "let", "new",
        "None", "nonlocal", "not", "null", "or", "pass", "private", "protected",
        "public", "raise", "return", "static", "struct", "switch", "this", "throw",
        "true", "True", "try", "typedef", "var", "void", "while", "with", "yield"
    ]);
    const codeBuiltins = new Set([
        "append", "bool", "dict", "enumerate", "float", "int", "len", "list", "map",
        "max", "min", "pop", "print", "range", "set", "sort", "str", "sum", "vector"
    ]);
    const highlightCode = (source) => {
        const highlightLine = (line) => {
            let html = "";
            let index = 0;
            while (index < line.length) {
                const rest = line.slice(index);
                const char = line[index];

                if (char === "#") {
                    html += `<span class="tok-comment">${escapeHtml(rest)}</span>`;
                    break;
                }

                if (char === '"' || char === "'") {
                    const quote = char;
                    let end = index + 1;
                    while (end < line.length) {
                        if (line[end] === "\\\\") {
                            end += 2;
                            continue;
                        }
                        if (line[end] === quote) {
                            end += 1;
                            break;
                        }
                        end += 1;
                    }
                    html += `<span class="tok-string">${escapeHtml(line.slice(index, end))}</span>`;
                    index = end;
                    continue;
                }

                const numberMatch = rest.match(/^\\b\\d+(?:\\.\\d+)?\\b/);
                if (numberMatch) {
                    html += `<span class="tok-number">${numberMatch[0]}</span>`;
                    index += numberMatch[0].length;
                    continue;
                }

                const wordMatch = rest.match(/^[A-Za-z_]\\w*/);
                if (wordMatch) {
                    const word = wordMatch[0];
                    if (codeKeywords.has(word)) {
                        html += `<span class="tok-keyword">${word}</span>`;
                    } else if (codeBuiltins.has(word)) {
                        html += `<span class="tok-builtin">${word}</span>`;
                    } else if (/^[A-Z][A-Za-z0-9_]*$/.test(word)) {
                        html += `<span class="tok-type">${word}</span>`;
                    } else {
                        html += escapeHtml(word);
                    }
                    index += word.length;
                    continue;
                }

                html += escapeHtml(char);
                index += 1;
            }
            return html;
        };
        return source.split("\\n").map(highlightLine).join("\\n");
    };
    const enhanceReportCodeBlocks = () => {
        for (const pre of document.querySelectorAll(".report-view pre")) {
            if (pre.dataset.reportCodeEnhanced === "true") {
                continue;
            }
            pre.dataset.reportCodeEnhanced = "true";
            pre.classList.add("report-code-block");
            const codeNode = pre.querySelector("code") || pre;
            const rawCode = normalizeReportCode(codeNode.textContent);
            if (codeNode instanceof HTMLElement && codeNode.dataset.reportHighlighted !== "true") {
                codeNode.dataset.rawCode = rawCode;
                codeNode.dataset.reportHighlighted = "true";
                codeNode.innerHTML = highlightCode(rawCode);
            }

            const button = document.createElement("button");
            button.type = "button";
            button.className = "report-code-copy";
            button.textContent = "复制";
            button.title = "复制完整代码";
            button.setAttribute("aria-label", "复制完整代码");
            button.addEventListener("click", async (event) => {
                event.preventDefault();
                event.stopPropagation();

                const code = pre.querySelector("code") || pre;
                const text = code.dataset.rawCode || normalizeReportCode(code.textContent);
                try {
                    await copyText(text);
                    button.textContent = "已复制";
                    button.classList.add("is-copied");
                } catch (error) {
                    button.textContent = "复制失败";
                    button.classList.add("is-error");
                }
                window.setTimeout(() => {
                    button.textContent = "复制";
                    button.classList.remove("is-copied", "is-error");
                }, 1400);
            });
            pre.appendChild(button);
        }
    };
    const applyEnhancements = () => {
        applyLightTheme();
        enhanceReportCodeBlocks();
    };
    applyLightTheme();
    enhanceReportCodeBlocks();
    document.addEventListener("DOMContentLoaded", applyEnhancements);
    setTimeout(applyEnhancements, 50);
    setTimeout(applyEnhancements, 250);
    setTimeout(applyEnhancements, 1000);
    new MutationObserver(applyEnhancements).observe(document.documentElement, { childList: true, subtree: true });
})();
</script>
"""

CUSTOM_CSS = """    :root {
        --code-editor-font-size: 14px;
        --code-editor-min-height: 300px;
        --app-bg: #f4f7fb;
        --app-bg-soft: #eef6f6;
        --app-surface: #ffffff;
        --app-surface-muted: #f8fafc;
        --app-border: #dbe3ee;
        --app-border-strong: #bfd4ef;
        --app-text: #102033;
        --app-text-muted: #5b6b7f;
        --app-primary: #2563eb;
        --app-primary-strong: #1d4ed8;
        --app-indigo: #4338ca;
        --app-teal: #0f766e;
        --app-amber: #b45309;
        --app-rose: #be123c;
        --app-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
        --app-shadow-soft: 0 10px 26px rgba(15, 23, 42, 0.06);
        --app-font-sans: "Inter", "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
        --app-font-mono: Consolas, "Cascadia Code", "JetBrains Mono", "Fira Code", "SFMono-Regular", "Liberation Mono", monospace;
    }
    body {
        background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 28rem),
            linear-gradient(180deg, #f8fbff 0%, var(--app-bg) 46%, #eef2f7 100%) !important;
        min-height: 100vh;
        color: var(--app-text);
        font-family: var(--app-font-sans);
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
    }
    .app-bg-holder {
        all: unset !important;
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    .app-bg-holder > div,
    .app-bg-holder > div > div,
    .app-bg-holder > div > div > div,
    .app-bg-holder img {
        all: unset !important;
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    .app-bg-holder img {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        object-fit: cover !important;
        z-index: 0 !important;
        pointer-events: none !important;
        display: block !important;
    }
    .gradio-container,
    .gradio-container * {
        font-family: var(--app-font-sans);
    }
    .gradio-container .absolute {
        display: none !important;
    }
    code,
    pre,
    .cm-editor,
    .cm-editor *,
    .cm-content,
    .cm-content *,
    .cm-line,
    .cm-line *,
    .cm-gutters,
    .cm-gutters * {
        font-family: var(--app-font-mono) !important;
    }
    .main-title {
        text-align: center;
        margin-bottom: 10px;
    }
    .app-light-theme,
    .app-light-theme .gradio-container {
        color-scheme: light;
        --body-background-fill: #f8fafc;
        --body-text-color: #0f172a;
        --block-background-fill: #ffffff;
        --block-border-color: #e5e7eb;
        --input-background-fill: #ffffff;
        --input-border-color: #d1d5db;
        --button-secondary-background-fill: #f8fafc;
    }
    .status-bar {
        padding: 14px 16px;
        border-radius: 8px;
        background:
            linear-gradient(135deg, rgba(29, 78, 216, 0.96) 0%, rgba(15, 118, 110, 0.98) 100%),
            #1d4ed8;
        color: #ffffff !important;
        box-shadow: var(--app-shadow-soft);
        font-weight: 750;
        letter-spacing: 0;
        text-shadow: 0 1px 1px rgba(15, 23, 42, 0.28);
    }
    .status-bar,
    .status-bar *,
    .status-bar p,
    .status-bar span,
    .status-bar strong,
    .status-bar em,
    .status-bar a {
        color: #ffffff !important;
    }
    .status-bar p {
        margin: 0 !important;
        font-size: 1.03rem;
        line-height: 1.6;
    }
    .gradio-container {
        max-width: 1680px !important;
        padding: 24px !important;
        background: transparent !important;
    }
    .app-header {
        border: 1px solid rgba(191, 212, 239, 0.78);
        border-radius: 8px;
        padding: 22px 26px 20px;
        margin-bottom: 18px;
        background:
            linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.90)),
            linear-gradient(90deg, rgba(37, 99, 235, 0.08), rgba(15, 118, 110, 0.10));
        box-shadow: var(--app-shadow);
    }
    .app-header h1 {
        margin: 0 0 6px !important;
        color: var(--app-primary-strong);
        font-size: clamp(2rem, 3.2vw, 3rem);
        font-weight: 900;
        letter-spacing: 0;
    }
    .app-header h3,
    .app-header p {
        margin-top: 6px !important;
        color: var(--app-text-muted);
        font-weight: 600;
    }
    .config-panel {
        border: 1px solid var(--app-border) !important;
        border-radius: 8px !important;
        margin-bottom: 18px !important;
        background: rgba(255, 255, 255, 0.78) !important;
        box-shadow: var(--app-shadow-soft);
        overflow: hidden;
    }
    .main-tabs .tab-nav {
        border-bottom: 1px solid var(--app-border);
        margin-bottom: 16px;
    }
    .main-tabs button[role="tab"] {
        border-radius: 8px 8px 0 0 !important;
        font-weight: 700 !important;
    }
    .main-tabs button[aria-selected="true"] {
        color: var(--app-primary) !important;
        border-bottom-color: var(--app-primary) !important;
    }
    .work-panel,
    .result-panel,
    .library-panel,
    .guide-panel {
        border: 1px solid var(--app-border);
        border-radius: 8px;
        padding: 16px;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: var(--app-shadow-soft);
    }
    .result-panel {
        background: rgba(255, 255, 255, 0.94);
    }
    .panel-heading h3 {
        margin-top: 0 !important;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--app-border);
        color: var(--app-indigo);
        font-weight: 850;
    }
    .section-panel {
        border: 1px solid var(--app-border);
        border-radius: 8px;
        padding: 16px;
        background: var(--app-surface);
    }
    label,
    .wrap label,
    .block label {
        color: var(--app-text) !important;
        font-weight: 750 !important;
    }
    input,
    textarea,
    select {
        border-radius: 8px !important;
    }
    .form,
    .block {
        border-color: var(--app-border) !important;
    }
    button {
        border-radius: 8px !important;
    }
    button.primary {
        background: linear-gradient(135deg, #2563eb, #0f766e) !important;
        border: none !important;
        box-shadow: 0 10px 20px rgba(37, 99, 235, 0.18);
    }
    button.secondary {
        border-color: var(--app-border-strong) !important;
        color: var(--app-primary) !important;
        background: var(--app-surface-muted) !important;
    }
    button:hover {
        transform: translateY(-1px);
        transition: transform 0.14s ease, box-shadow 0.14s ease;
    }
    .code-settings-row {
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        margin: 12px 0 10px;
        border: 1px solid var(--app-border-strong);
        border-radius: 8px;
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(248, 250, 252, 0.92)),
            var(--app-surface-muted);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
    }
    #code-font-size {
        min-width: 260px;
    }
    #code-font-size,
    #code-expand-toggle {
        margin: 0 !important;
    }
    #code-font-size label,
    #code-expand-toggle label {
        font-size: 0.92rem !important;
        color: var(--app-primary-strong) !important;
        font-weight: 800 !important;
    }
    #code-font-size .wrap,
    #code-font-size .container,
    #code-expand-toggle .wrap,
    #code-expand-toggle .container {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    #code-font-size input[type="number"] {
        max-width: 76px;
        text-align: center;
        font-weight: 750;
        color: var(--app-text);
        background: var(--app-surface) !important;
        border: 1px solid var(--app-border-strong) !important;
        border-radius: 8px !important;
    }
    #code-font-size button {
        box-shadow: none !important;
    }
    #code-expand-toggle {
        max-width: 180px;
        padding: 7px 10px !important;
        border: 1px solid var(--app-border);
        border-radius: 8px;
        background: var(--app-surface);
    }
    #code-expand-toggle label {
        color: var(--app-text) !important;
    }
    .code-editor-shell {
        margin-top: 12px;
        border: 1px solid var(--app-border-strong);
        border-radius: 8px;
        padding: 10px;
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.96)),
            var(--app-surface);
        box-shadow: var(--app-shadow-soft);
    }
    #code-input .cm-editor,
    #code-input .cm-editor *,
    #code-input .cm-content,
    #code-input .cm-content *,
    #code-input .cm-line,
    #code-input .cm-line *,
    #code-input .cm-gutters,
    #code-input .cm-gutters *,
    #code-input textarea,
    #code-input pre,
    #code-input pre *,
    #code-input code {
        font-size: var(--code-editor-font-size) !important;
        font-family: Consolas, "Cascadia Code", "JetBrains Mono", "Fira Code", "SFMono-Regular", "Liberation Mono", monospace !important;
    }
    #code-input .cm-editor {
        min-height: var(--code-editor-min-height) !important;
    }
    #code-input .cm-scroller {
        min-height: var(--code-editor-min-height) !important;
    }
    #code-input {
        --font-mono: Consolas, "Cascadia Code", "JetBrains Mono", "Fira Code", "SFMono-Regular", "Liberation Mono", monospace;
        --mono-font: Consolas, "Cascadia Code", "JetBrains Mono", "Fira Code", "SFMono-Regular", "Liberation Mono", monospace;
        transition: min-height 0.2s ease;
        margin: 0 !important;
        border-radius: 8px !important;
        overflow: hidden;
    }
    #code-input > label,
    #code-input .label-wrap {
        border-radius: 8px 8px 0 0 !important;
        background: linear-gradient(90deg, #dbeafe, #e0f2fe) !important;
        color: #0f172a !important;
        font-weight: 850 !important;
        padding: 8px 10px !important;
        border: 1px solid var(--app-border) !important;
        border-bottom: none !important;
    }
    #code-input .cm-editor {
        border-radius: 0 0 8px 8px;
        border-color: var(--app-border) !important;
        background: #ffffff !important;
        outline: none !important;
    }
    #code-input .cm-gutters {
        background: #f8fafc !important;
        border-right: 1px solid var(--app-border) !important;
        color: #8a9ab0 !important;
    }
    .code-area-expanded #code-input {
        width: 100%;
    }
    .report-view .report-nav {
        border: 1px solid var(--app-border-strong);
        border-radius: 8px;
        padding: 12px 14px;
        margin: 12px 0 18px;
        background: linear-gradient(180deg, #f8fbff, #eef6ff);
    }
    .report-view .report-nav-title {
        font-weight: 700;
        margin-bottom: 6px;
        color: var(--app-indigo);
    }
    .report-view .report-nav ul {
        margin: 0;
        padding-left: 18px;
    }
    .report-view .report-nav li {
        margin: 4px 0;
    }
    .report-view .report-nav a {
        color: var(--app-primary);
        text-decoration: none;
        font-weight: 650;
    }
    .report-view .report-nav a:hover {
        text-decoration: underline;
    }
    .report-view .report-section {
        border-top: 1px solid var(--app-border);
        padding: 10px 0 14px;
        scroll-margin-top: 16px;
    }
    .report-view .report-section-summary {
        cursor: pointer;
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.35;
        color: var(--app-indigo);
        list-style-position: inside;
    }
    .report-view .report-section-summary:hover {
        color: var(--app-primary);
    }
    .report-view .report-section[open] .report-section-summary {
        margin-bottom: 10px;
    }
    .report-view a[id] {
        scroll-margin-top: 16px;
    }
    .report-view pre,
    .report-view .report-code-block {
        position: relative;
        margin: 14px 0 18px !important;
        padding: 18px 58px 18px 20px !important;
        border-radius: 8px !important;
        border: 1px solid #c9d8ea !important;
        background:
            linear-gradient(180deg, #ffffff 0%, #f7fbff 100%) !important;
        box-shadow:
            inset 4px 0 0 rgba(37, 99, 235, 0.24),
            0 12px 28px rgba(15, 23, 42, 0.08);
        min-height: 0 !important;
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
        overflow-x: hidden !important;
        white-space: pre-wrap !important;
        word-break: break-word;
        overflow-wrap: anywhere;
        color: #172033 !important;
    }
    .report-view pre code,
    .report-view .report-code-block code {
        display: block;
        padding: 0 !important;
        border-radius: 0 !important;
        background: transparent !important;
        color: #172033 !important;
        font-family: var(--app-font-mono) !important;
        font-size: 0.94rem;
        font-weight: 650;
        line-height: 1.72;
        min-height: 0 !important;
        height: auto !important;
        white-space: pre-wrap !important;
        word-break: break-word;
        overflow-wrap: anywhere;
        tab-size: 4;
    }
    .report-view .tok-keyword {
        color: #7c3aed;
        font-weight: 800;
    }
    .report-view .tok-string {
        color: #047857;
    }
    .report-view .tok-number {
        color: #b45309;
        font-weight: 750;
    }
    .report-view .tok-comment {
        color: #64748b;
        font-style: italic;
        font-weight: 600;
    }
    .report-view .tok-builtin {
        color: #0369a1;
        font-weight: 760;
    }
    .report-view .tok-type {
        color: #be123c;
        font-weight: 800;
    }
    .report-view pre button:not(.report-code-copy),
    .report-view .report-code-block button:not(.report-code-copy),
    .report-view pre [aria-label*="copy" i]:not(.report-code-copy),
    .report-view pre [title*="copy" i]:not(.report-code-copy) {
        display: none !important;
    }
    .report-view .report-code-copy {
        position: absolute;
        float: right;
        top: 10px;
        right: 10px;
        z-index: 2;
        min-width: 46px;
        height: 30px;
        margin: 0;
        padding: 0 10px;
        border: 1px solid #bfdbfe !important;
        border-radius: 8px !important;
        background: #eff6ff !important;
        color: #1d4ed8 !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.14);
        font-family: var(--app-font-sans) !important;
        font-size: 0.8rem !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        cursor: pointer;
    }
    .report-view .report-code-copy:hover {
        background: #dbeafe !important;
        transform: translateY(-1px);
    }
    .report-view .report-code-copy.is-copied {
        border-color: #99f6e4 !important;
        background: #ccfbf1 !important;
        color: #0f766e !important;
    }
    .report-view .report-code-copy.is-error {
        border-color: #fecdd3 !important;
        background: #fff1f2 !important;
        color: #be123c !important;
    }
    .report-view code {
        border-radius: 6px;
        padding: 1px 4px;
        color: #0f4f78;
        background: #eef6ff;
        font-weight: 650;
    }
    .report-view h1,
    .report-view h2,
    .report-view h3,
    .report-view h4 {
        color: var(--app-indigo);
        font-weight: 850;
    }
    .report-view strong {
        color: var(--app-primary-strong);
        font-weight: 850;
    }
    .report-view li::marker {
        color: var(--app-teal);
    }
    .report-view p,
    .report-view li {
        color: var(--app-text);
        line-height: 1.82;
    }
    .library-panel .dataframe,
    .library-panel table {
        border-radius: 8px !important;
        overflow: hidden;
    }
    .footer-note {
        color: var(--app-text-muted);
        text-align: center;
        margin-top: 20px;
    }
    footer {
        display: none !important;
    }
"""
