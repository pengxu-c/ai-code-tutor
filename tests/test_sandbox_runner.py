import glob
import os
import tempfile

from analyzer.sandbox import SandboxRunner


def test_sandbox_runs_stdin_code_and_compares_output():
    runner = SandboxRunner(timeout=2, max_output=1024)
    try:
        result = runner.run_tests(
            "name = input()\nprint(f'hello {name}')",
            [{"input": "Ada", "expected": "hello Ada"}],
        )[0]
    finally:
        runner.cleanup()

    assert result.actual_output == "hello Ada\n"
    assert result.error == ""
    assert result.passed is True
    assert result.timeout is False
    assert runner._bootstrap_path is None


def test_sandbox_runs_function_calls_with_json_arguments():
    runner = SandboxRunner(timeout=2, max_output=1024)
    try:
        result = runner.run_tests(
            "def add(a, b):\n    return a + b",
            [{"input": "[2, 3]", "expected": "5"}],
            function_name="add",
        )[0]
    finally:
        runner.cleanup()

    assert result.actual_output == "5\n"
    assert result.passed is True


def test_sandbox_output_compare_ignores_line_whitespace_and_detects_failure():
    runner = SandboxRunner(timeout=2, max_output=1024)
    try:
        assert runner._compare_output("  a  \n\n b ", "a\nb") is True
        result = runner.run_tests(
            "print('actual')",
            [{"input": "", "expected": "expected"}],
        )[0]
    finally:
        runner.cleanup()

    assert result.actual_output == "actual\n"
    assert result.passed is False


def test_sandbox_blocks_dangerous_builtins_and_imports():
    runner = SandboxRunner(timeout=2, max_output=4096)
    try:
        open_result = runner.run_code("open('x.txt', 'w')")
        import_result = runner.run_code("import os\nprint(os.getcwd())")
    finally:
        runner.cleanup()

    assert "安全限制" in open_result.error
    assert "open" in open_result.error
    assert "安全限制" in import_result.error
    assert "os" in import_result.error


def test_sandbox_timeout_and_truncation():
    timeout_runner = SandboxRunner(timeout=1, max_output=1024)
    try:
        timeout_result = timeout_runner.run_code("while True:\n    pass")
    finally:
        timeout_runner.cleanup()

    assert timeout_result.timeout is True
    assert "代码执行超时" in timeout_result.error

    truncate_runner = SandboxRunner(timeout=2, max_output=10)
    try:
        truncate_result = truncate_runner.run_code("print('x' * 50)")
    finally:
        truncate_runner.cleanup()

    assert truncate_result.actual_output.startswith("xxxxxxxxxx")
    assert "输出已截断" in truncate_result.actual_output


def test_sandbox_cleanup_removes_bootstrap_file():
    runner = SandboxRunner(timeout=2, max_output=1024)
    path = runner._get_bootstrap_script()

    assert os.path.exists(path)
    runner.cleanup()
    assert runner._bootstrap_path is None
    assert not os.path.exists(path)


def test_no_workspace_sandbox_bootstrap_files_are_created():
    workspace_sandboxes = glob.glob(os.path.join(os.getcwd(), "sandbox_*.py"))
    temp_sandboxes = glob.glob(os.path.join(tempfile.gettempdir(), "sandbox_*.py"))

    assert workspace_sandboxes == []
    # Temp files from previous interrupted runs should not be produced by these tests.
    assert all(os.path.dirname(path) == tempfile.gettempdir() for path in temp_sandboxes)
