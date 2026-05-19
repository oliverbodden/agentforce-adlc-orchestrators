# Attempt 02b-full-discipline — diagnostic-augmented per playbook

**Status:** approved per HITL 2026-05-16T19:50Z and follow-up "follow ur recommendation, just make sure you read the playbook and implement debugging logs".

## What's in the prompt beyond the 02b draft I originally presented

Per `adlc/playbooks/prompt-engineering-playbook.md` § Diagnostics → "Diagnostic Logs For Repeated Prompt Failures" + "Agentforce Diagnostic Trace Pattern":

### Hypothesis-driven Debug fields (was: generic 5 fields, now: 8 fields tied to specific ACs)

| New / changed field | Hypothesis it tests | Tied to |
|---|---|---|
| **Confirm chain** (new) | "Model self-reports Submit but the chain is actually broken (no prior Confirm, or user didn't actually accept)" | AC #2 |
| **Slots** (new) | "Model invents applicationKey or drifts slot values between Confirm and Submit" | AC #5, AC #7 |
| **Retrieval** (was: "Tools called", now split) | "Model is calling the wrong retrieval, or not reusing prior retrieval correctly on CONTINUATION" | AC #5, AC #6 |
| **App + qualifier** (new vs GeneralQnA) | "Model misses or fabricates qualifier disambiguation" | AC #4 category, AC #5 |
| **Intent** (new vs GeneralQnA) | "Model classifies INFO as ACTION and queues Submit when it should Answer" | AC #3 |

### Transparency reinforcement at multiple prompt layers (was: only at end, now: 6 layers)

Playbook says a single Debug section is not enough — Agentforce's trusted output layer can strip it. Reinforced at:

1. **Top-level diagnostic/transparency requirement** (first line of prompt: "DIAGNOSTIC MODE...")
2. **Per-strategy reminders** inline in each Service Strategy section ("[Required: end this reply with the Debug block.]")
3. **Submit-specific reinforcement** ("...include the slot snapshot AND the Confirm-chain audit in the Debug 'Slots' and 'Confirm chain' fields.")
4. **Confirm-specific reinforcement** ("...include the slot snapshot in the Debug 'Slots' field.")
5. **Debug template section** (the actual structure)
6. **Final "no exceptions" reminder** in the Rules block (rule 8: "Debug block is required scaffolding and will be removed before production acceptance. Until then, no exceptions.")

### Diagnostic-mode framing

The prompt opens with "DIAGNOSTIC MODE — this prompt requires per-turn transparency... will be removed or internalized before production acceptance." Per playbook: "Temporary diagnostic logs are not automatically an acceptance failure during development. They become a production blocker only when the run is ready for final user-facing acceptance and product has not approved exposed transparency output."

## Iteration removal plan

- **Iter 8-9 (after Service Strategy classifications are stable):** Strip per-strategy reminders; keep Debug record + top-of-prompt diagnostic-mode line.
- **Final iter (before acceptance):** Strip Debug record entirely OR convert to internal scratchpad (the latter requires checking whether Agentforce supports an internal-only annotation; if not, strip).
- **Acceptance check (Phase 6):** Per skill — `removal_verified=true` in `discovery.json` before production handoff.

## What we expect to learn from the Debug log specifically

| Failure mode I expect to see | Debug field that catches it |
|---|---|
| Submit fired with chain BROKEN | Confirm chain = BROKEN but Strategy = Submit (rule 6 contradiction; immediate iteration trigger) |
| Slot drift Confirm → Submit | Slots in Submit turn differ from Slots in immediately-prior Confirm turn |
| Wrong applicationKey on retrieval | Retrieval.inputChatMessage doesn't match the app named in App+qualifier |
| Multi-option Clarify defaulted to General | Retrieval returned N>=2 access types but accessTypeKey = "General" in next Confirm |
| INFO misclassified as ACTION | Intent = ACTION on a "is X auto-provisioned?"-style utterance |
| GATHER skipped when it shouldn't | Retrieval = "skipped" on a CONTINUATION turn that doesn't have a reusable prior retrieval |

If iteration 2 unit/smoke tests trip these consistently, that's the failure layer signal to act on — not "edit the prompt blindly".

## What this attempt does NOT change

- No .agent structural changes (no `require_user_confirmation`, no `available_when`, no new variables) — confirmed per Stage 0 HITL.
- No edits to other subagents.
- No edits to `agent_router`.
- No edits to global `system.instructions`.
- Catalog block in topic `description:` preserved verbatim.
- Action input/output descriptions preserved verbatim.

## Final prompt stats

- Lines: ~130 (was 35 in v7 original; ~270% growth).
- This is within the HELPEXP-274 GeneralQnA UGB prompt range (~80 lines) plus 5-bucket overhead and diagnostic scaffolding. Not flagged as size HITL trigger; will revisit at iter 8-9 strip-pass.
