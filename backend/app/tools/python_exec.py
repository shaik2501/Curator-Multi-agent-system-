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


def run_python(code: str) -> ExecResult:
    """Execute `code` in a sandboxed subprocess and return its result."""
    _ISOLATION_HOOK = (
        "import sys\n"
        "def __audit_hook(name, args):\n"
        "    if name == 'socket.connect':\n"
        "        raise PermissionError('Network access is blocked in sandbox')\n"
        "sys.addaudithook(__audit_hook)\n\n"
    )

    lines = code.split('\n')
    future_imports = []
    rest = []

    for line in lines:
        if line.startswith('from __future__ import'):
            future_imports.append(line)
        else:
            rest.append(line)

    code = '\n'.join(future_imports) + ('\n' if future_imports else '') + _ISOLATION_HOOK + '\n'.join(rest)

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "snippet.py"
        script_path.write_text(code, encoding="utf-8")

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
