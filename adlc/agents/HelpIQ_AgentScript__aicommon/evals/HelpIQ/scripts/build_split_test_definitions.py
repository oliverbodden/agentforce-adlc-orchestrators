#!/usr/bin/env python3
"""Build split AiEvaluationDefinition XML for HelpIQ static suites.

Single-turn master exceeds Salesforce's ~1000 case limit when deployed as one
definition. This emits pt1 + pt2 (deduped utterance groups) plus fixed multi-turn.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from build_test_definitions import build_definition, read_rows


EVAL_ROOT = Path(__file__).resolve().parents[1]


def split_single_rows(rows: list[dict[str, str]], pt1_unique_groups: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    order: list[tuple[str, str]] = []
    for row in rows:
        key = (row.get("utterance", ""), row.get("expected_topic", ""))
        if key not in groups:
            order.append(key)
        groups[key].append(row)

    pt1_keys = set(order[:pt1_unique_groups])
    pt1 = [row for key in pt1_keys for row in groups[key]]
    pt2 = [row for key in order[pt1_unique_groups:] for row in groups[key]]
    return pt1, pt2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single-csv", type=Path, default=EVAL_ROOT / "single_turn_tests.csv")
    parser.add_argument("--multi-csv", type=Path, default=EVAL_ROOT / "multi_turn_tests.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--subject-name", default="HelpIQ_AgentScript_AB2")
    parser.add_argument("--subject-version", default="v2")
    parser.add_argument("--pt1-unique-groups", type=int, default=313)
    parser.add_argument("--name-prefix", default="HelpIQ_AB2_v2_active")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    single_rows = read_rows(args.single_csv)
    pt1_rows, pt2_rows = split_single_rows(single_rows, args.pt1_unique_groups)
    multi_rows = read_rows(args.multi_csv)

    specs = [
        (
            f"{args.name_prefix}_single_pt1.aiEvaluationDefinition-meta.xml",
            pt1_rows,
            f"{args.name_prefix} single-turn pt1",
        ),
        (
            f"{args.name_prefix}_single_pt2.aiEvaluationDefinition-meta.xml",
            pt2_rows,
            f"{args.name_prefix} single-turn pt2",
        ),
        (
            f"{args.name_prefix}_multi.aiEvaluationDefinition-meta.xml",
            multi_rows,
            f"{args.name_prefix} fixed multi-turn",
        ),
    ]

    for filename, rows, label in specs:
        tree = build_definition(
            rows,
            name=label,
            subject_name=args.subject_name,
            subject_version=args.subject_version,
        )
        path = args.output_dir / filename
        tree.write(path, encoding="UTF-8", xml_declaration=True)
        print(f"{path} ({len(rows)} cases, subjectVersion={args.subject_version})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
