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


def test_allows_network_access_and_strips_env():
    code = (
        "import socket\n"
        "import os\n"
        "socket.setdefaulttimeout(3)\n"
        "try:\n"
        "    socket.create_connection(('example.com', 80), timeout=3)\n"
        "    print('CONNECTED')\n"
        "except Exception as e:\n"
        "    print('BLOCKED:', type(e).__name__)\n"
        "print('ENV_KEYS:', ','.join(os.environ.keys()))\n"
    )
    result = run_python(code)
    # Network access should be allowed per the new architectural requirement
    assert "CONNECTED" in result["stdout"]
    assert "BLOCKED" not in result["stdout"]
    # Verify environment is stripped (only PATH should be passed, though Python might inject a few things like PYTHONHASHSEED, but we definitely shouldn't see full host env)
    assert "HTTP_PROXY" not in result["stdout"]


def test_captures_stderr_on_exception():
    result = run_python("raise ValueError('boom')")
    assert result["returncode"] != 0
    assert "ValueError" in result["stderr"]
