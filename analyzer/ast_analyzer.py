"""
AST 代码结构分析模块
使用 Python ast 模块对用户代码进行静态分析，提取代码结构信息
"""
import ast
import textwrap
from typing import Optional


class ASTAnalyzer:
    """
    基于 Python AST 的代码结构分析器

    功能：
      - 提取函数、类定义及其参数
      - 识别变量声明与使用
      - 统计控制流结构（循环、条件分支）
      - 检测常见代码模式与潜在问题
      - 生成可视化调用关系

    用法:
        analyzer = ASTAnalyzer()
        report = analyzer.analyze("def twoSum(nums, target): ...")
    """

    def __init__(self):
        self.source_code: str = ""
        self.tree: Optional[ast.AST] = None
        self.parse_error: Optional[str] = None

    # ------------------------------------------------------------------
    #  公共接口
    # ------------------------------------------------------------------
    def analyze(self, code: str) -> str:
        """
        对给定代码进行完整的 AST 分析，返回 Markdown 格式的分析报告

        Args:
            code: Python 源代码字符串

        Returns:
            Markdown 格式的分析结果
        """
        self.source_code = code.strip()
        self.parse_error = None

        # 1) 尝试解析
        try:
            self.tree = ast.parse(self.source_code)
        except SyntaxError as e:
            self.parse_error = (
                f"第 {e.lineno} 行，第 {e.offset} 列：{e.msg}\n"
                f"  {e.text}"
            )
            return self._build_error_report()

        # 2) 收集各项分析数据
        functions = self._extract_functions()
        classes = self._extract_classes()
        variables = self._extract_variables()
        imports = self._extract_imports()
        control_flow = self._analyze_control_flow()
        complexity = self._calc_complexity()
        issues = self._detect_common_issues()

        # 3) 拼接 Markdown 报告
        parts = []

        # --- 概览 ---
        parts.append("### 代码概览")
        parts.append(f"- **总行数：** {len(self.source_code.splitlines())}")
        parts.append(f"- **函数数量：** {len(functions)}")
        parts.append(f"- **类数量：** {len(classes)}")
        parts.append(f"- **变量数量：** {len(variables['defined'])}")
        parts.append(f"- **导入模块：** {', '.join(imports) if imports else '无'}")
        parts.append(f"- **圈复杂度：** {complexity}")
        parts.append("")

        # --- 函数/方法 ---
        if functions:
            parts.append("### 函数列表")
            for func in functions:
                parts.append(f"- **`{func['name']}`**（第 {func['lineno']} 行）")
                parts.append(f"  - 参数：{func['args'] or '无'}")
                parts.append(f"  - 返回类型：{func['returns'] or '未标注'}")
                parts.append(f"  - 文档字符串：{'有' if func['docstring'] else '无'}")
                parts.append(f"  - 行数：{func['end_lineno'] - func['lineno'] + 1}")
                if func["calls"]:
                    parts.append(f"  - 调用的函数：{', '.join(func['calls'])}")
            parts.append("")

        # --- 类 ---
        if classes:
            parts.append("### 类列表")
            for cls in classes:
                parts.append(f"- **`{cls['name']}`**（第 {cls['lineno']} 行）")
                parts.append(f"  - 基类：{cls['bases'] or '无'}")
                parts.append(f"  - 方法：{', '.join(cls['methods']) if cls['methods'] else '无'}")
            parts.append("")

        # --- 变量 ---
        if variables["defined"]:
            parts.append("### 变量定义")
            parts.append(f"- 定义的变量：{', '.join(f'`{v}`' for v in sorted(variables['defined']))}")
            if variables["unused"]:
                parts.append(f"- ⚠️ 可能未使用的变量：{', '.join(f'`{v}`' for v in sorted(variables['unused']))}")
            parts.append("")

        # --- 控制流 ---
        parts.append("### 控制流分析")
        parts.append(f"- `for` 循环：{control_flow['for_loops']} 个")
        parts.append(f"- `while` 循环：{control_flow['while_loops']} 个")
        parts.append(f"- `if/elif/else` 分支：{control_flow['if_stmts']} 个")
        parts.append(f"- `try/except` 块：{control_flow['try_excepts']} 个")
        parts.append(f"- 列表推导式：{control_flow['list_comprehensions']} 个")
        parts.append("")

        # --- 常见问题检测 ---
        if issues:
            parts.append("### 常见问题检测")
            for issue in issues:
                icon = "🔴" if issue["severity"] == "error" else "🟡" if issue["severity"] == "warning" else "🔵"
                parts.append(f"- {icon} **{issue['title']}**（第 {issue['line']} 行）：{issue['message']}")
            parts.append("")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    #  私有方法 —— 各项分析
    # ------------------------------------------------------------------
    def _extract_functions(self) -> list[dict]:
        """提取所有函数定义"""
        results = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                args = [a.arg for a in node.args.args]
                returns = self._get_annotation_str(node.returns)
                calls = self._get_called_functions(node)
                results.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno or node.lineno,
                    "args": args,
                    "returns": returns,
                    "docstring": ast.get_docstring(node) is not None,
                    "calls": calls,
                    "is_method": False,
                })

        # 标记方法（类内部函数）
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                method_names = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
                for func in results:
                    if func["name"] in method_names:
                        func["is_method"] = True

        return results

    def _extract_classes(self) -> list[dict]:
        """提取所有类定义"""
        results = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                bases = [self._get_name_str(b) for b in node.bases]
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                results.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "bases": bases,
                    "methods": methods,
                })
        return results

    def _extract_variables(self) -> dict:
        """提取变量定义与使用情况"""
        defined = set()
        used = set()

        for node in ast.walk(self.tree):
            # 赋值目标
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    defined.update(self._extract_names_from_target(target))
            elif isinstance(node, ast.AugAssign):
                defined.add(self._get_name_str(node.target))
            elif isinstance(node, ast.AnnAssign) and node.target:
                defined.add(self._get_name_str(node.target))
            # for 循环变量
            elif isinstance(node, ast.For):
                defined.update(self._extract_names_from_target(node.target))
            # with ... as var
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars:
                        defined.update(self._extract_names_from_target(item.optional_vars))

            # 名称使用
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    used.add(node.id)

        # 排除函数名和类名（不是变量）
        func_names = {f["name"] for f in self._extract_functions()}
        class_names = {c["name"] for c in self._extract_classes()}
        defined -= func_names - class_names

        unused = defined - used - func_names - class_names
        # 排除下划线变量（通常表示故意不使用）
        unused = {v for v in unused if not v.startswith("_")}

        return {"defined": sorted(defined), "used": sorted(used), "unused": sorted(unused)}

    def _extract_imports(self) -> list[str]:
        """提取所有导入的模块"""
        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(a.name for a in node.names)
                imports.append(f"{module}.{names}" if module else names)
        return imports

    def _analyze_control_flow(self) -> dict:
        """统计控制流结构"""
        counts = {
            "for_loops": 0,
            "while_loops": 0,
            "if_stmts": 0,
            "try_excepts": 0,
            "list_comprehensions": 0,
        }
        for node in ast.walk(self.tree):
            if isinstance(node, ast.For):
                counts["for_loops"] += 1
            elif isinstance(node, ast.While):
                counts["while_loops"] += 1
            elif isinstance(node, ast.If):
                counts["if_stmts"] += 1
            elif isinstance(node, ast.Try):
                counts["try_excepts"] += 1
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                counts["list_comprehensions"] += 1
        return counts

    def _calc_complexity(self) -> int:
        """计算圈复杂度（McCabe Cyclomatic Complexity）"""
        complexity = 1
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            # 列表推导式中 if 视为条件分支
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                for generator in node.generators:
                    complexity += len(generator.ifs)
            elif isinstance(node, ast.DictComp):
                for generator in node.generators:
                    complexity += len(generator.ifs)
        return complexity

    def _detect_common_issues(self) -> list[dict]:
        """检测常见代码问题"""
        issues = []
        lines = self.source_code.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 裸 except
            if stripped == "except:" or stripped.startswith("except:"):
                issues.append({
                    "severity": "warning",
                    "title": "裸 except 捕获",
                    "line": i,
                    "message": "使用裸 except 会捕获所有异常（包括 KeyboardInterrupt），建议指定具体异常类型。",
                })

            # 使用 mutable 默认参数
            if "def " in stripped and ("=[]" in stripped or "={}" in stripped):
                issues.append({
                    "severity": "error",
                    "title": "可变默认参数",
                    "line": i,
                    "message": "使用列表/字典作为默认参数会在多次调用间共享状态，建议使用 None 作为默认值。",
                })

            # 变量名覆盖内置函数
            builtins = {"list", "dict", "set", "tuple", "str", "int", "float", "bool",
                        "type", "id", "input", "print", "len", "range", "sum", "max", "min",
                        "abs", "map", "filter", "zip", "enumerate", "sorted", "reversed"}
            for name in builtins:
                if stripped.startswith(f"{name} =") or f" {name} =" in stripped:
                    if not stripped.startswith("#"):
                        issues.append({
                            "severity": "warning",
                            "title": "覆盖内置名称",
                            "line": i,
                            "message": f"变量名 `{name}` 覆盖了 Python 内置函数/类型，可能导致后续调用出错。",
                        })
                        break

        # 检查过长的函数（> 50 行）
        for func in self._extract_functions():
            line_count = func["end_lineno"] - func["lineno"] + 1
            if line_count > 50:
                issues.append({
                    "severity": "warning",
                    "title": "函数过长",
                    "line": func["lineno"],
                    "message": f"函数 `{func['name']}` 共 {line_count} 行，超过 50 行，建议拆分为更小的函数。",
                })

        # 检查过深的嵌套（> 4 层）
        max_depth = self._max_nesting_depth(self.tree)
        if max_depth > 4:
            issues.append({
                "severity": "info",
                "title": "嵌套层级过深",
                "line": 0,
                "message": f"代码最大嵌套深度为 {max_depth} 层，超过 4 层，建议使用 early return 或提取子函数。",
            })

        return issues

    # ------------------------------------------------------------------
    #  辅助方法
    # ------------------------------------------------------------------
    def _get_annotation_str(self, node) -> str:
        if node is None:
            return ""
        return ast.unparse(node) if hasattr(ast, "unparse") else ""

    def _get_name_str(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name_str(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name_str(node.value)}[...]"
        return ""

    def _extract_names_from_target(self, target) -> set[str]:
        names = set()
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
            for elt in target.elts:
                names.update(self._extract_names_from_target(elt))
        elif isinstance(target, ast.Starred):
            names.update(self._extract_names_from_target(target.value))
        return names

    def _get_called_functions(self, func_node) -> list[str]:
        """获取函数体内调用的所有函数名"""
        calls = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return sorted(calls)

    def _max_nesting_depth(self, tree: ast.AST) -> int:
        """计算代码的最大嵌套深度"""
        max_depth = 0

        def _walk(node, depth):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.For, ast.While, ast.If, ast.With, ast.Try)):
                    _walk(child, depth + 1)
                else:
                    _walk(child, depth)

        _walk(tree, 0)
        return max_depth

    def _build_error_report(self) -> str:
        """当代码存在语法错误时，返回错误报告"""
        lines = [
            "### 语法错误",
            f"代码存在语法错误，无法完成 AST 分析：",
            f"",
            f"```",
            f"{self.parse_error}",
            f"```",
            f"",
            f"**建议：** 请先修复语法错误后再进行分析。常见原因包括：",
            f"- 缺少冒号 `:`",
            f"- 缩进不正确",
            f"- 括号不匹配",
            f"- 关键字拼写错误",
        ]
        return "\n".join(lines)
