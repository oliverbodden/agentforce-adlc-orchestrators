#!/usr/bin/env python3
"""Re-audit open checklist rows against the live AB2 agent via `sf agent preview`.

Pass criterion per single-turn trial (derived from the master deep-dive expectations):
- ticket_action_called == false  (single-turn pack never expects a ticket on turn 1)
- qna_attempted == true          (the QnA-first router intent was honored)
- selected_route != Off_Topic    (the request was not written off)

A row's verdict aggregates N trials:
- Resolved: all trials pass with no execution errors
- BrokenSame: all trials fail in the same dominant mode as the original AB2 trial
- BrokenNew: all trials fail but in a different way than original AB2
- Flaky: 1..N-1 trials pass
- NeedsEyeball: any execution error, or expected route is multi-valued
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Reuse the existing preview helpers from the dynamic runner.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from run_dynamic_tests import (  # type: ignore
    end_session,
    extract_message,
    parse_debug,
    run_sf,
    start_session,
)


EVAL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT = "HelpIQ_AgentScript_AB2"


def _normalize(text: str) -> str:
    if text is None:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    # Drop curly quotes to align with checklist truncation
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return text


def load_deep_dive(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def parse_open_router_rows(checklist_path: Path) -> list[dict[str, str]]:
    """Extract numbered open rows from the ROUTER_TOPIC_UPDATE section of the checklist."""
    text = checklist_path.read_text()
    start_marker = "## ROUTER_TOPIC_UPDATE"
    end_marker = "## QNA_RAG_HANDLING"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("could not locate ROUTER_TOPIC_UPDATE section in checklist")
    section = text[start:end]
    rows = []
    # Match lines like `- **11. Hi. My laptop has stopped working...`
    pattern = re.compile(r"^- \*\*(\d+)\.\s+(.+?)\*\*\s*$", re.MULTILINE)
    for match in pattern.finditer(section):
        number = match.group(1)
        utterance_raw = match.group(2)
        # Strip trailing ellipsis that the checklist uses for truncation.
        utterance = utterance_raw.rstrip()
        if utterance.endswith("..."):
            utterance = utterance[:-3].rstrip()
        rows.append({
            "checklist_number": number,
            "utterance_prefix": utterance,
        })
    return rows


def join_to_deep_dive(rows: list[dict[str, str]], deep: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Match each checklist row to a deep-dive row by utterance prefix."""
    deep_by_norm = []
    for d in deep:
        deep_by_norm.append({"norm": _normalize(d["Utterance"]), "row": d})
    joined: list[dict[str, Any]] = []
    misses: list[str] = []
    duplicates: list[str] = []
    for row in rows:
        prefix_norm = _normalize(row["utterance_prefix"])
        # Allow markdown link rendering differences by stripping common patterns.
        prefix_simple = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", prefix_norm)
        candidates = [
            d for d in deep_by_norm
            if d["norm"].startswith(prefix_norm)
            or d["norm"].startswith(prefix_simple)
            or _normalize(re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", d["norm"])).startswith(prefix_simple)
        ]
        if not candidates:
            misses.append(f"#{row['checklist_number']}: {row['utterance_prefix'][:80]}")
            continue
        if len(candidates) > 1:
            duplicates.append(f"#{row['checklist_number']}: {row['utterance_prefix'][:80]} -> {len(candidates)} matches")
            continue
        d = candidates[0]["row"]
        joined.append({
            "row_id": f"ROUTER-{int(row['checklist_number']):03d}",
            "checklist_number": row["checklist_number"],
            "utterance": d["Utterance"],
            "utterance_prefix": row["utterance_prefix"],
            "expected_subagent": d["Expected Subagent (Master)"],
            "expected_action": d["Expected Action (Master)"],
            "regression_bucket": d["Regression Bucket"],
            "product": d["Product"],
            "category": d["Category"],
            "subcategory": d["Subcategory"],
            "ab2_original_actual_topics": d["AB2 Actual Topics"],
            "ab2_original_actual_actions": d["AB2 Actual Actions"],
            "ab2_original_topic_results": d["AB2 Topic Results"],
            "ab2_original_action_results": d["AB2 Action Results"],
        })
    return joined, misses, duplicates


def write_input_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_existing_attempts(jsonl_path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    existing: dict[tuple[str, int], dict[str, Any]] = {}
    if not jsonl_path.exists():
        return existing
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (obj.get("row_id"), int(obj.get("attempt", 0)))
            existing[key] = obj
    return existing


def grade_attempt(debug: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    selected = (debug.get("selected_route") or "").strip().lower()
    qna = (debug.get("qna_attempted") or "").strip().lower()
    ticket = (debug.get("ticket_action_called") or "").strip().lower()
    if ticket == "true":
        failures.append("ticket_action_called_true")
    if qna != "true":
        failures.append("qna_not_attempted")
    if selected.startswith("off_topic"):
        failures.append("selected_route_off_topic")
    return not failures, failures


def run_trial(agent: str, utterance: str) -> dict[str, Any]:
    started = time.time()
    error = None
    session_id = None
    response = ""
    debug: dict[str, Any] = {}
    try:
        session_id = start_session(agent)
        data = run_sf(
            [
                "agent", "preview", "send", "--json",
                "--authoring-bundle", agent,
                "--session-id", session_id,
                "--utterance", utterance,
            ],
            timeout=180,
        )
        response = extract_message(data)
        debug = parse_debug(response)
        if data.get("_returncode") != 0:
            error = data.get("raw") or data.get("_stderr") or "non_zero_returncode"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if session_id:
            try:
                end_session(agent, session_id)
            except Exception:
                pass
    elapsed_ms = int((time.time() - started) * 1000)
    passed, failure_reasons = grade_attempt(debug)
    if error:
        passed = False
        failure_reasons.append("execution_error")
    return {
        "session_id": session_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": elapsed_ms,
        "debug": debug,
        "agent_message": response,
        "criterion_passed": passed,
        "failure_reasons": failure_reasons,
        "error": error,
    }


def aggregate_verdicts(rows: list[dict[str, Any]], attempts: dict[tuple[str, int], dict[str, Any]], runs_per_row: int) -> list[dict[str, Any]]:
    verdicts = []
    for row in rows:
        row_attempts = []
        for n in range(1, runs_per_row + 1):
            entry = attempts.get((row["row_id"], n))
            if entry:
                row_attempts.append(entry)
        passes = sum(1 for a in row_attempts if a.get("criterion_passed"))
        errors = sum(1 for a in row_attempts if a.get("error"))
        total = len(row_attempts)
        failure_modes = [reason for a in row_attempts for reason in (a.get("failure_reasons") or [])]
        dominant_failure = max(set(failure_modes), key=failure_modes.count) if failure_modes else ""
        if errors > 0:
            verdict = "NeedsEyeball"
        elif total == 0:
            verdict = "NotRun"
        elif passes == total:
            verdict = "Resolved"
        elif passes == 0:
            ab2_orig = (row.get("ab2_original_actual_topics") or "").lower()
            if "off_topic" in ab2_orig and dominant_failure == "selected_route_off_topic":
                verdict = "BrokenSame"
            elif "ticket" in (row.get("ab2_original_actual_actions") or "").lower() and dominant_failure == "ticket_action_called_true":
                verdict = "BrokenSame"
            else:
                verdict = "BrokenNew"
        else:
            verdict = "Flaky"
        sample_passing = next((a for a in row_attempts if a.get("criterion_passed")), None)
        sample_failing = next((a for a in row_attempts if not a.get("criterion_passed")), None)
        verdicts.append({
            **row,
            "trials_run": total,
            "trials_passed": passes,
            "trial_errors": errors,
            "verdict": verdict,
            "dominant_failure": dominant_failure,
            "sample_passing_debug": (sample_passing or {}).get("debug"),
            "sample_failing_debug": (sample_failing or {}).get("debug"),
            "sample_passing_message": ((sample_passing or {}).get("agent_message") or "")[:1500],
            "sample_failing_message": ((sample_failing or {}).get("agent_message") or "")[:1500],
        })
    return verdicts


def write_summary_md(verdicts: list[dict[str, Any]], path: Path, runs_per_row: int) -> None:
    by_verdict: dict[str, list[dict[str, Any]]] = {}
    for v in verdicts:
        by_verdict.setdefault(v["verdict"], []).append(v)
    order = ["BrokenSame", "BrokenNew", "Flaky", "NeedsEyeball", "Resolved", "NotRun"]
    lines = [
        f"# Router Audit Summary",
        "",
        f"- Agent: `{verdicts[0].get('_agent', 'HelpIQ_AgentScript_AB2') if verdicts else 'n/a'}`",
        f"- Rows audited: {len(verdicts)}",
        f"- Trials per row: {runs_per_row}",
        f"- Audit timestamp: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Counts by Verdict",
        "",
        "| Verdict | Count |",
        "| --- | --- |",
    ]
    for verdict in order:
        if verdict in by_verdict:
            lines.append(f"| {verdict} | {len(by_verdict[verdict])} |")
    lines.append("")
    for verdict in order:
        if verdict not in by_verdict:
            continue
        lines.append(f"## {verdict} ({len(by_verdict[verdict])} rows)")
        lines.append("")
        for v in by_verdict[verdict]:
            lines.append(
                f"- **{v['row_id']}** (#{v['checklist_number']}, bucket=`{v['regression_bucket']}`, "
                f"product=`{v['product']} / {v['category']} / {v['subcategory']}`)"
            )
            lines.append(f"  - Utterance: `{v['utterance'][:200]}{'...' if len(v['utterance']) > 200 else ''}`")
            lines.append(
                f"  - Trials: passed={v['trials_passed']}/{v['trials_run']} "
                f"errors={v['trial_errors']} dominant_failure=`{v['dominant_failure']}`"
            )
            lines.append(
                f"  - Original AB2: topics=`{v['ab2_original_actual_topics']}` "
                f"actions=`{v['ab2_original_actual_actions']}`"
            )
            if v.get("sample_failing_debug"):
                debug_brief = {k: v["sample_failing_debug"].get(k) for k in ["selected_route", "qna_attempted", "ticket_action_called", "policy_triggered"]}
                lines.append(f"  - Sample failing debug: `{debug_brief}`")
            if v.get("sample_passing_debug"):
                debug_brief = {k: v["sample_passing_debug"].get(k) for k in ["selected_route", "qna_attempted", "ticket_action_called", "policy_triggered"]}
                lines.append(f"  - Sample passing debug: `{debug_brief}`")
            lines.append("")
        lines.append("")
    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checklist", required=True)
    parser.add_argument("--deep-dive", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--agent", default=DEFAULT_AGENT)
    parser.add_argument("--runs-per-row", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true", help="Build input only, no preview runs")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    deep = load_deep_dive(Path(args.deep_dive))
    rows = parse_open_router_rows(Path(args.checklist))
    joined, misses, duplicates = join_to_deep_dive(rows, deep)
    print(f"[audit] checklist open rows: {len(rows)}; matched to deep-dive: {len(joined)}; misses: {len(misses)}; duplicates: {len(duplicates)}")
    if misses:
        miss_path = output_dir / "router_audit_unmatched.txt"
        miss_path.write_text("\n".join(misses))
        print(f"[audit] unmatched rows written to {miss_path}")
    if duplicates:
        dup_path = output_dir / "router_audit_duplicate_matches.txt"
        dup_path.write_text("\n".join(duplicates))
        print(f"[audit] duplicate matches written to {dup_path}")

    input_csv = output_dir / "router_audit_input.csv"
    write_input_csv(joined, input_csv)
    print(f"[audit] input csv: {input_csv}")

    if args.dry_run:
        print("[audit] dry-run; exiting before preview turns")
        return

    jsonl_path = output_dir / "router_audit_runs.jsonl"
    existing = load_existing_attempts(jsonl_path)
    print(f"[audit] resuming with {len(existing)} prior attempts on file")

    total_trials = len(joined) * args.runs_per_row
    completed = len(existing)
    with jsonl_path.open("a") as out:
        for row_idx, row in enumerate(joined, start=1):
            for attempt in range(1, args.runs_per_row + 1):
                key = (row["row_id"], attempt)
                if key in existing:
                    continue
                trial_started = time.time()
                trial = run_trial(args.agent, row["utterance"])
                record = {
                    "row_id": row["row_id"],
                    "attempt": attempt,
                    "agent": args.agent,
                    **trial,
                }
                out.write(json.dumps(record) + "\n")
                out.flush()
                existing[key] = record
                completed += 1
                trial_elapsed = time.time() - trial_started
                status = "PASS" if trial.get("criterion_passed") else "FAIL"
                err = "(err)" if trial.get("error") else ""
                print(
                    f"[audit] [{completed}/{total_trials}] row={row['row_id']} #{row['checklist_number']} "
                    f"attempt={attempt}/{args.runs_per_row} {status}{err} "
                    f"elapsed={trial_elapsed:.1f}s"
                )

    verdicts = aggregate_verdicts(joined, existing, args.runs_per_row)
    for v in verdicts:
        v["_agent"] = args.agent
    verdicts_path = output_dir / "router_audit_verdicts.json"
    verdicts_path.write_text(json.dumps(verdicts, indent=2))
    print(f"[audit] verdicts json: {verdicts_path}")

    summary_md = output_dir / "router_audit_summary.md"
    write_summary_md(verdicts, summary_md, args.runs_per_row)
    print(f"[audit] summary md: {summary_md}")


if __name__ == "__main__":
    main()
