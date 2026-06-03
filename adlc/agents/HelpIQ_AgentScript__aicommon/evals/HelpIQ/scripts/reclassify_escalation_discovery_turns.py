#!/usr/bin/env python3
"""Reclassify fixed multi-turn rows from immediate-escalate to discovery intake.

Use when AB2 (and target product behavior) gathers ticket fields on confirm/handoff
turns instead of invoking HelpIqAgentEscalateAction on that turn.

Updates multi_turn_tests.csv in place (with optional backup). Rebuild XML with
build_test_definitions.py after applying.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parents[1]
MULTI_CSV = EVAL_ROOT / "multi_turn_tests.csv"
OLD_POLICY = "escalate_after_context_or_confirmation"
NEW_POLICY = "discovery_intake_before_escalation"

DISCOVERY_EXPECTED_ANSWER = (
    "(Discovery intake — agent asks for missing details needed to open a ticket "
    "(for example email, issue summary, error text, device/context). Must not invoke "
    "HelpIqAgentEscalateAction on this turn and must not state that a ticket is "
    "already created or submitted unless the escalate tool actually ran.)"
)

DISCOVERY_POLICY_NOTES = (
    "User confirmed handoff or asked to create a ticket, but required intake fields "
    "are not yet collected. Discovery/clarify is valid; escalate tool must not run "
    "until intake is complete and a later turn explicitly submits."
)


def load_regression_test_ids(report_path: Path) -> set[str]:
    sys.path.insert(0, str(EVAL_ROOT / "scripts"))
    import build_report as br  # noqa: WPS433

    with report_path.open() as f:
        data = json.load(f)
    base = next(a for a in data["agents"] if a["agent"] == "HelpIQ20")
    ab2 = next(a for a in data["agents"] if a["agent"] == "HelpIQ_AgentScript_AB2")

    def ms(row: dict) -> dict:
        tc = row["case"]
        return {m: br.metric_pass(tc, m) for m in br.BENCHMARK_METRICS}

    def benchmark_pass(status: dict) -> bool:
        vals = [v for v in status.values() if v is not None]
        return all(vals) if vals else False

    base_map = {r["test_id"]: r for r in base["static_rows"] if r["suite"] == "fixed_multi_turn"}
    ab2_map = {r["test_id"]: r for r in ab2["static_rows"] if r["suite"] == "fixed_multi_turn"}

    ids: set[str] = set()
    for tid, brow in base_map.items():
        if brow.get("tool_policy") != OLD_POLICY:
            continue
        if tid not in ab2_map:
            continue
        if benchmark_pass(ms(brow)) and not benchmark_pass(ms(ab2_map[tid])):
            ids.add(tid)
    return ids


def should_update_row(row: dict[str, str], mode: str, regression_ids: set[str]) -> bool:
    if row.get("tool_policy") != OLD_POLICY:
        return False
    if mode == "ab2-regression":
        return row["test_id"] in regression_ids
    if mode == "all-escalate-after":
        return True
    return False


def apply_discovery_row(row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    prior = (row.get("expected_actions") or "").strip()
    if prior and not (row.get("original_expected_actions") or "").strip():
        out["original_expected_actions"] = prior

    out["expected_actions"] = "[]"
    out["allowed_tools"] = "HelpIQ_QnA"
    forbidden = [t for t in (row.get("forbidden_tools") or "").split("|") if t]
    for tool in ("HelpIqAgentEscalateAction",):
        if tool not in forbidden:
            forbidden.append(tool)
    out["forbidden_tools"] = "|".join(forbidden)
    out["requires_confirmation_before_tool"] = "true"
    out["tool_policy"] = NEW_POLICY
    out["tool_policy_notes"] = DISCOVERY_POLICY_NOTES
    out["expected_answer"] = DISCOVERY_EXPECTED_ANSWER
    if not (row.get("allowed_topics") or "").strip():
        out["allowed_topics"] = "Escalation|GeneralQnA_HelpIQ"
    note = (row.get("notes") or "").strip()
    stamp = "Reclassified to discovery_intake_before_escalation for AB2 intake (2026-06)."
    out["notes"] = f"{note} {stamp}".strip() if note else stamp
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("ab2-regression", "all-escalate-after"),
        default="ab2-regression",
        help="ab2-regression: only HelpIQ20-pass / AB2-fail rows from report; "
        "all-escalate-after: every escalate_after_context_or_confirmation row.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=EVAL_ROOT.parent.parent
        / "eval-runs/2026-06-01-clarify-overask/report/helpiq_evaluation_report.json",
        help="Report used for ab2-regression mode.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing CSV.")
    parser.add_argument("--backup", action="store_true", help="Write timestamped backup before update.")
    args = parser.parse_args()

    regression_ids: set[str] = set()
    if args.mode == "ab2-regression":
        if not args.report_json.exists():
            print(f"Report not found: {args.report_json}", file=sys.stderr)
            return 1
        regression_ids = load_regression_test_ids(args.report_json)
        print(f"Regression targets from report: {len(regression_ids)}")

    with MULTI_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = rows[0].keys() if rows else []

    updated: list[str] = []
    for row in rows:
        if should_update_row(row, args.mode, regression_ids):
            updated.append(row["test_id"])

    print(f"Mode: {args.mode}")
    print(f"Rows to update: {len(updated)}")
    if updated[:8]:
        print("Sample:", ", ".join(updated[:8]), ("..." if len(updated) > 8 else ""))

    if args.dry_run:
        return 0

    if not updated:
        print("Nothing to update.")
        return 0

    if args.backup:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = MULTI_CSV.with_suffix(f".csv.bak-{ts}")
        shutil.copy2(MULTI_CSV, backup)
        print(f"Backup: {backup}")

    id_set = set(updated)
    new_rows = [apply_discovery_row(row) if row["test_id"] in id_set else row for row in rows]
    with MULTI_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)

    manifest = EVAL_ROOT / "discovery_intake_reclassified_test_ids.json"
    manifest.write_text(json.dumps(sorted(updated), indent=2) + "\n")
    print(f"Updated {MULTI_CSV}")
    print(f"Manifest: {manifest}")
    print("Next: rebuild AiEvaluationDefinition XML with build_test_definitions.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
