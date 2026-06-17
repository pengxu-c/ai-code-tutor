from analyzer.ast_analyzer import ASTAnalyzer


def test_ast_analyzer_reports_python_structure_and_common_issues():
    code = """
import math

class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        cache = {}
        unused_value = 42
        for i, num in enumerate(nums):
            if target - num in cache:
                return [cache[target - num], i]
            cache[num] = i
        return []
"""

    report = ASTAnalyzer().analyze(code)

    assert "### 代码概览" in report
    assert "- **函数数量：** 1" in report
    assert "- **类数量：** 1" in report
    assert "- **导入模块：** math" in report
    assert "- **圈复杂度：** 3" in report
    assert "**`twoSum`**" in report
    assert "返回类型：list[int]" in report
    assert "调用的函数：enumerate" in report
    assert "**`Solution`**" in report
    assert "定义的变量：`cache`, `i`, `num`, `unused_value`" in report
    assert "可能未使用的变量：`unused_value`" in report
    assert "`for` 循环：1 个" in report
    assert "`if/elif/else` 分支：1 个" in report


def test_ast_analyzer_reports_syntax_error_with_location():
    report = ASTAnalyzer().analyze("def broken(\n    pass")

    assert "### 语法错误" in report
    assert "第 1 行" in report
    assert "第 11 列" in report
    assert "请先修复语法错误" in report


def test_ast_analyzer_detects_existing_common_issue_rules():
    code = """
def append_item(items=[]):
    try:
        list = 1
    except:
        pass
    return items
"""

    report = ASTAnalyzer().analyze(code)

    assert "可变默认参数" in report
    assert "裸 except 捕获" in report
    assert "覆盖内置名称" in report
