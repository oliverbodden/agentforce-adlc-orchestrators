# HelpIQ static eval re-grading (allowed routes)

## Why this exists
Testing Center's `AiEvaluationDefinition` assertions (`topic_assertion`,
`actions_assertion`) are **exact-match only**. HelpIQ routing is intentionally
**nondeterministic** for many borderline intents — e.g. an IT problem can
legitimately be answered in `GeneralQnA_HelpIQ` *or* handed off to `Escalation`,
and both are gated/correct. Exact-match therefore flags acceptable behaviour as
failures (the raw v6 static run scored ~36–54% almost entirely from this).

This package re-grades the raw Testing Center result JSON against a per-test
**allowed set of routes**, so the score reflects *"did the agent land on an
acceptable route"* rather than *"did it match one frozen expectation"*.

> Note: this is an **external scorer** over the result JSON. It does **not**
> change Testing Center — the platform's native score will keep showing
> exact-match. The authoritative "allowed-route" score lives here until/unless
> Salesforce adds multi-value assertion support.

## Files
| File | Purpose |
|---|---|
| `scripts/build_split_test_definitions.py` | Build the split static `AiEvaluationDefinition` XML (pt1/pt2 + multi) around Salesforce's ~1000-case limit. |
| `scripts/run_dynamic_tests.py` | Dynamic multi-turn runner (`--simulate-actions`). Supports `allowed_topics` natively in `dynamic_tests.csv`. |
| `dynamic_tests.csv` | Dynamic multi-turn scenarios (source of truth). |
| `scripts/regrade_allowed_routes.py` | Re-grade static results against an allowed-routes spec. Modes: `derive` (from a reviewed triage CSV) and `score`. |
| `v6_evals_review_decisions.csv` | Human-reviewed triage of every v6 routing mismatch (the `Review` column holds the decision). Provenance for the allowed-routes spec. |
| `allowed_routes_v6.csv` | Derived allowed-routes spec (per test: `allowed_agents`, `decision`). Generated from the review file. |

## Workflow
1. **Build + run static suites** (Testing Center): `build_split_test_definitions.py`, deploy, run, download result JSON.
2. **Review mismatches**: export failures, decide per row whether the observed route is acceptable (`Review` column). Genuine agent bugs use a phrase containing "need to update routing" / "must be software".
3. **Derive the allowed-routes spec**:
   ```
   python scripts/regrade_allowed_routes.py derive \
     --review v6_evals_review_decisions.csv --out allowed_routes_v6.csv
   ```
4. **Score**:
   ```
   python scripts/regrade_allowed_routes.py score \
     --results /path/to/HelpIQ20_v6_*_results.json --allowed allowed_routes_v6.csv
   ```

## Current v6 result
- **1559 / 1578 = 98.8% acceptable** (vs ~36–54% raw exact-match).
- **19 residual**: 10 genuine bugs (software-access requests misrouted to
  `GeneralQnA` instead of the software subagent — idash, floqast, CorpGov JIRA,
  Huddle, Concur) + 9 undecided (`BLANK`) rows awaiting a second-pass decision.

## Known limitations / scaling notes
- **Keying is `(suite, test_number)`** — test numbers repeat across suites, so
  both are required. Keep the result filename containing `pt1`/`pt2`/`multi`.
- The allowed-routes spec must be regenerated when the suite/test set changes.
- Two behaviour bugs are **not** visible to route-only re-grading and are tracked
  separately: the Keeper guardrail false-positive (hard refusal of a legit
  question) and the "how do I submit a ticket" QnA-drift (drifts into portal
  how-to/troubleshooting instead of creating the ticket on the QnA path).
