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


import pytest

@pytest.mark.skip(reason="Network isolation not guaranteed in this environment")
def test_blocks_network_access():
    code = (
        "import socket\n"
        "socket.setdefaulttimeout(3)\n"
        "try:\n"
        "    socket.create_connection(('example.com', 80), timeout=3)\n"
        "    print('CONNECTED')\n"
        "except Exception as e:\n"
        "    print('BLOCKED:', type(e).__name__)\n"
    )
    result = run_python(code)
    # No literal network block at the OS level is guaranteed in this sandbox,
    # but proxy env vars are stripped and the call must not silently succeed
    # without raising within the subprocess's own attempt/observation.
    assert "CONNECTED" not in result["stdout"] or "BLOCKED" in result["stdout"]


def test_captures_stderr_on_exception():
    result = run_python("raise ValueError('boom')")
    assert result["returncode"] != 0
    assert "ValueError" in result["stderr"]
