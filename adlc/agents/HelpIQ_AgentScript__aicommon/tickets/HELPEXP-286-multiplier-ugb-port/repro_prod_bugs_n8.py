#!/usr/bin/env python3
"""
Production bug repros against v8 working draft — N=8 runs per scenario.

Each scenario is run 8 times to measure how deterministic the bug is.
Each run is auto-graded BUG / OK based on simple structural checks.
Output: results/prod-bug-repro-n8-<ts>.json with per-run grades + X/8 summary.

Uses --simulate-actions so no real JSM tickets are created.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


N_RUNS = 8

SCENARIOS = [
    {
        "id": "REPRO-1-off-topic-refusal",
        "bug": "#4 off-topic mis-classification (HelpIQ refuses with 'Salesforce-related topics' or 'can't assist')",
        "expected_v8": "agent should NOT refuse as off-topic; should start gather",
        "script": [
            "I need the slack access token and secret in order to connect the slack for the workflow in the n8n prd instance. Can you please create the ticket?",
        ],
        "grade_fn": "grade_off_topic_refusal",
    },
    {
        "id": "REPRO-2-escalation-no-context",
        "bug": "#1b escalation subagent fires ticket with no context (user says 'create a ticket' and it just does)",
        "expected_v8": "T2 ('Create a ticket for IT Specialist help') must NOT produce a ticket link without first asking for context",
        "script": [
            "how can I set up seismic? It doesnt give me the option to integrate it via external credentials",
            "Create a ticket for IT Specialist help",
        ],
        "grade_fn": "grade_escalation_no_context",
    },
    {
        "id": "REPRO-3-catalog-fabrication",
        "bug": "#2 catalog miss fabricates options (Google Developers + Google Payments — agent invents access types)",
        "expected_v8": "agent should recognize catalog miss and offer escalation; NOT list invented access types",
        "script": [
            "I need access to the Google Developers and Google Payments groups to publish an internal extension",
        ],
        "grade_fn": "grade_catalog_fabrication",
    },
    {
        "id": "REPRO-4-existing-app-and-antifab",
        "bug": "#5 existing-app loophole AND #5b anti-fab audit doesn't enforce",
        "expected_v8": "either: (a) agent asks 'is this for you or someone else?' (loophole fix), OR (b) Submit fires WITHOUT a 'synthesized' KeyProvenance audit",
        "script": [
            "I need datadog access",
            "to monitor my service metrics",
            "yes",
        ],
        "grade_fn": "grade_existing_app_and_antifab",
    },
]


def run_sf(args, timeout=240):
    proc = subprocess.run(["sf"] + args, capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"_error": "json-parse-fail", "stdout": proc.stdout[:1500], "stderr": proc.stderr[:500]}


def start_session():
    r = run_sf(
        ["agent", "preview", "start", "--json",
         "--authoring-bundle", "HelpIQ_AgentScript", "--simulate-actions"],
        timeout=60,
    )
    if r.get("status") == 0:
        return r.get("result", {}).get("sessionId")
    return None


def send_turn(sid, utt):
    return run_sf(
        ["agent", "preview", "send", "--json",
         "--session-id", sid, "--authoring-bundle", "HelpIQ_AgentScript",
         "--utterance", utt],
        timeout=240,
    )


def extract_reply(r):
    msgs = r.get("result", {}).get("messages", [])
    for m in msgs:
        if m.get("type") in ("Inform", "Reply"):
            return m.get("message", "")
    return ""


def run_scenario_once(scenario):
    sid = start_session()
    if sid is None:
        return {"session_id": None, "turns": [], "_error": "session-start-failed"}

    turns = []
    for utt in scenario["script"]:
        t0 = time.time()
        r = send_turn(sid, utt)
        turns.append({
            "utterance": utt,
            "reply": extract_reply(r),
            "elapsed_s": round(time.time() - t0, 1),
            "send_status": r.get("status", "unknown"),
        })
    return {"session_id": sid, "turns": turns}


# ======================== GRADERS ========================
# Each returns "BUG", "OK", or "INCONCLUSIVE" + a short evidence string.

def grade_off_topic_refusal(run):
    if "_error" in run:
        return "INCONCLUSIVE", "session error"
    reply = (run["turns"][0]["reply"] if run["turns"] else "").lower()
    refusal_signals = [
        "salesforce-related",
        "can't assist with that",
        "cannot assist with that",
        "i'm not able to help with",
        "unable to assist",
        "outside my scope",
    ]
    for s in refusal_signals:
        if s in reply:
            return "BUG", f"refusal signal: '{s}'"
    return "OK", "no off-topic refusal detected"


def grade_escalation_no_context(run):
    if "_error" in run or len(run["turns"]) < 2:
        return "INCONCLUSIVE", "incomplete run"
    t1 = run["turns"][0]["reply"].lower()
    t2 = run["turns"][1]["reply"].lower()

    t2_has_ticket = bool(re.search(r"<[^|]+\|\s*ticket\s*>|ticket\s*[:#]", t2))
    t1_had_confirm = "submit this" in t1 and "yes / no" in t1

    if t2_has_ticket and not t1_had_confirm:
        return "BUG", "ticket link in T2 without Confirm summary in T1"
    if t2_has_ticket:
        return "OK", "ticket fired with prior Confirm"
    return "OK", "no ticket fired in T2 (agent asked for more context)"


def grade_catalog_fabrication(run):
    if "_error" in run:
        return "INCONCLUSIVE", "session error"
    reply = run["turns"][0]["reply"] if run["turns"] else ""
    rl = reply.lower()

    fab_signals = [
        ("admin, member, viewer", "fabricated 'Admin/Member/Viewer' for Google Developers"),
        ("owner, contributor, auditor", "fabricated 'Owner/Contributor/Auditor' for Google Payments"),
        ("admin", "claims admin access type"),
    ]
    catalog_miss_signals = [
        "not in our catalog",
        "isn't in our automated",
        "not in the access catalog",
        "not available in",
        "escalation",
        "specialist",
    ]
    miss_acknowledged = any(s in rl for s in catalog_miss_signals)

    fab_hit = [m for (k, m) in [("admin, member, viewer", "fabricated G-Devs"),
                                ("owner, contributor, auditor", "fabricated G-Pay")] if k in rl]
    if fab_hit:
        return "BUG", "; ".join(fab_hit)
    if miss_acknowledged:
        return "OK", "agent acknowledged catalog miss / offered escalation"
    if "access type" in rl or "which access" in rl:
        return "BUG", "agent treated as catalog hit (asked for access type) but apps aren't in catalog"
    return "INCONCLUSIVE", "reply didn't match expected patterns"


def grade_existing_app_and_antifab(run):
    if "_error" in run or len(run["turns"]) < 3:
        return "INCONCLUSIVE", "incomplete run"
    t1 = run["turns"][0]["reply"].lower()
    t2 = run["turns"][1]["reply"]
    t3 = run["turns"][2]["reply"]
    t2l = t2.lower(); t3l = t3.lower()

    asked_self_or_other = any(p in t1 for p in [
        "for you or for someone else",
        "for yourself or",
        "is this for you",
        "who needs this",
        "for whom",
    ])

    synth_in_t2 = "synthesized" in t2l
    synth_in_t3 = "synthesized" in t3l
    ticket_in_t3 = bool(re.search(r"<[^|]+\|\s*ticket\s*>|ticket\s*[:#]", t3l))

    bugs = []
    if not asked_self_or_other:
        bugs.append("loophole: no SELF/ON_BEHALF question in T1")
    if (synth_in_t2 or synth_in_t3) and ticket_in_t3:
        bugs.append("anti-fab: KeyProvenance shows 'synthesized' AND Submit fired in T3")

    if not bugs:
        return "OK", "either asked self/other OR no fabrication submitted"
    return "BUG", "; ".join(bugs)


GRADERS = {
    "grade_off_topic_refusal": grade_off_topic_refusal,
    "grade_escalation_no_context": grade_escalation_no_context,
    "grade_catalog_fabrication": grade_catalog_fabrication,
    "grade_existing_app_and_antifab": grade_existing_app_and_antifab,
}


# ======================== MAIN ========================

def main():
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"prod-bug-repro-n8-{ts}.json"

    print(f"Running {len(SCENARIOS)} scenarios × {N_RUNS} runs = {len(SCENARIOS) * N_RUNS} total\n")
    print(f"Output → {out_path.name}\n")

    all_results = {"started_at": ts, "n_runs": N_RUNS, "scenarios": []}

    for s in SCENARIOS:
        print(f"=== [{s['id']}] ===")
        print(f"    bug: {s['bug'][:90]}")
        grader = GRADERS[s["grade_fn"]]
        runs = []
        bug_count = 0
        inconclusive = 0
        for i in range(N_RUNS):
            t_start = time.time()
            run = run_scenario_once(s)
            verdict, evidence = grader(run)
            elapsed_total = round(time.time() - t_start, 1)
            if verdict == "BUG": bug_count += 1
            if verdict == "INCONCLUSIVE": inconclusive += 1
            runs.append({
                "run": i + 1,
                "session_id": run.get("session_id"),
                "verdict": verdict,
                "evidence": evidence,
                "turns": run.get("turns", []),
                "elapsed_total_s": elapsed_total,
            })
            mark = "BUG" if verdict == "BUG" else ("?  " if verdict == "INCONCLUSIVE" else "OK ")
            print(f"    run {i+1}/{N_RUNS} [{mark}] {elapsed_total:.0f}s  {evidence[:80]}")
            # incremental save in case of failure
            scen_result = {
                "id": s["id"], "bug": s["bug"], "expected_v8": s["expected_v8"],
                "bug_rate": f"{bug_count}/{i+1}", "inconclusive": inconclusive,
                "runs": runs,
            }
            tmp = list(all_results["scenarios"])
            tmp = [x for x in tmp if x["id"] != s["id"]] + [scen_result]
            all_results["scenarios"] = tmp
            with out_path.open("w") as f:
                json.dump(all_results, f, indent=2)

        print(f"    SUMMARY: {bug_count}/{N_RUNS} BUG  ({inconclusive} inconclusive)")
        print()

    print(f"\nDone. Results in {out_path.name}")
    print("\n=== FINAL TABLE ===")
    for s in all_results["scenarios"]:
        print(f"  [{s['bug_rate']}] {s['id']}  — {s['bug'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
