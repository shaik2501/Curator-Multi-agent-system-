"""Sandboxed Python execution tool.

Runs untrusted code in a subprocess: 10s timeout, temp-dir cwd, no network
(proxy env vars stripped, python invoked with -I isolated mode).
"""
from __future__ import annotations

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


def run_python(code: str) -> ExecResult:
    """Execute `code` in a sandboxed subprocess and return its result."""
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "snippet.py"
        script_path.write_text(code, encoding="utf-8")

        wrapper_path = Path(tmpdir) / "wrapper.py"
        wrapper_code = """
import sys
import runpy

def audit_hook(event, args):
    if event == "socket.connect" or event == "socket.getaddrinfo":
        raise PermissionError("Network access is blocked in this sandbox.")

sys.addaudithook(audit_hook)
runpy.run_path("snippet.py", run_name="__main__")
"""
        wrapper_path.write_text(wrapper_code, encoding="utf-8")

        # Minimize inherited environment further while keeping PATH so the
        # interpreter itself can be located.
        env = {"PATH": os.environ.get("PATH", "")}

        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(wrapper_path)],
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
