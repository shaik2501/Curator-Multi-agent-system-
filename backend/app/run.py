"""CLI: python -m app.run "goal" --provider-config-id <id>

Runs the full graph end-to-end and prints the final report. Provider
credentials now come from saved LLMConfig rows (app/db.py), not env vars —
use `python -m app.run --list-configs` to see available ids (e.g. one seeded
from .env on first startup).

Per-role assignment: the API lets each of the 7 agent roles use a different
saved config (ResearchState.agent_configs). This CLI is a single-config
convenience wrapper — the one --provider-config-id you pass is applied to
every role. For genuinely mixed per-role assignment, use the API directly.
"""
from __future__ import annotations

import argparse
import sys

from app import db
from app.graph import build_graph, new_run_id
from app.llm import ProviderUnavailable, check_config_available
from app.llm_configs import to_public_dict
from app.state import AGENT_ROLES, new_state
from app.tools.search import reset_run_search_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Curator end-to-end from the CLI.")
    parser.add_argument("goal", nargs="?", help="Research goal")
    parser.add_argument(
        "--provider-config-id",
        help="id of a saved LLMConfig row, applied to every agent role",
    )
    parser.add_argument(
        "--list-configs", action="store_true", help="List saved LLM configs and exit"
    )
    args = parser.parse_args()

    db.init_db()

    if args.list_configs:
        for config in db.list_llm_configs():
            print(to_public_dict(config))
        return

    if not args.goal:
        parser.error("goal is required unless --list-configs is given")
    if not args.provider_config_id:
        parser.error("--provider-config-id is required unless --list-configs is given")

    run_id = new_run_id()
    config = db.get_llm_config(args.provider_config_id)
    if config is None:
        print(f"Run failed: LLM config {args.provider_config_id!r} not found.", file=sys.stderr)
        sys.exit(1)

    agent_configs = {role: config.id for role in AGENT_ROLES}
    snapshot = {
        role: {"config_id": config.id, "provider_type": config.provider_type, "label": config.label}
        for role in AGENT_ROLES
    }
    db.create_run(run_id, args.goal, snapshot)

    try:
        for role in AGENT_ROLES:
            check_config_available(agent_configs[role])
    except ProviderUnavailable as exc:
        db.update_run_status(run_id, "failed", error=str(exc))
        print(f"Run failed: {exc}", file=sys.stderr)
        raise

    reset_run_search_count(run_id)

    def print_callback(event_type: str, data: dict) -> None:
        print(f"[{event_type}] {data}", file=sys.stderr)

    graph = build_graph(callback=print_callback)
    state = new_state(run_id, args.goal, agent_configs)

    try:
        final_state = graph.invoke(state, {"recursion_limit": 100})
    except Exception as exc:  # noqa: BLE001
        db.update_run_status(run_id, "failed", error=str(exc))
        print(f"Run failed: {exc}", file=sys.stderr)
        raise

    report = final_state.get("report", "")
    db.update_run_status(run_id, "completed", report=report)
    print("\n===== FINAL REPORT =====\n")
    print(report)


if __name__ == "__main__":
    main()
