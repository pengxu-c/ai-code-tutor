import requests

from database.leetcode_client import LeetCodeClient


class FakeResponse:
    def __init__(self, body=None, status_code=200, text=""):
        self._body = body or {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)


def make_question(**overrides):
    question = {
        "questionFrontendId": "1",
        "title": "Two Sum",
        "translatedTitle": "两数之和",
        "titleSlug": "two-sum",
        "translatedContent": "<p>给定一个整数数组。</p>",
        "content": "<p>Given an integer array.</p>",
        "difficulty": "EASY",
        "isPaidOnly": False,
        "exampleTestcases": "nums = [2,7,11,15]\ntarget = 9",
        "topicTags": [{"name": "Array", "translatedName": "数组"}],
        "codeSnippets": [
            {"langSlug": "python3", "code": "class Solution:\n    pass"},
            {"langSlug": "java", "code": "class Solution {}"},
        ],
    }
    question.update(overrides)
    return question


def test_normalize_slug_accepts_common_problem_inputs():
    normalize = LeetCodeClient.normalize_slug

    assert normalize("two-sum") == "two-sum"
    assert normalize(" /two-sum/ ") == "two-sum"
    assert normalize("https://leetcode.cn/problems/two-sum/?envType=study-plan") == "two-sum"
    assert normalize("https://leetcode.com/problems/two-sum/description/#examples") == "two-sum"
    assert normalize("leetcode.cn/problems/two-sum/description/") == "two-sum"
    assert normalize("https://leetcode.cn/explore/") == ""


def test_auth_headers_accept_raw_values_name_value_and_full_cookie():
    client = LeetCodeClient()

    raw_headers = client._build_auth_headers(
        "https://leetcode.cn/graphql/",
        leetcode_session="sess-x",
        csrf_token="csrf-x",
    )
    assert raw_headers["Cookie"] == "LEETCODE_SESSION=sess-x; csrftoken=csrf-x"
    assert raw_headers["X-CSRFToken"] == "csrf-x"
    assert raw_headers["Referer"] == "https://leetcode.cn/problemset/"

    name_value_headers = client._build_auth_headers(
        "https://leetcode.com/graphql",
        leetcode_session="LEETCODE_SESSION=sess-nv",
        csrf_token="csrftoken=csrf-nv",
    )
    assert name_value_headers["Cookie"] == "LEETCODE_SESSION=sess-nv; csrftoken=csrf-nv"
    assert name_value_headers["Referer"] == "https://leetcode.com/problemset/"

    cookie_headers = client._build_auth_headers(
        "https://leetcode.cn/graphql/",
        leetcode_session="foo=bar; LEETCODE_SESSION=sess-cookie; csrftoken=csrf-cookie",
    )
    assert cookie_headers["Cookie"] == "LEETCODE_SESSION=sess-cookie; csrftoken=csrf-cookie"
    assert cookie_headers["X-CSRFToken"] == "csrf-cookie"


def test_graphql_returns_data_and_raises_compact_errors():
    client = LeetCodeClient()
    calls = []

    def post_success(endpoint, json, headers, timeout):
        calls.append((endpoint, json, headers, timeout))
        return FakeResponse({"data": {"question": {"titleSlug": "two-sum"}}})

    client.session.post = post_success
    assert client._graphql("https://leetcode.cn/graphql/", "query", {"titleSlug": "two-sum"}) == {
        "question": {"titleSlug": "two-sum"}
    }
    assert calls[0][0] == "https://leetcode.cn/graphql/"

    long_error = "HTTP failure " + ("x" * 400)
    client.session.post = lambda *args, **kwargs: FakeResponse(status_code=403, text=long_error)
    try:
        client._graphql("https://leetcode.cn/graphql/", "query", {})
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
    assert message.startswith("HTTP failure")
    assert len(message) <= 243

    client.session.post = lambda *args, **kwargs: FakeResponse(
        {"errors": [{"message": "GraphQL failure " + ("y" * 400)}]}
    )
    try:
        client._graphql("https://leetcode.cn/graphql/", "query", {})
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
    assert message.startswith("GraphQL failure")
    assert len(message) <= 243


def test_fetch_problem_falls_back_from_cn_to_global_endpoint():
    client = LeetCodeClient(endpoints=["https://leetcode.cn/graphql/", "https://leetcode.com/graphql"])
    endpoints = []

    def post(endpoint, json, headers, timeout):
        endpoints.append(endpoint)
        if "leetcode.cn" in endpoint:
            return FakeResponse({"errors": [{"message": "cn unavailable"}]})
        return FakeResponse({"data": {"question": make_question(translatedTitle=None, translatedContent=None)}})

    client.session.post = post

    problem = client.fetch_problem("two-sum", language_slug="python3")

    assert endpoints == ["https://leetcode.cn/graphql/", "https://leetcode.com/graphql"]
    assert problem["title"] == "1. Two Sum"
    assert problem["source"] == "leetcode.com"
    assert problem["starter_code"] == "class Solution:\n    pass"
    assert problem["leetcode_url"] == "https://leetcode.com/problems/two-sum/"
