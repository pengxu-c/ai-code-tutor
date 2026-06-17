from utils.languages import (
    build_local_starter,
    get_gradio_language,
    get_language_choices,
    get_language_spec,
    get_leetcode_slug,
    is_python_language,
)


def test_language_mappings_and_unknown_fallback():
    assert "Python3" in get_language_choices()
    assert get_language_spec("Python3").leetcode_slug == "python3"
    assert get_language_spec("python3").display == "Python3"
    assert get_language_spec("Unknown").display == "Python3"
    assert get_leetcode_slug("C++") == "cpp"
    assert get_gradio_language("JavaScript") == "javascript"
    assert get_gradio_language("Java") is None
    assert is_python_language("Python3") is True
    assert is_python_language("Java") is False


def test_build_local_starter_uses_python_starter_code():
    problem = {"title": "任意题", "starter_code": "class Solution:\n    pass"}

    assert build_local_starter(problem, "Python3") == "class Solution:\n    pass"


def test_build_local_starter_uses_builtin_templates():
    problem = {"title": "两数之和", "starter_code": "python-only"}

    assert "public int[] twoSum" in build_local_starter(problem, "Java")
    assert "vector<int> twoSum" in build_local_starter(problem, "C++")
    assert "function twoSum" in build_local_starter(problem, "TypeScript")


def test_build_local_starter_falls_back_to_generic_language_template():
    problem = {"title": "自定义题", "starter_code": "python-only"}

    assert "请根据题目“自定义题”补全方法签名和实现" in build_local_starter(problem, "Java")
    assert "impl Solution" in build_local_starter(problem, "Rust")
    assert "请根据题目“自定义题”补全代码" in build_local_starter(problem, "Ruby")
