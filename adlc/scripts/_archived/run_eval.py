#!/usr/bin/env python3
"""Run a Testing Center eval and collect results.

Usage:
    python3 run_eval.py --org <alias> --spec <yaml> --suite-name <name> --output <csv>

Creates/updates the test suite, runs it, waits for results, and exports to CSV.
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import time


def run_sf(args_list, timeout=600):
    result = subprocess.run(
        ["sf"] + args_list,
        capture_output=True, text=True, timeout=timeout
    )
    # Strip CLI warnings
    lines = result.stdout.split("\n")
    clean = "\n".join(l for l in lines if not l.strip().startswith("\u203a"))
    return json.loads(clean) if clean.strip() else {}


def main():
    parser = argparse.ArgumentParser(description="Run Testing Center eval")
    parser.add_argument("--org", required=True)
    parser.add_argument("--spec", required=True, help="YAML test spec path")
    parser.add_argument("--suite-name", required=True, help="Test suite API name")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--wait", type=int, default=30, help="Max wait minutes")
    args = parser.parse_args()

    # Deploy test suite
    print(f"Deploying test suite: {args.suite_name}")
    run_sf(["agent", "test", "create",
            "--spec", args.spec,
            "--api-name", args.suite_name,
            "--force-overwrite",
            "-o", args.org, "--json"])

    # Run
    print(f"Running eval (wait up to {args.wait} min)...")
    result = run_sf(["agent", "test", "run",
                     "--api-name", args.suite_name,
                     "--wait", str(args.wait),
                     "--result-format", "json",
                     "-o", args.org, "--json"],
                    timeout=args.wait * 60 + 60)

    run_id = result.get("result", {}).get("runId")
    if not run_id:
        print("Error: no runId in result", file=sys.stderr)
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)
    print(f"Run ID: {run_id}")

    # Get results
    print("Fetching results...")
    res = run_sf(["agent", "test", "results",
                  "--job-id", run_id,
                  "--result-format", "json",
                  "-o", args.org, "--json"])

    tc_list = res.get("result", {}).get("testCases", [])
    print(f"Test cases: {len(tc_list)}")

    # Export to CSV
    rows = []
    for tc in tc_list:
        rows.append({
            "Utterance": tc["inputs"]["utterance"],
            "Actual Action": tc.get("generatedData", {}).get("actionsSequence", ""),
            "Actual Outcome": tc.get("generatedData", {}).get("outcome", ""),
            "Conversation History": "[]",
            "Output Latency Milliseconds": ""
        })

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Utterance", "Actual Action", "Actual Outcome",
            "Conversation History", "Output Latency Milliseconds"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV written: {len(rows)} rows → {args.output}")

    # Quick summary
    topic_pass = sum(1 for tc in tc_list
                     if any(r["name"] == "topic_assertion" and r["result"] == "PASS"
                            for r in tc.get("testResults", [])))
    outcome_pass = sum(1 for tc in tc_list
                       if any(r["name"] == "output_validation" and r["result"] == "PASS"
                              for r in tc.get("testResults", [])))
    print(f"Topic: {topic_pass}/{len(tc_list)} | Outcome: {outcome_pass}/{len(tc_list)}")


if __name__ == "__main__":
    main()
