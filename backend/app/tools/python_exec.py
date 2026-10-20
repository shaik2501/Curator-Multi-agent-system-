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
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "snippet.py"
        script_path.write_text(code, encoding="utf-8")

        # Minimize inherited environment to just PATH so the interpreter itself
        # can be located, inherently stripping proxy env vars.
        env = {"PATH": __import__("os").environ.get("PATH", "")}

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
