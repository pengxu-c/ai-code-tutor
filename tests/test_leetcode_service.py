from services import leetcode_service
from services.leetcode_service import load_leetcode_template, normalize_leetcode_slug


def test_normalize_leetcode_slug_accepts_slug_and_urls():
    assert normalize_leetcode_slug("two-sum") == "two-sum"
    assert normalize_leetcode_slug("https://leetcode.cn/problems/two-sum/") == "two-sum"
    assert normalize_leetcode_slug("https://leetcode.com/problems/two-sum/description/") == "two-sum"


def test_load_leetcode_template_success_with_login_state(monkeypatch):
    captured = {}

    def fake_get_problem(slug_or_url, language_slug, leetcode_session="", csrf_token=""):
        captured.update(
            {
                "slug_or_url": slug_or_url,
                "language_slug": language_slug,
                "leetcode_session": leetcode_session,
                "csrf_token": csrf_token,
            }
        )
        return {
            "title": "1. 两数之和",
            "difficulty": "简单",
            "tags": ["数组", "哈希表"],
            "leetcode_url": "https://leetcode.cn/problems/two-sum/",
            "description": "给定一个整数数组。",
            "examples": [{"input": "nums = [2,7,11,15]\ntarget = 9", "output": "[0,1]"}],
            "starter_code": "class Solution:\n    pass",
            "paid_only": True,
        }

    monkeypatch.setattr(leetcode_service, "get_leetcode_problem", fake_get_problem)

    code_update, desc, test_in, test_out, status = load_leetcode_template(
        "https://leetcode.cn/problems/two-sum/",
        "Python3",
        leetcode_session="sess-x",
        leetcode_csrf_token="csrf-x",
    )

    assert captured == {
        "slug_or_url": "https://leetcode.cn/problems/two-sum/",
        "language_slug": "python3",
        "leetcode_session": "sess-x",
        "csrf_token": "csrf-x",
    }
    assert code_update["value"] == "class Solution:\n    pass"
    assert code_update["language"] == "python"
    assert "# 1. 两数之和" in desc
    assert "- 标签：数组, 哈希表" in desc
    assert test_in == "nums = [2,7,11,15]\ntarget = 9"
    assert test_out == "[0,1]"
    assert "已使用 LeetCode 登录态" in status
    assert "会员题" in status


def test_load_leetcode_template_rejects_empty_or_invalid_slug(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("get_leetcode_problem should not be called")

    monkeypatch.setattr(leetcode_service, "get_leetcode_problem", fail_if_called)

    code_update, desc, test_in, test_out, status = load_leetcode_template(
        "https://leetcode.cn/explore/",
        "C++",
    )

    assert code_update["language"] == "cpp"
    assert "value" not in code_update
    assert desc == ""
    assert test_in == ""
    assert test_out == ""
    assert "请输入有效的题目 slug 或题目链接" in status


def test_load_leetcode_template_failure_preserves_language(monkeypatch):
    def fake_get_problem(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(leetcode_service, "get_leetcode_problem", fake_get_problem)

    code_update, desc, test_in, test_out, status = load_leetcode_template("two-sum", "JavaScript")

    assert code_update["language"] == "javascript"
    assert "value" not in code_update
    assert desc == ""
    assert test_in == ""
    assert test_out == ""
    assert status == "LeetCode 导入失败：network unavailable"


def test_load_leetcode_template_uses_first_parsed_example(monkeypatch):
    def fake_get_problem(*args, **kwargs):
        return {
            "title": "4. 寻找两个正序数组的中位数",
            "difficulty": "困难",
            "tags": ["数组", "二分查找"],
            "leetcode_url": "https://leetcode.cn/problems/median-of-two-sorted-arrays/",
            "description": "给定两个正序数组。",
            "examples": [
                {"input": "nums1 = [1,3]\nnums2 = [2]", "output": "2.00000"},
                {"input": "nums1 = [1,2]\nnums2 = [3,4]", "output": "2.50000"},
            ],
            "starter_code": "class Solution:\n    def findMedianSortedArrays(self, nums1, nums2):\n        pass",
            "paid_only": False,
        }

    monkeypatch.setattr(leetcode_service, "get_leetcode_problem", fake_get_problem)

    code_update, desc, test_in, test_out, status = load_leetcode_template(
        "median-of-two-sorted-arrays",
        "Python3",
    )

    assert code_update["value"].startswith("class Solution:")
    assert test_in == "nums1 = [1,3]\nnums2 = [2]"
    assert test_out == "2.00000"
    assert "寻找两个正序数组的中位数" in desc
