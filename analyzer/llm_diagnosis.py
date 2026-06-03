"""
LLM 智能诊断模块
使用 DeepSeek 大模型对用户代码进行错误定位、原因分析和修复建议
"""
import json
import os
import re
from typing import Optional

import requests

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DIAGNOSIS_MODEL,
    VARIANT_MODEL,
)


class LLMDiagnosis:
    """
    基于 DeepSeek 大语言模型的代码诊断器

    功能：
      - 错误定位：找到代码中的错误行和错误类型
      - 原因分析：解释为什么会产生错误
      - 修复建议：给出具体的修改方案和修正后的代码
      - 变式题生成：基于原题生成相似练习题

    用法:
        diag = LLMDiagnosis()
        result = diag.diagnose(code, problem_desc, error_info)
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.diagnosis_model = DIAGNOSIS_MODEL
        self.variant_model = VARIANT_MODEL

    # ------------------------------------------------------------------
    #  核心 API 调用
    # ------------------------------------------------------------------
    def _call_llm(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """
        调用 DeepSeek Chat API

        Args:
            messages: 对话消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Returns:
            模型生成的文本内容
        """
        api_key = self._normalize_api_key()
        if not api_key:
            return (
                "API Key 未配置：请在页面“配置”区域输入 DeepSeek API Key，"
                "或设置环境变量 DEEPSEEK_API_KEY 后重启应用。"
            )
        if not api_key.startswith("sk-"):
            return (
                "API Key 格式不正确：DeepSeek 的 Authorization 应为 `Bearer sk-...`。"
                "请只填写以 `sk-` 开头的 API Key，不要填写占位符或其他文本。"
            )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model or self.diagnosis_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            return "请求超时，请稍后重试。"
        except requests.exceptions.ConnectionError:
            return "无法连接到 API 服务，请检查网络连接和 API 地址。"
        except requests.exceptions.HTTPError as e:
            return f"API 请求失败（HTTP {e.response.status_code}）：{e.response.text[:200]}"
        except (KeyError, IndexError):
            return "API 返回格式异常，请检查 API 配置。"

    def _normalize_api_key(self) -> str:
        """Normalize user input to a raw DeepSeek API key."""
        api_key = (self.api_key or "").strip()
        if api_key.lower().startswith("bearer "):
            api_key = api_key[7:].strip()
        return api_key

    # ------------------------------------------------------------------
    #  错误诊断
    # ------------------------------------------------------------------
    def diagnose(
        self,
        code: str,
        problem_desc: str = "",
        error_info: str = "",
        test_cases: Optional[list[dict]] = None,
        language: str = "Python3",
    ) -> dict:
        """
        对用户代码进行全面的错误诊断

        Args:
            code: 用户提交的代码
            problem_desc: 题目描述
            error_info: 报错信息或运行结果
            test_cases: 测试用例列表，每个元素 {"input": ..., "expected": ...}
            language: 用户代码使用的编程语言

        Returns:
            包含 error_analysis 和 fix_suggestion 两个键的字典
        """
        test_info = ""
        if test_cases:
            test_info = "\n\n### 测试用例\n"
            for i, tc in enumerate(test_cases, 1):
                test_info += f"- 用例{i}：输入={tc.get('input','')}, 期望输出={tc.get('expected','')}\n"

        system_prompt = """你是一位经验丰富的编程教师和代码审查专家。你的任务是：
1. 仔细阅读学生使用指定编程语言编写的代码，找出其中的逻辑错误、语法错误或效率问题
2. 用通俗易懂的语言解释错误原因，帮助学生理解"为什么错"
3. 给出具体的修复建议，包括使用同一种编程语言修改后的完整代码
4. 如果代码是正确的，也要指出可以优化的地方

请用中文回答，使用 Markdown 格式。"""

        user_prompt = f"""## 编程语言
{language}

## 题目描述
{problem_desc or '（未提供）'}

## 学生代码
```{language.lower()}
{code}
```

## 报错信息 / 运行结果
{error_info or '（未提供）'}
{test_info}

请按以下格式回答：

### 1. 错误定位
指出代码中存在问题的具体位置（行号或代码片段）。

### 2. 错误原因分析
详细解释为什么会产生这个错误，帮助学生理解问题的本质。

