#!/usr/bin/env python3
"""Re-grade HelpIQ static eval results against an *allowed-route* set.

Why this exists
---------------
Testing Center's `AiEvaluationDefinition` `topic_assertion` / `actions_assertion`
are EXACT-match only. HelpIQ routing is intentionally nondeterministic for many
borderline intents (e.g. an IT problem may legitimately be answered in
GeneralQnA *or* escalated), so exact-match flags acceptable behaviour as
failures. This scorer re-grades the raw static results against a per-test
*allowed set* of routes/tools so the score reflects "did the agent land on an
acceptable route", not "did it match one frozen expectation".

It does NOT change Testing Center; it is an external scorer over the result
JSON that Testing Center produces.

Two modes
---------
1. derive : build an allowed-routes spec from a human-reviewed triage CSV
            (the "Review" column decisions). Run once after a review pass.
2. score  : grade static result JSONs against an allowed-routes spec and print
            the pass rate + the residual genuine-bug list.

Usage
-----
  # derive the allowed-routes spec from a reviewed triage csv
  python regrade_allowed_routes.py derive \
      --review "v6 evals update review - HelpIQ20_v6_routing_triage.csv" \
      --out allowed_routes_v6.csv

  # score result JSONs against the spec
  python regrade_allowed_routes.py score \
      --results /path/to/*.json --allowed allowed_routes_v6.csv
"""
from __future__ import annotations
import argparse, csv, glob, json, re
from collections import Counter

# Review-column phrases that mean "this is a genuine agent bug — keep it FAILING"
BUG_MARKERS = ("need to update routing", "must be sofware", "must be software")


def classify(review: str) -> str:
    r = (review or "").strip().lower()
    if r == "":
        return "BLANK"
    if any(m in r for m in BUG_MARKERS):
        return "BUG"
    return "ACCEPT"


def derive(review_csv: str, out_csv: str) -> None:
    rows = list(csv.DictReader(open(review_csv)))
    out = []
    for r in rows:
        decision = classify(r.get("Review"))
        expected = (r.get("expected_agent") or "").strip()
        actual = (r.get("actual_sub_agent") or "").strip()
        # ACCEPT -> the route the agent took is allowed (in addition to expected)
        # BUG    -> only the expected route is allowed (so the misroute still fails)
        # BLANK  -> undecided; keep strict (expected only) and flag for follow-up
        if decision == "ACCEPT":
            allowed = sorted({expected, actual} - {""})
        else:
            allowed = sorted({expected} - {""})
        out.append({
            "suite": r.get("suite", ""),
            "test_number": r.get("test_number", ""),
            "utterance": (r.get("utterance") or "").replace("\n", " ").strip(),
            "allowed_agents": "|".join(allowed),
            "decision": decision,
        })
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["suite", "test_number", "utterance", "allowed_agents", "decision"])
        w.writeheader()
        w.writerows(out)
    c = Counter(o["decision"] for o in out)
    print(f"derived {len(out)} rows -> {out_csv}  ({dict(c)})")


def _suite_from_path(path: str) -> str:
    m = re.search(r"(pt1|pt2|multi)", path)
    return m.group(1) if m else ""


def _load_results(patterns: list[str]) -> dict:
    """Return {(suite, test_number): actual_topic}. Test numbers repeat across
    suites, so the suite MUST be part of the key."""
    actual = {}
    for pat in patterns:
        for path in glob.glob(pat):
            suite = _suite_from_path(path)
            data = json.load(open(path))
            res = data.get("result", data)
            for c in res.get("testCases", []):
                top = ""
                for tr in c.get("testResults", []):
                    if tr.get("name") == "topic_assertion":
                        top = str(tr.get("actualValue"))
                actual[(suite, str(c.get("testNumber")))] = top
    return actual


def score(result_patterns: list[str], allowed_csv: str) -> None:
    allowed_rows = list(csv.DictReader(open(allowed_csv)))
    key = lambda r: (r["suite"], r["test_number"])
    allowed = {key(r): set(filter(None, r["allowed_agents"].split("|"))) for r in allowed_rows}
    decision = {key(r): r["decision"] for r in allowed_rows}
    utt = {key(r): r["utterance"] for r in allowed_rows}
    actual = _load_results(result_patterns)

    total = len(actual)
    in_spec = passed = failed = 0
    bugs = []
    for k, act in actual.items():
        if k not in allowed:
            # not in the reviewed/allowed spec -> was already passing
            continue
        in_spec += 1
        if act in allowed[k] or not allowed[k]:
            passed += 1
        else:
            failed += 1
            bugs.append((k, decision.get(k), act, utt.get(k, "")[:70]))

    not_in_spec = total - in_spec  # runs that weren't flagged in triage = already passing
    eff_pass = passed + not_in_spec
    print(f"total runs scored:        {total}")
    print(f"  already-passing (not in triage): {not_in_spec}")
    print(f"  reviewed runs:                   {in_spec}  (pass {passed} / fail {failed})")
    print(f"EFFECTIVE PASS: {eff_pass}/{total} = {100*eff_pass/total:.1f}%")
    print(f"\nresidual failures ({len(bugs)}):")
    for k, dec, act, u in sorted(bugs):
        print(f"  {k[0]}#{k[1]} [{dec}] actual={act} :: {u}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("derive"); d.add_argument("--review", required=True); d.add_argument("--out", required=True)
    s = sub.add_parser("score"); s.add_argument("--results", nargs="+", required=True); s.add_argument("--allowed", required=True)
    a = ap.parse_args()
    if a.cmd == "derive":
        derive(a.review, a.out)
    else:
        score(a.results, a.allowed)


if __name__ == "__main__":
    main()
