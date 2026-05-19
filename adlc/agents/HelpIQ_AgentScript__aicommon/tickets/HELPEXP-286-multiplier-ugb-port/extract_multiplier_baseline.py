#!/usr/bin/env python3
"""
Extract multiplier-expected test cases from a HelpIQ 999-case test result JSON
and compute per-metric pass rates as the v7-proxy baseline for HELPEXP-286.

v7 multiplier reasoning.instructions is byte-identical to v4 per the registry
(2026-05-15 entry). v4 was the last 999-case run against the canonical multiplier
prompt, so v4 multiplier-filtered rows serve as the v7 baseline for AC #1.

Usage:
    python extract_multiplier_baseline.py <results.json> <out.csv> <out.md>
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

MULTIPLIER_TOPIC = "HelpIqAgentMultiplierSoftwareRequests"


def load(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def case_topic_expectation(case: dict) -> str | None:
    for tr in case.get("testResults", []):
        if tr.get("name") == "topic_assertion":
            return tr.get("expectedValue")
    return None


def case_topic_actual(case: dict) -> str | None:
    return (case.get("generatedData") or {}).get("topic")


def case_utterance(case: dict) -> str:
    return ((case.get("inputs") or {}).get("utterance") or "").strip()


def case_outcome(case: dict) -> str:
    return ((case.get("generatedData") or {}).get("outcome") or "").strip()


def per_metric_rates(cases: list[dict]) -> dict[str, dict[str, int]]:
    rates: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    for case in cases:
        for tr in case.get("testResults", []):
            name = tr.get("name")
            result = tr.get("result")
            if name and result:
                rates[name][result] += 1
                rates[name]["total"] += 1
    return rates


def welcome_only_count(cases: list[dict], min_words: int = 25) -> dict[str, int]:
    welcome_markers = (
        "i'm here to help",
        "i am here to help",
        "ask me for help",
        "hi! i'm here to help",
        "hi! i am here to help",
    )
    welcome_only = 0
    substantive = 0
    empty_or_short = 0
    for case in cases:
        outcome = case_outcome(case).lower()
        words = outcome.split()
        if not outcome:
            empty_or_short += 1
            continue
        is_welcome = any(m in outcome for m in welcome_markers) and len(words) < 40
        if is_welcome:
            welcome_only += 1
        elif len(words) >= min_words:
            substantive += 1
        else:
            empty_or_short += 1
    return {
        "welcome_only": welcome_only,
        "substantive": substantive,
        "empty_or_short": empty_or_short,
        "total": len(cases),
    }


def main() -> int:
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <results.json> <out.csv> <out.md>", file=sys.stderr)
        return 2

    results_path = Path(sys.argv[1])
    out_csv = Path(sys.argv[2])
    out_md = Path(sys.argv[3])

    data = load(results_path)
    all_cases = data.get("result", {}).get("testCases", [])
    multiplier_cases = [
        c for c in all_cases if case_topic_expectation(c) == MULTIPLIER_TOPIC
    ]

    rates = per_metric_rates(multiplier_cases)
    welcome = welcome_only_count(multiplier_cases)

    # CSV: per-case detail
    with out_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "case_number", "trial", "utterance", "expected_topic",
            "actual_topic", "outcome_first_120",
            "topic_assertion", "actions_assertion",
            "output_validation", "completeness", "coherence", "conciseness",
            "latency_ms",
        ])
        for case in multiplier_cases:
            metrics = {
                tr.get("name"): tr.get("result")
                for tr in case.get("testResults", [])
            }
            latency = ""
            for tr in case.get("testResults", []):
                if tr.get("name") == "output_latency_milliseconds":
                    latency = tr.get("actualValue", "")
            writer.writerow([
                case.get("testNumber"),
                case.get("trialNumber", ""),
                case_utterance(case),
                case_topic_expectation(case),
                case_topic_actual(case),
                case_outcome(case)[:120],
                metrics.get("topic_assertion", ""),
                metrics.get("actions_assertion", ""),
                metrics.get("output_validation", ""),
                metrics.get("completeness", ""),
                metrics.get("coherence", ""),
                metrics.get("conciseness", ""),
                latency,
            ])

    # MD: summary
    lines: list[str] = []
    lines.append("# v7-proxy multiplier baseline (extracted from v4 999-case run)")
    lines.append("")
    lines.append(f"**Source:** `{results_path.name}`")
    lines.append(
        f"**Multiplier-expected cases:** {len(multiplier_cases)} of "
        f"{len(all_cases)} ({len(multiplier_cases) * 100 // max(len(all_cases), 1)}%)"
    )
    lines.append("")
    lines.append("**Why this is the v7 baseline:** The multiplier sub-agent's")
    lines.append("`reasoning.instructions` is byte-identical between v4 and v7 per")
    lines.append("`AGENT_VERSION_REGISTRY.md` 2026-05-15 entry. The cross-version")
    lines.append("drop on v7 vs v4 is documented as welcome-only-fallback rate")
    lines.append("change (47% → 58%), not prompt-driven. For prompt-edit AC #1,")
    lines.append("v4 multiplier-row metrics are the canonical baseline; welcome-only")
    lines.append("rate is the separately-tracked guardrail.")
    lines.append("")
    lines.append("## Per-metric pass rates (multiplier-expected subset)")
    lines.append("")
    lines.append("| Metric | PASS | Other | Total | Pass rate | AC #1 floor (−5pp) |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for metric in [
        "topic_assertion",
        "actions_assertion",
        "output_validation",
        "completeness",
        "coherence",
        "conciseness",
    ]:
        r = rates.get(metric, {})
        passed = r.get("PASS", 0)
        total = r.get("total", 0) or 1
        other = total - passed
        pct = passed * 100 // total
        floor = max(pct - 5, 0)
        lines.append(
            f"| `{metric}` | {passed} | {other} | {total} | {pct}% | ≥ {floor}% |"
        )
    lines.append("")
    lines.append("## Welcome-only fallback baseline (guardrail metric)")
    lines.append("")
    lines.append(
        f"- welcome-only: **{welcome['welcome_only']} / {welcome['total']}** "
        f"({welcome['welcome_only'] * 100 // max(welcome['total'], 1)}%)"
    )
    lines.append(
        f"- substantive (≥25 words): {welcome['substantive']} / {welcome['total']}"
    )
    lines.append(
        f"- empty/short: {welcome['empty_or_short']} / {welcome['total']}"
    )
    lines.append("")
    lines.append("Welcome-only rate is the registry-documented separate failure mode")
    lines.append("(non-prompt). HELPEXP-286 acceptance must NOT cause this rate to")
    lines.append("worsen (≤ +3pp), but does NOT need to improve it.")
    lines.append("")
    lines.append("## Catalog app coverage in multiplier-expected subset")
    lines.append("")
    apps = Counter()
    catalog = [
        "Adobe", "Asana", "Confluence", "Figma", "Gitlab", "Glean", "Gong",
        "Grammarly", "Huddle", "Keeper", "Zoom", "Windsurf", "Waldo", "Slack",
        "Office 365", "Microsoft", "Passport", "Tableau", "Salesforce",
        "Ishbook", "Agiloft", "Indeed TV", "Cursor", "Claude", "N8N",
        "Lucid", "Seismic", "DataLake", "Mechabugs", "Logrepo", "Canva",
        "Cloudflare", "Flex", "Idash", "DocuSign", "Floqast", "GitHub",
        "Excel", "Box", "IBIS", "GD",
    ]
    for case in multiplier_cases:
        utterance_lower = case_utterance(case).lower()
        for app in catalog:
            if app.lower() in utterance_lower:
                apps[app] += 1
    lines.append("| App | Cases |")
    lines.append("|---|---:|")
    for app, count in apps.most_common():
        lines.append(f"| {app} | {count} |")

    with out_md.open("w") as f:
        f.write("\n".join(lines))

    print(
        f"Wrote {out_csv.name} ({len(multiplier_cases)} multiplier-expected rows) "
        f"and {out_md.name}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
