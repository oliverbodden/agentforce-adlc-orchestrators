---
name: helpiq-agent-evals
description: >-
  Run dynamic behavioral evals for the HelpIQ Agentforce agents — the cheap
  deterministic runner (scripted sf preview + graders) and the subagent
  drive+judge methodology (live multi-turn testing + LLM-as-judge against
  per-scenario rubrics). Use when testing HelpIQ agent behavior, routing,
  confirmation gating, guardrails, or software-access/catalog scenarios; when
  running or scoring dynamic_tests.csv; or when the user asks to eval/regress a
  HelpIQ agent build (HelpIQ20, HelpIQ_AgentScript_AB1/AB2).
---

# HelpIQ Agent Evals

Project-specific dynamic eval methodology for the HelpIQ Agentforce agents. Two modes — pick per scenario, not per suite.

- **Mode 1 — deterministic runner**: cheap, reproducible, scriptable. Best for bulk regression and stable invariants.
- **Mode 2 — subagent drive+judge**: a tester subagent drives a live multi-turn conversation and judges it against a rubric. Best for nondeterministic / behavior-rich scenarios where exact-match graders misjudge (routing *variance*, conditional gates like `requiresReasonForAccess`, description-driven corrections, post-QnA anti-repeat, guardrail false-positives). Higher fidelity, but expensive and non-deterministic — use for the *hard* scenarios only.

## Files (all under `adlc/agents/HelpIQ_AgentScript__aicommon/evals/HelpIQ/`)
- `dynamic_tests.csv` — scenario source of truth (both modes read it).
- `scripts/run_dynamic_tests.py` — Mode 1 runner. `--live-actions` switches preview to real Apex/Flows (default is simulated).
- `scripts/regrade_allowed_routes.py` — re-grade results against an allowed-route set (Testing Center `topic_assertion` is exact-match; HelpIQ routing is intentionally nondeterministic). See `EVAL_REGRADE_README.md`.
- `EVAL_REGRADE_README.md` — allowed-route re-grade workflow + limitations.

## Scenario columns (`dynamic_tests.csv`)
Mode-1 columns: `initial_utterance`, `strategy` (→ hardcoded follow-ups in the runner), `tool_policy`/`topic_policy` (→ grader branches), `allowed_topics`, `runs`.
Mode-2 (drive+judge) columns:
- `rubric` — explicit PASS/FAIL criteria; the judge's contract.
- `drive_guidance` — how to drive adaptively (opening utterance + realistic follow-ups; do **not** volunteer details the agent should ask for).
- `action_mode` — `live` | `simulate`. Use **live** for catalog/data-dependent behavior (`requiresReasonForAccess`, access-type descriptions, software-access lookups). `simulate` mocks those and is meaningless for them.
- `stop_before_submit` — `true` (default) = stop at the Confirm gate and judge gate behavior without filing; `false` = drive to submit to verify actual filing.

## Mode 1 — deterministic runner
```bash
cd adlc/agents/HelpIQ_AgentScript__aicommon/evals/HelpIQ
# simulated (cheap, mocks actions):
python3 scripts/run_dynamic_tests.py --agent <BUNDLE> --scenarios dynamic_tests.csv --output-dir <dir>
# live (real Apex; required for catalog/requiresReason/description scenarios):
python3 scripts/run_dynamic_tests.py --agent <BUNDLE> --scenarios dynamic_tests.csv --output-dir <dir> --live-actions
```
Parallelize big runs by splitting the CSV into chunks and running concurrently (cap ~5). Re-grade routing failures with `regrade_allowed_routes.py`.

## Mode 2 — subagent drive+judge
Dispatch **one tester subagent per scenario** (parallel, cap concurrency ~5). Each subagent:
1. Runs the scenario **N≈10 times** (N=3 is too small — it once hid a known ~60% route as a misleading 3/3).
2. Drives a live conversation per `drive_guidance`; never volunteers details the agent must ask for.
3. Judges each run against `rubric`; returns per-run verdict + observed `selected_route` + distribution + overall + judge summary.

Give the tester a **debug-exposed** agent build so it can read `selected_route` from the `Debug:` block (e.g. `HelpIQ_AgentScript_AB2`). The committed source-of-truth builds (HelpIQ20) use internal-only debug — judge on behavior there.

Live-drive commands (the tester runs these):
```bash
# --use-live-actions is valid ONLY on start, never on send/end:
sf agent preview start --authoring-bundle <BUNDLE> --use-live-actions --json   # strip ANSI, parse from first '{', read result.sessionId
sf agent preview send  --authoring-bundle <BUNDLE> --json --session-id <SID> --utterance "<TEXT>"   # read result.messages[].message + Debug: selected_route
sf agent preview end   --authoring-bundle <BUNDLE> --json --session-id <SID>
```

Tester subagent prompt template — see [tester-prompt.md](tester-prompt.md).

## Safety / gotchas
- **LIVE actions create REAL records. Run only against a sandbox org.** Real records in sandbox are acceptable. Even with `stop_before_submit=true`, the agent can bypass its own gate and auto-file (observed: a turn-2 utterance auto-created a ticket) — expect occasional stray records.
- `--use-live-actions` is valid ONLY on `sf agent preview start`.
- Strip ANSI control chars from preview JSON; parse from the first `{`.
- The `Debug:` block is absent on some turns (e.g. guardrail refusals) — judge on behavior then.
- The judge is reliable (a 5-scenario prototype matched every known result and self-diagnosed flakiness); the tuning knobs are **N (run count)** and **which scenarios warrant Mode 2** vs. cheaper Mode 1.

## Choosing a mode
- Stable invariant, deterministic, bulk → **Mode 1**.
- Nondeterministic routing, conditional gates, descriptions, guardrail false-positives, "did it behave acceptably across multiple acceptable paths" → **Mode 2** (set `rubric`, `action_mode=live` where data-dependent).
