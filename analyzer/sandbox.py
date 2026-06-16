"""
沙箱安全执行模块
在受限环境中安全地运行用户代码，并与测试用例对比验证

提供两种执行模式：
  - subprocess 模式（默认）：通过 subprocess 创建子进程，兼容性好
  - multiprocessing 模式：通过 multiprocessing 创建子进程，适合复杂场景
"""
import subprocess
import sys
import os
import time
import json
import tempfile
import ast
from dataclasses import dataclass, field
from typing import Optional


import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SANDBOX_TIMEOUT, SANDBOX_MAX_OUTPUT


# ==================== 安全执行器模板代码 ====================
# 这段代码会作为子进程的启动脚本运行
_SANDBOX_BOOTSTRAP = '''
import sys, io, builtins, traceback, json, ast, typing

# --- 安全限制 ---
FORBIDDEN_BUILTINS = {"exec", "eval", "compile", "open",
                      "globals", "locals", "vars", "exit", "quit"}
FORBIDDEN_MODULES = {"os", "sys", "subprocess", "shutil", "pathlib",
                     "socket", "http", "urllib", "requests",
                     "ctypes", "multiprocessing", "threading",
                     "signal", "resource"}

# 保存原始内置函数（compile 和 exec 在沙箱自身也需要使用）
_original_builtins = {}
for name in FORBIDDEN_BUILTINS:
    if hasattr(builtins, name):
        _original_builtins[name] = getattr(builtins, name)

# 保存 compile 和 exec 供沙箱自身使用
_safe_compile = _original_builtins.get("compile", compile)
_safe_exec = _original_builtins.get("exec", exec)

# 禁用用户使用的危险内置函数（排除 compile/exec，沙箱自身需要）
for name in FORBIDDEN_BUILTINS - {"compile", "exec"}:
    if hasattr(builtins, name):
        class _Forbidden:
            def __init__(self, n): self._n = n
            def __call__(self, *a, **kw):
                raise RuntimeError(f"安全限制：不允许使用 '{self._n}'")
        try:
            setattr(builtins, name, _Forbidden(name))
        except (AttributeError, TypeError):
            pass

# 禁用危险模块导入
_original_import = builtins.__import__
def _safe_import(name, *args, **kwargs):
    top = name.split(".")[0]
    if top in FORBIDDEN_MODULES:
        raise ImportError(f"安全限制：不允许导入模块 '{name}'")
    return _original_import(name, *args, **kwargs)
builtins.__import__ = _safe_import

# --- 执行用户代码 ---
def _parse_call_input(input_data):
    text = (input_data or "").strip()
    if not text:
        return [], {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed, {}
        if isinstance(parsed, dict):
            return [], parsed
        return [parsed], {}
    except json.JSONDecodeError:
        pass

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, tuple):
            return list(parsed), {}
        if isinstance(parsed, list):
            return parsed, {}
        if isinstance(parsed, dict):
            return [], parsed
        return [parsed], {}
    except (ValueError, SyntaxError):
        pass

    values = {}
    ordered_names = []
    try:
        module = ast.parse(text, mode="exec")
        for node in module.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                name = node.targets[0].id
                values[name] = ast.literal_eval(node.value)
                ordered_names.append(name)
        if values:
            return [], {name: values[name] for name in ordered_names}
    except Exception:
        pass

    return [input_data], {}


def _resolve_callable(ns, func_name):
    if func_name in ns and callable(ns[func_name]):
        return ns[func_name]

    if "." in func_name:
        owner, method = func_name.split(".", 1)
        target = ns.get(owner)
        if isinstance(target, type):
            target = target()
        if target is not None and hasattr(target, method):
            return getattr(target, method)

    solution = ns.get("Solution")
    if isinstance(solution, type) and hasattr(solution, func_name):
        return getattr(solution(), func_name)

    return None


def run_user_code():
    output_buf = io.StringIO()
    error_buf = io.StringIO()

    stdout_bak = sys.stdout
    stderr_bak = sys.stderr
    sys.stdout = output_buf
    sys.stderr = error_buf

    try:
        data = json.loads(sys.stdin.read())
        code = data["code"]
        input_data = data.get("input", "")
        func_name = data.get("function", "")

        compiled = _safe_compile(code, "<user_code>", "exec")

        if func_name:
            ns = {"__builtins__": builtins}
            _safe_exec(compiled, ns)
            target = _resolve_callable(ns, func_name)
            if target:
                args, kwargs = _parse_call_input(input_data)
                if kwargs:
                    result = target(**kwargs)
                else:
                    result = target(*args)
                if result is not None:
                    print(result)
            else:
                print(f"错误：未找到函数 '{func_name}'")
        else:
            ns = {"__builtins__": builtins}
            stdin_bak = sys.stdin
            sys.stdin = io.StringIO(input_data)
            _safe_exec(compiled, ns)
            sys.stdin = stdin_bak

    except SystemExit:
        pass
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    finally:
        sys.stdout = stdout_bak
        sys.stderr = stderr_bak
        # 恢复内置函数
        for name, original in _original_builtins.items():
            try:
                setattr(builtins, name, original)
            except:
                pass
        builtins.__import__ = _original_import

        # 输出 JSON 格式的结果
        result = {
            "output": output_buf.getvalue(),
            "error": error_buf.getvalue()
        }
        print(json.dumps(result, ensure_ascii=False))

run_user_code()
'''


