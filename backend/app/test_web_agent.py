"""CLI: python -m app.test_web_agent "topic" --provider-config-id <id>

Exercises the Web Agent alone as a mini pipeline: search -> fetch -> summarize
with sources. Used for Phase 1 manual verification. Provider credentials come
from a saved LLMConfig row (app/db.py) — use
`python -m app.run --list-configs` to see available ids.
"""
from __future__ import annotations

import argparse

from app import db
from app.agents import web as web_agent
from app.state import new_state
from app.tools.search import reset_run_search_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Web Agent alone against a topic.")
    parser.add_argument("topic", help="Topic to research")
    parser.add_argument("--provider-config-id", required=True, help="id of a saved LLMConfig row")
    args = parser.parse_args()

    db.init_db()

    run_id = "test-web-agent"
    reset_run_search_count(run_id)
    state = new_state(run_id, args.topic, {"web": args.provider_config_id})

    note = web_agent.run(state, args.topic)

    print("\n===== WEB AGENT SUMMARY =====\n")
    print(note.content)
    print("\n===== SOURCES =====\n")
    for src in note.sources:
        print(f"- {src}")


if __name__ == "__main__":
    main()
