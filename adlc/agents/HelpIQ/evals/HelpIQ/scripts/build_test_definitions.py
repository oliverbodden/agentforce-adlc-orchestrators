#!/usr/bin/env python3
"""Build Salesforce AiEvaluationDefinition XML from HelpIQ master CSV files.

The CSV masters keep `original_expected_actions` for auditability, but the
generated Testing Center XML intentionally uses `expected_actions`. That column
contains the corrected runtime tool assertions after removing pseudo control
flow labels such as `stage_request`, `go_to_*`, and confirmation markers.
"""

from __future__ import annotations

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path


EVAL_ROOT = Path(__file__).resolve().parents[1]
NS = "http://soap.sforce.com/2006/04/metadata"
ET.register_namespace("", NS)


def add_text(parent: ET.Element, tag: str, text: str | int) -> ET.Element:
    child = ET.SubElement(parent, f"{{{NS}}}{tag}")
    child.text = str(text)
    return child


def add_expectation(test_case: ET.Element, name: str, value: str = "") -> None:
    expectation = ET.SubElement(test_case, f"{{{NS}}}expectation")
    if value:
        add_text(expectation, "expectedValue", value)
    add_text(expectation, "name", name)


def add_inputs(test_case: ET.Element, row: dict[str, str]) -> None:
    inputs = ET.SubElement(test_case, f"{{{NS}}}inputs")
    history_raw = row.get("conversation_history_json") or "[]"
    try:
        history = json.loads(history_raw)
    except json.JSONDecodeError:
        history = []
    for item in history:
        ch = ET.SubElement(inputs, f"{{{NS}}}conversationHistory")
        for field in ["role", "message", "topic", "index"]:
            value = item.get(field)
            if value not in (None, ""):
                add_text(ch, field, value)
    add_text(inputs, "utterance", row["utterance"])


def build_definition(
    rows: list[dict[str, str]],
    *,
    name: str,
    subject_name: str,
    subject_version: str,
) -> ET.ElementTree:
    root = ET.Element(f"{{{NS}}}AiEvaluationDefinition")
    add_text(root, "name", name)
    add_text(root, "subjectName", subject_name)
    add_text(root, "subjectType", "AGENT")
    add_text(root, "subjectVersion", subject_version)

    for index, row in enumerate(rows, 1):
        test_case = ET.SubElement(root, f"{{{NS}}}testCase")
        add_expectation(test_case, "topic_sequence_match", row.get("expected_topic", ""))
        add_expectation(test_case, "action_sequence_match", row.get("expected_actions", ""))
        add_expectation(test_case, "bot_response_rating", row.get("expected_answer", ""))
        for metric in (row.get("judge_metrics") or "").split("|"):
            metric = metric.strip()
            if metric:
                add_expectation(test_case, metric)
        add_inputs(test_case, row)
        add_text(test_case, "number", row.get("case_number") or index)

    return ET.ElementTree(root)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single-csv", type=Path, default=EVAL_ROOT / "single_turn_tests.csv")
    parser.add_argument("--multi-csv", type=Path, default=EVAL_ROOT / "multi_turn_tests.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--subject-name", default="HelpIQ_AgentScript_AB2")
    parser.add_argument("--subject-version", default="v1")
    parser.add_argument("--single-name", default="HelpIQ - single-turn master")
    parser.add_argument("--multi-name", default="HelpIQ - fixed multi-turn master")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        (
            args.output_dir / "HelpIQ_single_turn.aiEvaluationDefinition-meta.xml",
            build_definition(
                read_rows(args.single_csv),
                name=args.single_name,
                subject_name=args.subject_name,
                subject_version=args.subject_version,
            ),
        ),
        (
            args.output_dir / "HelpIQ_fixed_multi_turn.aiEvaluationDefinition-meta.xml",
            build_definition(
                read_rows(args.multi_csv),
                name=args.multi_name,
                subject_name=args.subject_name,
                subject_version=args.subject_version,
            ),
        ),
    ]
    for path, tree in outputs:
        tree.write(path, encoding="UTF-8", xml_declaration=True)
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
