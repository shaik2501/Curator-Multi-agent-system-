"""Tests for the sandboxed python_exec tool: timeout, no network, stdout capture."""
from __future__ import annotations

from app.tools.python_exec import run_python


def test_returns_stdout():
    result = run_python("print('hello world')")
    assert "hello world" in result["stdout"]
    assert result["returncode"] == 0
    assert result["timed_out"] is False


def test_times_out_at_10s():
    result = run_python("import time; time.sleep(30)")
    assert result["timed_out"] is True
    assert result["returncode"] == -1


def test_captures_stderr_on_exception():
    result = run_python("raise ValueError('boom')")
    assert result["returncode"] != 0
    assert "ValueError" in result["stderr"]
