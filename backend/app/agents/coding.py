"""Coding agent: writes and runs small Python snippets via the sandboxed tool."""
from __future__ import annotations

import re

from app.llm import ProviderUnavailable, get_llm, invoke_llm
from app.state import Note, ResearchState
from app.tools.python_exec import run_python

SYSTEM_PROMPT = """You are the Coding Agent on a research team.
Given a task, write a short, self-contained Python snippet (using only the
standard library — no network access is available) that computes or
demonstrates what's needed. Respond with ONLY a python code block:

```python
<code>
```
"""

SUMMARY_PROMPT = """You are the Coding Agent. Given the code you wrote and its
output, write a short note (2-5 sentences) describing what it computed/showed
and the key result. Plain text, no code fences."""


def _extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def run(state: ResearchState, task: str) -> Note:
    provider_config_id = state.get("agent_configs", {}).get("coding", "")

    try:
        llm = get_llm(provider_config_id=provider_config_id)
        response = invoke_llm(
            llm,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Task: {task}"},
            ]
        )
        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        code = _extract_code(content)
    except ProviderUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        return Note(agent="coding", content=f"(Coding agent LLM call failed: {exc})", sources=[])

    result = run_python(code)
    result_text = (
        f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}\n"
        f"returncode: {result['returncode']} timed_out: {result['timed_out']}"
    )

    try:
        llm = get_llm(provider_config_id=provider_config_id)
        summary_resp = invoke_llm(
            llm,
            [
                {"role": "system", "content": SUMMARY_PROMPT},
                {
                    "role": "user",
                    "content": f"Task: {task}\n\nCode:\n{code}\n\nResult:\n{result_text}",
                },
            ]
        )
        summary = summary_resp.content if hasattr(summary_resp, "content") else str(summary_resp)
        if isinstance(summary, list):
            summary = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in summary
            )
    except ProviderUnavailable:
        raise
    except Exception:  # noqa: BLE001
        summary = f"Ran code for task '{task}'. Result:\n{result_text[:800]}"

    full_content = f"{summary}\n\n```python\n{code}\n```\n\nOutput:\n{result_text}"
    return Note(agent="coding", content=full_content, sources=[])
