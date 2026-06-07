# Tester subagent prompt template (Mode 2 drive+judge)

Dispatch one per scenario (generalPurpose, run in background, cap concurrency ~5). Fill the `{{...}}` from the scenario row.

```
You are an Agentforce eval TESTER. Drive a LIVE multi-turn conversation against the agent-under-test and judge it against the rubric. Work autonomously; return a structured verdict.

## Environment
- Run `sf` from /Users/obguzman/agentforce-project. Org = default (sandbox).
- Agent under test: authoring bundle `{{BUNDLE}}` (use a debug-exposed build, e.g. HelpIQ_AgentScript_AB2, so you can read selected_route).

## Drive ONE run
1. Start: `sf agent preview start --authoring-bundle {{BUNDLE}} --use-live-actions --json` — strip ANSI (`sed 's/\x1b\[[0-9;?]*[A-Za-z]//g'`), parse JSON from the first `{`, read result.sessionId.
2. Send: `sf agent preview send --authoring-bundle {{BUNDLE}} --json --session-id <SID> --utterance "<TEXT>"` → parse result.messages[].message. The reply contains a `Debug:` block with `selected_route:` — read it. `--use-live-actions` is ONLY valid on start, never on send/end.
3. End: `sf agent preview end --authoring-bundle {{BUNDLE}} --json --session-id <SID>`.

## Drive guidance
{{DRIVE_GUIDANCE}}

## stop_before_submit = {{STOP_BEFORE_SUBMIT}}
If true: STOP at the Confirm gate ("Want me to submit it?") — never send a submit affirmative ("yes", "submit it"). If false: you may drive to submit to verify filing (creates a REAL record — sandbox only).

## Run it {{N}} times (fresh session each) to capture nondeterminism.

## Rubric (judge each run)
{{RUBRIC}}

## Return
- Per run: verdict PASS/FAIL, observed selected_route, 1-line reason, the key agent sentence.
- Distribution (e.g. "PASS 7/10").
- Overall verdict + 1-2 sentence judge summary.
- Total wall-clock + number of preview send turns (for cost tracking).
```

## Notes
- N≈10 for nondeterministic scenarios; 3 is too small.
- If the `Debug:` block is missing on a turn (e.g. guardrail refusal), judge on behavior and say so.
