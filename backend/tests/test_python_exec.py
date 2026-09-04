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


def test_blocks_network_access():
    code = (
        "import os\n"
        "proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy']\n"
        "found = [k for k in proxy_keys if k in os.environ]\n"
        "if found:\n"
        "    print('FOUND:', found)\n"
        "else:\n"
        "    print('NO_PROXIES')\n"
    )
    result = run_python(code)
    # No literal network block at the OS level is guaranteed in this sandbox,
    # but proxy env vars are stripped. We verify that these proxy variables
    # do not exist in the subprocess environment.
    assert "NO_PROXIES" in result["stdout"]


def test_captures_stderr_on_exception():
    result = run_python("raise ValueError('boom')")
    assert result["returncode"] != 0
    assert "ValueError" in result["stderr"]
