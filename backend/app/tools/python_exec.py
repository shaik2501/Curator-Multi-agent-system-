"""Sandboxed Python execution tool.

Runs untrusted code in a subprocess: 10s timeout, temp-dir cwd, no network
(proxy env vars stripped, python invoked with -I isolated mode).
"""
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

TIMEOUT_SECONDS = 10


class ExecResult(TypedDict):
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool


_NETWORK_ENV_KEYS_TO_STRIP = {
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
}


def _inject_audit_hook(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    insert_line = 1
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            insert_line = node.end_lineno + 1
        elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
            insert_line = node.end_lineno + 1
        else:
            break

    lines = code.split("\n")
    hook_lines = [
        "import sys as __sys",
        "def __sandbox_audit_hook(event, args):",
        "    if event.startswith('socket.'):",
        "        raise RuntimeError('Network access is blocked')",
        "__sys.addaudithook(__sandbox_audit_hook)"
    ]

    idx = insert_line - 1
    return "\n".join(lines[:idx] + hook_lines + lines[idx:])

def run_python(code: str) -> ExecResult:
    """Execute `code` in a sandboxed subprocess and return its result."""
    code_with_hook = _inject_audit_hook(code)
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "snippet.py"
        script_path.write_text(code_with_hook, encoding="utf-8")

        env = {
            k: v
            for k, v in __import__("os").environ.items()
            if k not in _NETWORK_ENV_KEYS_TO_STRIP
        }
        # Minimize inherited environment further while keeping PATH so the
        # interpreter itself can be located.
        env = {"PATH": env.get("PATH", "")}

        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script_path)],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
            return ExecResult(
                stdout=proc.stdout[-20_000:],
                stderr=proc.stderr[-20_000:],
                returncode=proc.returncode,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecResult(
                stdout=(exc.stdout or ""),
                stderr=(exc.stderr or "") + "\n[timed out after 10s]",
                returncode=-1,
                timed_out=True,
            )
