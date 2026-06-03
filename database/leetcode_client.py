"""
LeetCode online problem loader.

The project keeps only lightweight local examples in git. This module fetches
LeetCode problems on demand when the user enters a problem slug or URL.
"""
from __future__ import annotations

import html
import os
import re
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import urlparse

import requests


DEFAULT_ENDPOINTS = [
    os.getenv("LEETCODE_GRAPHQL_URL", "https://leetcode.cn/graphql/"),
    "https://leetcode.com/graphql",
]

DIFFICULTY_TO_CN = {
    "EASY": "简单",
    "MEDIUM": "中等",
    "HARD": "困难",
    "Easy": "简单",
    "Medium": "中等",
    "Hard": "困难",
}

DIFFICULTY_TO_API = {
    "简单": "EASY",
    "中等": "MEDIUM",
    "困难": "HARD",
    "Easy": "EASY",
    "Medium": "MEDIUM",
    "Hard": "HARD",
}


class _HTMLToMarkdown(HTMLParser):
    """Small HTML-to-text converter tuned for LeetCode statements."""

    BLOCK_TAGS = {"p", "div", "section", "br", "ul", "ol", "li", "pre"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._in_li = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        if tag in {"p", "div", "section", "pre", "ul", "ol"}:
            self._newline()
        elif tag == "br":
            self._newline()
        elif tag == "li":
            self._newline()
            self.parts.append("- ")
            self._in_li = True
        elif tag in {"code", "strong", "b"}:
            self.parts.append("`" if tag == "code" else "**")

    def handle_endtag(self, tag: str):
        if tag in {"p", "div", "section", "pre", "ul", "ol", "li"}:
            self._newline()
            if tag == "li":
                self._in_li = False
        elif tag in {"code", "strong", "b"}:
            self.parts.append("`" if tag == "code" else "**")

    def handle_data(self, data: str):
        text = html.unescape(data)
        if not text.strip():
            if text and not self._last_is_space():
                self.parts.append(" ")
            return
        self.parts.append(text)

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _newline(self):
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def _last_is_space(self) -> bool:
        return bool(self.parts and self.parts[-1].endswith((" ", "\n")))


class LeetCodeClient:
    """Fetch LeetCode problems with the public GraphQL endpoint."""

    QUESTION_QUERY_CN = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        questionFrontendId
        title
        translatedTitle
        titleSlug
        content
        translatedContent
        difficulty
        isPaidOnly
        exampleTestcases
        sampleTestCase
        topicTags {
          name
          slug
          translatedName
        }
        codeSnippets {
          lang
          langSlug
          code
        }
      }
    }
    """

    QUESTION_QUERY_GLOBAL = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        questionFrontendId
        title
        titleSlug
        content
        difficulty
        isPaidOnly
        exampleTestcases
        topicTags {
          name
          slug
        }
        codeSnippets {
          lang
          langSlug
          code
        }
      }
    }
    """

    SEARCH_QUERY_CN = """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      problemsetQuestionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, filters: $filters) {
        total
        questions {
          frontendQuestionId
          title
          titleCn
          titleSlug
          difficulty
          paidOnly
          topicTags {
            name
            slug
            nameTranslated
          }
        }
      }
    }
    """

    SEARCH_QUERY_GLOBAL = """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      problemsetQuestionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, filters: $filters) {
        total
        questions {
          frontendQuestionId
          title
          titleSlug
          difficulty
          paidOnly
          topicTags {
            name
            slug
          }
        }
      }
    }
    """

    def __init__(self, endpoints: Optional[list[str]] = None, timeout: int = 20):
        self.endpoints = [e for e in (endpoints or DEFAULT_ENDPOINTS) if e]
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "ai-code-tutor/1.0",
            "Referer": "https://leetcode.cn/problemset/",
        })

    @staticmethod
    def normalize_slug(value: str) -> str:
        """Accept a title slug, problem URL, or text containing either."""
        value = (value or "").strip()
        if not value:
            return ""

        parsed = urlparse(value)
        if parsed.netloc:
            match = re.search(r"/problems/([^/?#]+)/?", parsed.path)
            return match.group(1) if match else ""

        match = re.search(r"problems/([^/?#\s]+)/?", value)
        if match:
            return match.group(1)

        value = value.strip("/ ")
        return value

    def fetch_problem(
        self,
        slug_or_url: str,
        language_slug: str = "python3",
        leetcode_session: str = "",
        csrf_token: str = "",
    ) -> dict[str, Any]:
        slug = self.normalize_slug(slug_or_url)
        if not slug:
            raise ValueError("请输入 LeetCode 题目链接或 titleSlug，例如 two-sum。")

        last_error = None
        for endpoint in self.endpoints:
            query = self.QUESTION_QUERY_CN if "leetcode.cn" in endpoint else self.QUESTION_QUERY_GLOBAL
            try:
                payload = self._graphql(
                    endpoint,
                    query,
                    {"titleSlug": slug},
                    leetcode_session=leetcode_session,
                    csrf_token=csrf_token,
                )
                question = payload.get("question")
                if question:
                    return self._format_problem(question, endpoint, language_slug)
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"无法获取 LeetCode 题目：{last_error or slug}")

    def search(
        self,
        keyword: str = "",
        difficulty: str = "",
        limit: int = 20,
        leetcode_session: str = "",
        csrf_token: str = "",
    ) -> list[dict[str, Any]]:
        filters: dict[str, str] = {}
        if keyword.strip():
            filters["searchKeywords"] = keyword.strip()
        if difficulty.strip() and difficulty != "全部":
            filters["difficulty"] = DIFFICULTY_TO_API.get(difficulty, difficulty).upper()

        variables = {
            "categorySlug": "",
            "skip": 0,
            "limit": max(1, min(limit, 50)),
            "filters": filters,
        }

        last_error = None
        for endpoint in self.endpoints:
            query = self.SEARCH_QUERY_CN if "leetcode.cn" in endpoint else self.SEARCH_QUERY_GLOBAL
            try:
                payload = self._graphql(
                    endpoint,
                    query,
                    variables,
                    leetcode_session=leetcode_session,
                    csrf_token=csrf_token,
                )
                data = payload.get("problemsetQuestionList") or {}
                questions = data.get("questions") or []
                rows = [self._format_search_row(q) for q in questions]
                exact_row = self._search_exact_slug(
                    keyword,
                    leetcode_session=leetcode_session,
                    csrf_token=csrf_token,
                )
                if exact_row:
                    rows = [r for r in rows if r.get("slug") != exact_row.get("slug")]
                    rows.insert(0, exact_row)
                return rows[:variables["limit"]]
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"无法检索 LeetCode 题库：{last_error}")

    def _graphql(
        self,
        endpoint: str,
        query: str,
        variables: dict[str, Any],
        leetcode_session: str = "",
        csrf_token: str = "",
    ) -> dict[str, Any]:
        headers = self._build_auth_headers(endpoint, leetcode_session, csrf_token)
        response = self.session.post(
            endpoint,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(response.text[:500]) from exc
        body = response.json()
        if body.get("errors"):
            messages = "; ".join(e.get("message", "unknown error") for e in body["errors"])
            raise RuntimeError(messages)
        return body.get("data") or {}

    def _build_auth_headers(self, endpoint: str, leetcode_session: str = "", csrf_token: str = "") -> dict[str, str]:
        """Build request headers with optional LeetCode login cookies."""
        session_value, csrf_value = self._normalize_auth_values(leetcode_session, csrf_token)
        headers = dict(self.session.headers)
        host = "leetcode.cn" if "leetcode.cn" in endpoint else "leetcode.com"
        headers["Referer"] = f"https://{host}/problemset/"

        cookies = []
        if session_value:
            cookies.append(f"LEETCODE_SESSION={session_value}")
        if csrf_value:
            cookies.append(f"csrftoken={csrf_value}")
            headers["X-CSRFToken"] = csrf_value
        if cookies:
            headers["Cookie"] = "; ".join(cookies)
        return headers

    @staticmethod
    def _normalize_auth_values(leetcode_session: str = "", csrf_token: str = "") -> tuple[str, str]:
        """Accept raw token values, `name=value`, or a full Cookie header."""
        session_value = (leetcode_session or "").strip()
        csrf_value = (csrf_token or "").strip()

        cookie_text = session_value if "=" in session_value else ""
        if cookie_text:
            pairs = {}
            for part in cookie_text.split(";"):
                if "=" not in part:
                    continue
                key, value = part.split("=", 1)
                pairs[key.strip()] = value.strip()
            session_value = pairs.get("LEETCODE_SESSION", session_value)
            csrf_value = csrf_value or pairs.get("csrftoken", "")

        if session_value.startswith("LEETCODE_SESSION="):
            session_value = session_value.split("=", 1)[1].strip()
        if csrf_value.startswith("csrftoken="):
            csrf_value = csrf_value.split("=", 1)[1].strip()

        return session_value, csrf_value

    def _format_problem(self, question: dict[str, Any], endpoint: str, language_slug: str) -> dict[str, Any]:
        is_cn = "leetcode.cn" in endpoint
        title = question.get("translatedTitle") or question.get("title") or question.get("titleSlug", "")
        raw_content = question.get("translatedContent") or question.get("content") or ""
        description = html_to_markdown(raw_content)
        frontend_id = question.get("questionFrontendId") or question.get("questionId") or ""
        title_slug = question.get("titleSlug") or ""

        tags = []
        for tag in question.get("topicTags") or []:
            tag_name = tag.get("translatedName") or tag.get("nameTranslated") or tag.get("name")
            if tag_name:
                tags.append(tag_name)

        starter = ""
        snippets = {}
        for snippet in question.get("codeSnippets") or []:
            slug = snippet.get("langSlug", "")
            if slug:
                snippets[slug] = snippet.get("code") or ""
            if slug == language_slug:
                starter = snippet.get("code") or ""
        if not starter and language_slug == "python3":
            starter = snippets.get("python") or ""
        if not starter:
            starter = snippets.get("python3") or next(iter(snippets.values()), "")

        source_host = "leetcode.cn" if is_cn else "leetcode.com"
        return {
            "title": f"{frontend_id}. {title}" if frontend_id else title,
            "difficulty": DIFFICULTY_TO_CN.get(question.get("difficulty"), question.get("difficulty", "未知")),
            "tags": tags,
            "description": description,
            "examples": _extract_examples(question.get("exampleTestcases") or question.get("sampleTestCase") or ""),
            "starter_code": starter,
            "code_snippets": snippets,
            "selected_language": language_slug,
            "hint": "题目来自 LeetCode 在线导入，请结合原站示例与约束练习。",
            "source": source_host,
            "leetcode_slug": title_slug,
            "leetcode_url": f"https://{source_host}/problems/{title_slug}/" if title_slug else "",
            "paid_only": bool(question.get("isPaidOnly")),
        }

    def _format_search_row(self, question: dict[str, Any]) -> dict[str, Any]:
        tags = []
        for tag in question.get("topicTags") or []:
            tag_name = tag.get("translatedName") or tag.get("nameTranslated") or tag.get("name")
            if tag_name:
                tags.append(tag_name)
        return {
            "id": question.get("frontendQuestionId", ""),
            "title": question.get("translatedTitle") or question.get("titleCn") or question.get("title", ""),
            "difficulty": DIFFICULTY_TO_CN.get(question.get("difficulty"), question.get("difficulty", "")),
            "tags": tags,
            "slug": question.get("titleSlug", ""),
            "paid_only": bool(question.get("paidOnly")),
        }

    def _search_exact_slug(
        self,
        keyword: str,
        leetcode_session: str = "",
        csrf_token: str = "",
    ) -> Optional[dict[str, Any]]:
        keyword = (keyword or "").strip()
        if not keyword or re.search(r"[\u4e00-\u9fff]", keyword):
            return None

        slug = self.normalize_slug(keyword.lower().replace(" ", "-"))
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            return None

        try:
            problem = self.fetch_problem(
                slug,
                leetcode_session=leetcode_session,
                csrf_token=csrf_token,
            )
        except Exception:
            return None

        title = problem.get("title", "")
        frontend_id = ""
        if ". " in title:
            frontend_id, title = title.split(". ", 1)

        return {
            "id": frontend_id,
            "title": title,
            "difficulty": problem.get("difficulty", ""),
            "tags": problem.get("tags", []),
            "slug": problem.get("leetcode_slug", slug),
            "paid_only": bool(problem.get("paid_only")),
        }


def html_to_markdown(html_text: str) -> str:
    parser = _HTMLToMarkdown()
    parser.feed(html_text or "")
    return parser.get_text()


def _extract_examples(example_text: str) -> list[dict[str, str]]:
    """Keep the current app's example shape without trying to parse every format."""
    example_text = (example_text or "").strip()
    if not example_text:
        return []
    return [{"input": example_text, "output": ""}]