### 3. 修复建议
给出使用 **{language}** 修改后的完整代码，并用该语言的注释标注修改的位置。不要切换到其他编程语言。

### 4. 知识点总结
列出涉及的关键知识点，帮助学生巩固。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self._call_llm(messages, model=self.diagnosis_model, temperature=0.3)
        error_analysis, fix_suggestion = self._split_diagnosis_response(response)

        return {
            "error_analysis": error_analysis,
            "fix_suggestion": fix_suggestion,
        }

    def _split_diagnosis_response(self, response: str) -> tuple[str, str]:
        """
        Split the model response into diagnosis and fix sections.

        The prompt asks for:
        1. 错误定位
        2. 错误原因分析
        3. 修复建议
        4. 知识点总结

        The report has its own top-level "三、修复建议" section, so keep
        sections 1-2 in "错误诊断" and move sections 3+ into "修复建议".
        """
        text = (response or "").strip()
        if not text:
            return "", ""

        fix_match = self._find_section_heading(text, {"3", "三"}, "修复")
        if not fix_match:
            return text, ""

        error_analysis = text[:fix_match.start()].strip()
        fix_suggestion = text[fix_match.start():].strip()

        return error_analysis or "（模型未单独返回错误诊断内容）", fix_suggestion

    @staticmethod
    def _find_section_heading(text: str, numbers: set[str], keyword: str) -> Optional[re.Match]:
        """Find a Markdown heading such as `### 3. 修复建议` or `## 三、修复建议`."""
        heading_pattern = re.compile(r"^(#{1,6})\s*(?P<title>.+?)\s*$", re.MULTILINE)
        number_pattern = re.compile(r"^\s*(?P<num>\d+|[一二三四五六七八九十])\s*[\.\、:：)]?\s*(?P<rest>.*)")

        for match in heading_pattern.finditer(text):
            title = match.group("title").strip()
            number_match = number_pattern.match(title)
            if not number_match:
                continue
            number = number_match.group("num")
            rest = number_match.group("rest")
            if number in numbers and keyword in rest:
                return match
        return None

    # ------------------------------------------------------------------
    #  变式题生成
    # ------------------------------------------------------------------
    def generate_variants(
        self,
        problem_desc: str,
        code: str = "",
        count: int = 3,
    ) -> list[str]:
        """
        基于原题生成变式训练题

        Args:
            problem_desc: 原题描述
            code: 原题代码（可选，用于参考解题思路）
            count: 生成变式题的数量

        Returns:
            变式题描述列表
        """
        system_prompt = """你是一位资深的编程教育专家。你的任务是基于给定的编程题目，生成相似但有变化的变式训练题，帮助学生举一反三、巩固知识。

要求：
1. 变式题应与原题考察相同或相近的知识点
2. 难度可以略有变化（有简单有困难）
3. 每道变式题都要有完整的题目描述、输入输出说明和示例
4. 用中文回答，使用 Markdown 格式"""

        user_prompt = f"""## 原题
{problem_desc}

## 原题参考代码
```python
{code or '（未提供）'}
```

请生成 {count} 道变式训练题，每道题按以下格式：

### 变式题 X
**题目名称：** ...

**题目描述：** ...

**输入格式：** ...

**输出格式：** ...

**示例：**
输入：...
输出：...

**提示：** 考察的知识点和解题思路"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self._call_llm(messages, model=self.variant_model, temperature=0.7)

        # 按变式题标题拆分
        variants = []
        current = []
        for line in response.split("\n"):
            if line.startswith("### 变式题") and current:
                variants.append("\n".join(current).strip())
                current = [line]
            else:
                current.append(line)
        if current:
            variants.append("\n".join(current).strip())

        return variants[:count]

    # ------------------------------------------------------------------
    #  代码理解（简要说明）
    # ------------------------------------------------------------------
    def explain_code(self, code: str, language: str = "Python3") -> str:
        """
        用通俗语言解释代码的功能和逻辑

        Args:
            code: Python 代码

        Returns:
            代码功能说明
        """
        system_prompt = "你是一位耐心的编程老师。请用通俗易懂的中文解释以下代码的功能、逻辑流程和关键步骤。"
        user_prompt = f"请解释以下 {language} 代码：\n```{language.lower()}\n{code}\n```"

        return self._call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
