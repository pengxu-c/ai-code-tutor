"""
Programming language metadata used by the UI, LeetCode import, and prompts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LanguageSpec:
    display: str
    leetcode_slug: str
    gradio_language: Optional[str]
    line_comment: str


SUPPORTED_LANGUAGES: list[LanguageSpec] = [
    LanguageSpec("Python3", "python3", "python", "#"),
    LanguageSpec("Java", "java", None, "//"),
    LanguageSpec("C++", "cpp", "cpp", "//"),
    LanguageSpec("C", "c", "c", "//"),
    LanguageSpec("C#", "csharp", None, "//"),
    LanguageSpec("JavaScript", "javascript", "javascript", "//"),
    LanguageSpec("TypeScript", "typescript", "typescript", "//"),
    LanguageSpec("Go", "golang", None, "//"),
    LanguageSpec("Rust", "rust", None, "//"),
    LanguageSpec("Kotlin", "kotlin", None, "//"),
    LanguageSpec("Swift", "swift", None, "//"),
    LanguageSpec("Ruby", "ruby", None, "#"),
    LanguageSpec("PHP", "php", None, "//"),
]

_BY_DISPLAY = {spec.display: spec for spec in SUPPORTED_LANGUAGES}
_BY_LEETCODE_SLUG = {spec.leetcode_slug: spec for spec in SUPPORTED_LANGUAGES}


def get_language_choices() -> list[str]:
    return [spec.display for spec in SUPPORTED_LANGUAGES]


def get_language_spec(language: str | None) -> LanguageSpec:
    if language in _BY_DISPLAY:
        return _BY_DISPLAY[language]
    if language in _BY_LEETCODE_SLUG:
        return _BY_LEETCODE_SLUG[language]
    return SUPPORTED_LANGUAGES[0]


def is_python_language(language: str | None) -> bool:
    return get_language_spec(language).leetcode_slug == "python3"


def get_leetcode_slug(language: str | None) -> str:
    return get_language_spec(language).leetcode_slug


def get_gradio_language(language: str | None) -> Optional[str]:
    return get_language_spec(language).gradio_language


def build_local_starter(problem: dict, language: str | None) -> str:
    """Return a local starter template for the selected language."""
    spec = get_language_spec(language)
    if spec.leetcode_slug == "python3":
        return problem.get("starter_code", "")

    signature = _signature_for_problem(problem.get("title", ""), spec.leetcode_slug)
    if signature:
        return signature

    title = problem.get("title", "题目")
    comment = spec.line_comment
    if spec.leetcode_slug == "java":
        return f"class Solution {{\n    {comment} 请根据题目“{title}”补全方法签名和实现\n}}"
    if spec.leetcode_slug == "cpp":
        return f"class Solution {{\npublic:\n    {comment} 请根据题目“{title}”补全方法签名和实现\n}};"
    if spec.leetcode_slug == "csharp":
        return f"public class Solution {{\n    {comment} 请根据题目“{title}”补全方法签名和实现\n}}"
    if spec.leetcode_slug in {"javascript", "typescript"}:
        return f"{comment} 请根据题目“{title}”补全函数签名和实现"
    if spec.leetcode_slug == "golang":
        return f"{comment} 请根据题目“{title}”补全函数签名和实现"
    if spec.leetcode_slug == "rust":
        return f"impl Solution {{\n    {comment} 请根据题目“{title}”补全方法签名和实现\n}}"
    return f"{comment} 请根据题目“{title}”补全代码"


def _signature_for_problem(title: str, slug: str) -> str:
    """Starter signatures for the built-in demo problems."""
    normalized = title.strip()
    templates = _LOCAL_STARTER_TEMPLATES.get(normalized, {})
    return templates.get(slug, "")


_LOCAL_STARTER_TEMPLATES: dict[str, dict[str, str]] = {
    "两数之和": {
        "java": "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        // 请在此编写代码\n        return new int[0];\n    }\n}",
        "cpp": "class Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        // 请在此编写代码\n        return {};\n    }\n};",
        "c": "int* twoSum(int* nums, int numsSize, int target, int* returnSize) {\n    // 请在此编写代码\n    *returnSize = 0;\n    return NULL;\n}",
        "csharp": "public class Solution {\n    public int[] TwoSum(int[] nums, int target) {\n        // 请在此编写代码\n        return new int[0];\n    }\n}",
        "javascript": "var twoSum = function(nums, target) {\n    // 请在此编写代码\n};",
        "typescript": "function twoSum(nums: number[], target: number): number[] {\n    // 请在此编写代码\n    return [];\n}",
        "golang": "func twoSum(nums []int, target int) []int {\n    // 请在此编写代码\n    return []int{}\n}",
        "rust": "impl Solution {\n    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {\n        // 请在此编写代码\n        vec![]\n    }\n}",
    },
    "三数之和": {
        "java": "class Solution {\n    public List<List<Integer>> threeSum(int[] nums) {\n        // 请在此编写代码\n        return new ArrayList<>();\n    }\n}",
        "cpp": "class Solution {\npublic:\n    vector<vector<int>> threeSum(vector<int>& nums) {\n        // 请在此编写代码\n        return {};\n    }\n};",
        "javascript": "var threeSum = function(nums) {\n    // 请在此编写代码\n};",
        "typescript": "function threeSum(nums: number[]): number[][] {\n    // 请在此编写代码\n    return [];\n}",
        "golang": "func threeSum(nums []int) [][]int {\n    // 请在此编写代码\n    return [][]int{}\n}",
        "rust": "impl Solution {\n    pub fn three_sum(nums: Vec<i32>) -> Vec<Vec<i32>> {\n        // 请在此编写代码\n        vec![]\n    }\n}",
    },
    "有效的括号": {
        "java": "class Solution {\n    public boolean isValid(String s) {\n        // 请在此编写代码\n        return false;\n    }\n}",
        "cpp": "class Solution {\npublic:\n    bool isValid(string s) {\n        // 请在此编写代码\n        return false;\n    }\n};",
        "javascript": "var isValid = function(s) {\n    // 请在此编写代码\n};",
        "typescript": "function isValid(s: string): boolean {\n    // 请在此编写代码\n    return false;\n}",
        "golang": "func isValid(s string) bool {\n    // 请在此编写代码\n    return false\n}",
        "rust": "impl Solution {\n    pub fn is_valid(s: String) -> bool {\n        // 请在此编写代码\n        false\n    }\n}",
    },
    "合并两个有序链表": {
        "java": "class Solution {\n    public ListNode mergeTwoLists(ListNode list1, ListNode list2) {\n        // 请在此编写代码\n        return null;\n    }\n}",
        "cpp": "class Solution {\npublic:\n    ListNode* mergeTwoLists(ListNode* list1, ListNode* list2) {\n        // 请在此编写代码\n        return nullptr;\n    }\n};",
        "javascript": "var mergeTwoLists = function(list1, list2) {\n    // 请在此编写代码\n};",
        "typescript": "function mergeTwoLists(list1: ListNode | null, list2: ListNode | null): ListNode | null {\n    // 请在此编写代码\n    return null;\n}",
        "golang": "func mergeTwoLists(list1 *ListNode, list2 *ListNode) *ListNode {\n    // 请在此编写代码\n    return nil\n}",
        "rust": "impl Solution {\n    pub fn merge_two_lists(list1: Option<Box<ListNode>>, list2: Option<Box<ListNode>>) -> Option<Box<ListNode>> {\n        // 请在此编写代码\n        None\n    }\n}",
    },
    "最大子数组和": {
        "java": "class Solution {\n    public int maxSubArray(int[] nums) {\n        // 请在此编写代码\n        return 0;\n    }\n}",
        "cpp": "class Solution {\npublic:\n    int maxSubArray(vector<int>& nums) {\n        // 请在此编写代码\n        return 0;\n    }\n};",
        "javascript": "var maxSubArray = function(nums) {\n    // 请在此编写代码\n};",
        "typescript": "function maxSubArray(nums: number[]): number {\n    // 请在此编写代码\n    return 0;\n}",
        "golang": "func maxSubArray(nums []int) int {\n    // 请在此编写代码\n    return 0\n}",
        "rust": "impl Solution {\n    pub fn max_sub_array(nums: Vec<i32>) -> i32 {\n        // 请在此编写代码\n        0\n    }\n}",
    },
    "二分查找": {
        "java": "class Solution {\n    public int search(int[] nums, int target) {\n        // 请在此编写代码\n        return -1;\n    }\n}",
        "cpp": "class Solution {\npublic:\n    int search(vector<int>& nums, int target) {\n        // 请在此编写代码\n        return -1;\n    }\n};",
        "javascript": "var search = function(nums, target) {\n    // 请在此编写代码\n};",
        "typescript": "function search(nums: number[], target: number): number {\n    // 请在此编写代码\n    return -1;\n}",
        "golang": "func search(nums []int, target int) int {\n    // 请在此编写代码\n    return -1\n}",
        "rust": "impl Solution {\n    pub fn search(nums: Vec<i32>, target: i32) -> i32 {\n        // 请在此编写代码\n        -1\n    }\n}",
    },
    "爬楼梯": {
        "java": "class Solution {\n    public int climbStairs(int n) {\n        // 请在此编写代码\n        return 0;\n    }\n}",
        "cpp": "class Solution {\npublic:\n    int climbStairs(int n) {\n        // 请在此编写代码\n        return 0;\n    }\n};",
        "javascript": "var climbStairs = function(n) {\n    // 请在此编写代码\n};",
        "typescript": "function climbStairs(n: number): number {\n    // 请在此编写代码\n    return 0;\n}",
        "golang": "func climbStairs(n int) int {\n    // 请在此编写代码\n    return 0\n}",
        "rust": "impl Solution {\n    pub fn climb_stairs(n: i32) -> i32 {\n        // 请在此编写代码\n        0\n    }\n}",
    },
    "最长公共前缀": {
        "java": "class Solution {\n    public String longestCommonPrefix(String[] strs) {\n        // 请在此编写代码\n        return \"\";\n    }\n}",
        "cpp": "class Solution {\npublic:\n    string longestCommonPrefix(vector<string>& strs) {\n        // 请在此编写代码\n        return \"\";\n    }\n};",
        "javascript": "var longestCommonPrefix = function(strs) {\n    // 请在此编写代码\n};",
        "typescript": "function longestCommonPrefix(strs: string[]): string {\n    // 请在此编写代码\n    return \"\";\n}",
        "golang": "func longestCommonPrefix(strs []string) string {\n    // 请在此编写代码\n    return \"\"\n}",
        "rust": "impl Solution {\n    pub fn longest_common_prefix(strs: Vec<String>) -> String {\n        // 请在此编写代码\n        String::new()\n    }\n}",
    },
    "买卖股票的最佳时机": {
        "java": "class Solution {\n    public int maxProfit(int[] prices) {\n        // 请在此编写代码\n        return 0;\n    }\n}",
        "cpp": "class Solution {\npublic:\n    int maxProfit(vector<int>& prices) {\n        // 请在此编写代码\n        return 0;\n    }\n};",
        "javascript": "var maxProfit = function(prices) {\n    // 请在此编写代码\n};",
        "typescript": "function maxProfit(prices: number[]): number {\n    // 请在此编写代码\n    return 0;\n}",
        "golang": "func maxProfit(prices []int) int {\n    // 请在此编写代码\n    return 0\n}",
        "rust": "impl Solution {\n    pub fn max_profit(prices: Vec<i32>) -> i32 {\n        // 请在此编写代码\n        0\n    }\n}",
    },
    "反转链表": {
        "java": "class Solution {\n    public ListNode reverseList(ListNode head) {\n        // 请在此编写代码\n        return null;\n    }\n}",
        "cpp": "class Solution {\npublic:\n    ListNode* reverseList(ListNode* head) {\n        // 请在此编写代码\n        return nullptr;\n    }\n};",
        "javascript": "var reverseList = function(head) {\n    // 请在此编写代码\n};",
        "typescript": "function reverseList(head: ListNode | null): ListNode | null {\n    // 请在此编写代码\n    return null;\n}",
        "golang": "func reverseList(head *ListNode) *ListNode {\n    // 请在此编写代码\n    return nil\n}",
        "rust": "impl Solution {\n    pub fn reverse_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {\n        // 请在此编写代码\n        None\n    }\n}",
    },
}
