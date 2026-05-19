#!/usr/bin/env python3
"""
Production bug repros against v8 working draft.

Runs 4 scenarios derived from real April 2026 production chats to determine
which production bugs are actually still present in the current v8 deployed
state vs. which have been fixed by iter-5/iter-15 structural work.

Each scenario uses --simulate-actions so no real JSM tickets are created.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCENARIOS = [
    {
        "id": "REPRO-1-off-topic-refusal",
        "bug": "#4 off-topic mis-classification (HelpIQ refuses with 'Salesforce-related topics' error)",
        "source_chat": "019d6dc4 turn 1",
        "expected_v8": "agent should NOT refuse as off-topic; should route to multiplier and start gather",
        "script": [
            "I need the slack access token and secret in order to connect the slack for the workflow in the n8n prd instance. Can you please create the ticket?",
        ],
    },
    {
        "id": "REPRO-2-seismic-confirm-gate",
        "bug": "#1 AC #2 Confirm-gate violation on Seismic (prod submitted without Confirm)",
        "source_chat": "019d9103",
        "expected_v8": "after picking access type, agent should produce Confirm summary 'Submit this request? (yes / no)' BEFORE firing Submit",
        "script": [
            "how can I set up seismic? It doesnt give me the option to integrate it via external credentials",
            "Create a ticket for IT Specialist help",
            "Regular user access for me to access standard sales content",
        ],
    },
    {
        "id": "REPRO-3-google-workspace-catalog-miss",
        "bug": "#2 catalog miss dumps user (no escalation route offered)",
        "source_chat": "019d4ead (Google Developers/Payments)",
        "expected_v8": "agent should recognize catalog miss + offer escalation + gather reason — NOT just say 'you may need to reach out to IT support team' and end",
        "script": [
            "I need access to the Google Developers and Google Payments groups to publish an internal extension",
        ],
    },
    {
        "id": "REPRO-4-datadog-existing-app-loophole",
        "bug": "#5 existing-app silent-failure (no beneficiary mention; ticket files for requester instead of intended user)",
        "source_chat": "discovery transcript Dario Sanchez example",
        "expected_v8": "after collecting access type and reason for 'datadog access' with no beneficiary mention, agent should produce Confirm summary; on yes, Submit fires for SESSION user (architectural limitation — there is no 'does user already have access?' check, so the bug should still be present)",
        "script": [
            "I need datadog access",
            "to monitor my service metrics",
            "yes",
        ],
    },
]


def run_sf(args: list[str], timeout: int = 240) -> dict:
    proc = subprocess.run(
        ["sf"] + args, capture_output=True, text=True, timeout=timeout,
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


def start_session() -> str | None:
    result = run_sf(
        ["agent", "preview", "start", "--json",
         "--authoring-bundle", "HelpIQ_AgentScript",
         "--simulate-actions"],
        timeout=60,
    )
    if result.get("status") == 0:
        return result.get("result", {}).get("sessionId")
    print(f"  ! start failed: {result}", file=sys.stderr)
    return None


def send_turn(session_id: str, utterance: str) -> dict:
    return run_sf(
        ["agent", "preview", "send", "--json",
         "--session-id", session_id,
         "--authoring-bundle", "HelpIQ_AgentScript",
         "--utterance", utterance],
        timeout=240,
    )


def extract_reply(send_result: dict) -> str:
    msgs = send_result.get("result", {}).get("messages", [])
    for m in msgs:
        if m.get("type") in ("Inform", "Reply"):
            return m.get("message", "")
    return ""


def extract_trace_id(send_result: dict) -> str | None:
    return send_result.get("result", {}).get("sessionTraceId")


def run_one(scenario: dict) -> dict:
    print(f"[{scenario['id']}] bug={scenario['bug'][:80]}")
    sid = start_session()
    if sid is None:
        return {"id": scenario["id"], "status": "session-start-failed"}

    turns = []
    for i, utt in enumerate(scenario["script"]):
        t0 = time.time()
        send_result = send_turn(sid, utt)
        elapsed = time.time() - t0
        reply = extract_reply(send_result)
        turns.append({
            "turn": i + 1,
            "utterance": utt,
            "reply": reply,
            "trace_id": extract_trace_id(send_result),
            "elapsed_s": round(elapsed, 1),
            "send_status": send_result.get("status", "unknown"),
        })
        print(f"  turn {i+1} done ({elapsed:.0f}s) — reply length={len(reply)}")

    return {
        "id": scenario["id"],
        "bug": scenario["bug"],
        "source_chat": scenario["source_chat"],
        "expected_v8": scenario["expected_v8"],
        "session_id": sid,
        "turns": turns,
    }


def main() -> int:
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"prod-bug-repro-{ts}.json"

    print(f"Running {len(SCENARIOS)} scenarios; output → {out_path.name}\n")

    runs = []
    for s in SCENARIOS:
        run = run_one(s)
        runs.append(run)
        with out_path.open("w") as f:
            json.dump({"started_at": ts, "scenarios": runs}, f, indent=2)
        print()

    print(f"Done. Results in {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
