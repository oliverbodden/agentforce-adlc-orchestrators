#!/usr/bin/env python3
"""Append router-audit verdict columns to the negative_delta deep-dive CSV.

Each audit run is identified by an `--audit-date` argument so multiple audits
can coexist as separate column sets (e.g., `AB2 Audit 2026-05-26 Verdict`,
`AB2 Audit 2026-06-15 Verdict`, ...).

Re-running with the same `--audit-date` overwrites that audit's columns
(idempotent).
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


COLUMN_TEMPLATES = [
    ("AB2 Audit {date} Verdict", "verdict"),
    ("AB2 Audit {date} Trials Passed", "trials_passed"),
    ("AB2 Audit {date} Trials Run", "trials_run"),
    ("AB2 Audit {date} Trial Errors", "trial_errors"),
    ("AB2 Audit {date} Dominant Failure", "dominant_failure"),
    ("AB2 Audit {date} Sample Failing Route", "sample_failing_route"),
    ("AB2 Audit {date} Sample Failing QnA Attempted", "sample_failing_qna"),
    ("AB2 Audit {date} Sample Failing Ticket Called", "sample_failing_ticket"),
]


def normalize(text: str) -> str:
    import re
    if text is None:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deep-dive", required=True)
    parser.add_argument("--verdicts", required=True, help="path to router_audit_verdicts.json")
    parser.add_argument("--audit-date", required=True, help="e.g. 2026-05-26")
    parser.add_argument("--output", help="defaults to overwriting --deep-dive in place")
    args = parser.parse_args()

    deep_path = Path(args.deep_dive)
    verdicts = json.loads(Path(args.verdicts).read_text())
    verdicts_by_utterance = {normalize(v.get("utterance", "")): v for v in verdicts}

    columns = [(name.format(date=args.audit_date), key) for name, key in COLUMN_TEMPLATES]

    with deep_path.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    for name, _ in columns:
        if name not in fieldnames:
            fieldnames.append(name)

    matched = 0
    for row in rows:
        v = verdicts_by_utterance.get(normalize(row.get("Utterance", "")))
        if not v:
            for name, _ in columns:
                row.setdefault(name, "")
            continue
        matched += 1
        sample = v.get("sample_failing_debug") or {}
        for name, key in columns:
            if key == "sample_failing_route":
                row[name] = sample.get("selected_route", "") or ""
            elif key == "sample_failing_qna":
                row[name] = sample.get("qna_attempted", "") or ""
            elif key == "sample_failing_ticket":
                row[name] = sample.get("ticket_action_called", "") or ""
            else:
                row[name] = v.get(key, "")

    out_path = Path(args.output) if args.output else deep_path
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[write_back] deep-dive rows: {len(rows)}; matched to audit verdicts: {matched}")
    print(f"[write_back] wrote: {out_path}")


if __name__ == "__main__":
    main()