@dataclass
class SandboxResult:
    """单个测试用例的运行结果"""
    input_data: str = ""
    expected_output: str = ""
    actual_output: str = ""
    error: str = ""
    passed: bool = False
    timeout: bool = False
    execution_time: float = 0.0


class SandboxRunner:
    """
    代码沙箱执行器（基于 subprocess）

    安全特性：
      - 子进程隔离：代码在独立进程中运行
      - 执行超时：防止死循环
      - 禁用危险函数：禁止文件操作、网络访问等
      - 输出限制：截断过长输出
      - 环境隔离：使用最小化的执行环境

    用法:
        runner = SandboxRunner()
        results = runner.run_tests(code, test_cases)
    """

    def __init__(
        self,
        timeout: int = SANDBOX_TIMEOUT,
        max_output: int = SANDBOX_MAX_OUTPUT,
    ):
        self.timeout = timeout
        self.max_output = max_output
        self._bootstrap_path: Optional[str] = None

    def _get_bootstrap_script(self) -> str:
        """获取引导脚本的文件路径（缓存到临时文件）"""
        if self._bootstrap_path and os.path.exists(self._bootstrap_path):
            return self._bootstrap_path

        # 写入临时文件
        fd, path = tempfile.mkstemp(suffix=".py", prefix="sandbox_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(_SANDBOX_BOOTSTRAP)
        self._bootstrap_path = path
        return path

    # ------------------------------------------------------------------
    #  公共接口
    # ------------------------------------------------------------------
    def run_tests(
        self,
        code: str,
        test_cases: list[dict],
        function_name: Optional[str] = None,
    ) -> list[SandboxResult]:
        """
        在沙箱中执行代码并验证测试用例

        Args:
            code: 用户代码
            test_cases: 测试用例列表
                - "input": 输入数据（会作为 stdin 传入）
                - "expected": 期望的输出
            function_name: 如果提供，直接调用该函数而非运行整个脚本

        Returns:
            SandboxResult 列表
        """
        results = []
        inferred_function = function_name or self._infer_callable_name(code)
        for tc in test_cases:
            result = self._run_single_test(
                code=code,
                input_data=str(tc.get("input", "")),
                expected_output=str(tc.get("expected", "")),
                function_name=inferred_function,
            )
            results.append(result)
        return results

    def run_code(self, code: str, input_data: str = "") -> SandboxResult:
        """
        运行代码并返回输出

        Args:
            code: Python 代码
            input_data: 标准输入数据

        Returns:
            SandboxResult
        """
        return self._run_single_test(
            code=code,
            input_data=input_data,
            expected_output="",
        )

    # ------------------------------------------------------------------
    #  内部方法
    # ------------------------------------------------------------------
    def _run_single_test(
        self,
        code: str,
        input_data: str,
        expected_output: str,
        function_name: Optional[str] = None,
    ) -> SandboxResult:
        """使用 subprocess 在子进程中运行单个测试"""
        result = SandboxResult(
            input_data=input_data,
            expected_output=expected_output,
        )

        try:
            bootstrap = self._get_bootstrap_script()
            payload = json.dumps({
                "code": code,
                "input": input_data,
                "function": function_name or "",
            }, ensure_ascii=False)

            start = time.time()
            proc = subprocess.run(
                [sys.executable, bootstrap],
                input=payload,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                # 安全限制
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": "/tmp",
                    "PYTHONPATH": "",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            elapsed = time.time() - start
            result.execution_time = round(elapsed, 3)

            if proc.returncode != 0 and not proc.stdout.strip():
                # 进程异常退出且无输出
                result.error = f"进程异常退出（返回码 {proc.returncode}）"
                if proc.stderr:
                    result.error += f"\n{proc.stderr[:500]}"
                return result

            # 解析子进程输出
            try:
                # 最后一行是 JSON 结果
                lines = proc.stdout.strip().split("\n")
                json_line = lines[-1] if lines else "{}"
                data = json.loads(json_line)
                result.actual_output = self._truncate(data.get("output", ""))
                error_text = data.get("error", "")
                if error_text:
                    result.error = error_text
            except (json.JSONDecodeError, IndexError):
                # JSON 解析失败，使用原始输出
                result.actual_output = self._truncate(proc.stdout)

            # 判断是否通过
            if expected_output:
                result.passed = self._compare_output(
                    result.actual_output.strip(),
                    expected_output.strip(),
                )

        except subprocess.TimeoutExpired:
            result.timeout = True
            result.error = f"代码执行超时（超过 {self.timeout} 秒），可能存在死循环。"
        except Exception as e:
            result.error = f"沙箱执行异常：{str(e)}"

        return result

    # ------------------------------------------------------------------
    #  辅助方法
    # ------------------------------------------------------------------
    def _infer_callable_name(self, code: str) -> Optional[str]:
        """Infer a callable for LeetCode-style Python submissions."""
        try:
            module = ast.parse(code)
        except SyntaxError:
            return None

        for node in module.body:
            if isinstance(node, ast.ClassDef) and node.name == "Solution":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                        return item.name

        for node in module.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                return node.name

        return None

    def _truncate(self, text: str) -> str:
        """截断过长输出"""
        if len(text) > self.max_output:
            return text[:self.max_output] + f"\n... (输出已截断，共 {len(text)} 字符)"
        return text

    def _compare_output(self, actual: str, expected: str) -> bool:
        """
        比较实际输出与期望输出
        支持多行输出、忽略空白差异等
        """
        actual_value = self._parse_output_value(actual)
        expected_value = self._parse_output_value(expected)
        if actual_value is not None and expected_value is not None:
            return actual_value == expected_value
        if isinstance(actual_value, str) and actual_value == self._strip_wrapping_quotes(expected):
            return True
        if isinstance(expected_value, str) and expected_value == self._strip_wrapping_quotes(actual):
            return True

        actual_lines = [line.strip() for line in actual.strip().splitlines() if line.strip()]
        expected_lines = [line.strip() for line in expected.strip().splitlines() if line.strip()]

        if len(actual_lines) != len(expected_lines):
            return False

        return all(a == e for a, e in zip(actual_lines, expected_lines))

    def _strip_wrapping_quotes(self, value: str) -> str:
        text = (value or "").strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            return text[1:-1]
        return text

    def _parse_output_value(self, value: str):
        """Parse JSON/Python-literal outputs so `[0, 1]` equals `[0,1]`."""
        text = (value or "").strip()
        if not text:
            return None

        for parser in (json.loads, ast.literal_eval):
            try:
                return parser(text)
            except (ValueError, SyntaxError, json.JSONDecodeError):
                continue

        lowered = text.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered == "null":
            return None

        return None

    def cleanup(self):
        """清理临时文件"""
        if self._bootstrap_path and os.path.exists(self._bootstrap_path):
            try:
                os.remove(self._bootstrap_path)
            except OSError:
                pass
            self._bootstrap_path = None
