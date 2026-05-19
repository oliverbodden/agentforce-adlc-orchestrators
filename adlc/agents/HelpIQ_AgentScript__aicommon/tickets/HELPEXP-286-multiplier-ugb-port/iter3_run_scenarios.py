#!/usr/bin/env python3
"""
Iter 3 scenario runner — HELPEXP-286 Multiplier UGB.

Runs scripted multi-turn scenarios via `sf agent preview send`, captures raw
replies + Debug records, and dumps to JSON for manual grading.

Knowledge-retrieval scenarios use --use-live-actions so real Glean catalog data
is exercised (AC #5/#6). Flow-control-only scenarios use --simulate-actions to
save time.

Usage:
    python iter3_run_scenarios.py [--scenario <id>] [--only-sim]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCENARIOS = [
    {
        "id": "SW-CONFIRM-01-figma-happy-path",
        "mode": "live",
        "category": "straightforward-action-Confirm-Submit",
        "primary_acs": ["AC #2", "AC #5", "AC #7"],
        "script": [
            "I need figma access so I can edit design mocks for my team's Monday launch",
            # depending on retrieval shape, either "Editor please" (multi-option) or "yes" (single-option)
            "Editor please",
            "yes go ahead",
        ],
    },
    {
        "id": "SW-CLARIFY-01-zoom-vs-zoom-phone",
        "mode": "live",
        "category": "qualifier-disambiguation",
        "primary_acs": ["AC #4", "AC #6"],
        "script": [
            "I need Zoom",
            # branch into Zoom Phone
            "Zoom Phone",
            "for calling our enterprise customers",
            "yes",
        ],
    },
    {
        "id": "SW-CLARIFY-03-tableau-multi-license",
        "mode": "live",
        "category": "multi-license-tier + multi-option-retrieval",
        "primary_acs": ["AC #4", "AC #6"],
        "script": [
            "I need Tableau access for building dashboards",
            # pick the tier we want
            "Creator",
            "yes",
        ],
    },
    {
        "id": "SW-ANSWER-01-zoom-info-not-action",
        "mode": "live",
        "category": "auto-provisioned-Answer-path",
        "primary_acs": ["AC #3"],
        "script": [
            "is Zoom auto-provisioned at the company or do I need to request access?",
        ],
    },
    {
        "id": "SW-CONFIRM-02-cursor-product",
        "mode": "live",
        "category": "straightforward-action-Confirm-Submit + product-diversity",
        "primary_acs": ["AC #2", "AC #4 distribution", "AC #5"],
        "script": [
            "I need Cursor access to start using AI coding tools",
            "yes please go ahead",
        ],
    },
    {
        "id": "SW-ESCALATE-01-catalog-miss",
        "mode": "live",
        "category": "escalate-path",
        "primary_acs": ["AC #4 Escalate"],
        "script": [
            "I need access to a tool called BananaFlow Pro 9000 for analytics",
        ],
    },
    {
        "id": "SW-VAGUE-01-no-app-named",
        "mode": "sim",
        "category": "UNDERSTAND-skip-GATHER",
        "primary_acs": ["AC #4 Clarify"],
        "script": [
            "I need software access",
        ],
    },
    {
        "id": "SW-CONFIRM-BROKEN-01-ok-after-clarify",
        "mode": "sim",
        "category": "ConfirmChain-subtle-break",
        "primary_acs": ["AC #2 subtle"],
        "script": [
            "I need access to Glean",
            # Glean is single-option likely; if Clarify comes back, "ok" is ambiguous and should NOT trigger Submit
            "ok",
        ],
    },
]


def run_sf(args: list[str], timeout: int = 240) -> dict:
    """Run sf CLI command, return parsed JSON."""
    proc = subprocess.run(
        ["sf"] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "_error": "json-parse-fail",
            "stdout": proc.stdout[:2000],
            "stderr": proc.stderr[:1000],
            "returncode": proc.returncode,
        }


def start_session(mode: str) -> str | None:
    flag = "--simulate-actions" if mode == "sim" else "--use-live-actions"
    result = run_sf(
        ["agent", "preview", "start", "--json", "--authoring-bundle", "HelpIQ_AgentScript", flag],
        timeout=60,
    )
    if result.get("status") == 0:
        return result.get("result", {}).get("sessionId")
    print(f"  ! start failed: {result}", file=sys.stderr)
    return None


def send_turn(session_id: str, utterance: str) -> dict:
    result = run_sf(
        [
            "agent", "preview", "send", "--json",
            "--session-id", session_id,
            "--authoring-bundle", "HelpIQ_AgentScript",
            "--utterance", utterance,
        ],
        timeout=240,
    )
    return result


def extract_reply(send_result: dict) -> str:
    msgs = send_result.get("result", {}).get("messages", [])
    for m in msgs:
        if m.get("type") in ("Inform", "Reply"):
            return m.get("message", "")
    return ""


def extract_session_trace_id(send_result: dict) -> str | None:
    return send_result.get("result", {}).get("sessionTraceId")


def run_scenario(scenario: dict, results_dir: Path) -> dict:
    sid = start_session(scenario["mode"])
    if sid is None:
        return {"id": scenario["id"], "status": "session-start-failed"}

    turns = []
    for i, utterance in enumerate(scenario["script"]):
        t0 = time.time()
        send_result = send_turn(sid, utterance)
        elapsed = time.time() - t0
        reply = extract_reply(send_result)
        turns.append({
            "turn": i + 1,
            "utterance": utterance,
            "reply": reply,
            "trace_id": extract_session_trace_id(send_result),
            "elapsed_s": round(elapsed, 1),
            "send_status": send_result.get("status", "unknown"),
        })
        print(f"  turn {i+1} done ({elapsed:.0f}s)")

    return {
        "id": scenario["id"],
        "mode": scenario["mode"],
        "category": scenario["category"],
        "primary_acs": scenario["primary_acs"],
        "session_id": sid,
        "turns": turns,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="run only this scenario ID")
    parser.add_argument("--only-sim", action="store_true", help="skip live-action scenarios")
    parser.add_argument("--only-live", action="store_true", help="skip simulator scenarios")
    args = parser.parse_args()

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = results_dir / f"iter3-scenarios-{ts}.json"

    scenarios = SCENARIOS
    if args.scenario:
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
    if args.only_sim:
        scenarios = [s for s in scenarios if s["mode"] == "sim"]
    if args.only_live:
        scenarios = [s for s in scenarios if s["mode"] == "live"]

    print(f"Running {len(scenarios)} scenarios; output → {out_path.name}")
    print()

    runs = []
    for s in scenarios:
        print(f"[{s['id']}] mode={s['mode']} category={s['category']}")
        run = run_scenario(s, results_dir)
        runs.append(run)
        with out_path.open("w") as f:
            json.dump({"started_at": ts, "scenarios": runs}, f, indent=2)
        print()

    print(f"Done. {len(runs)} scenarios; results in {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
