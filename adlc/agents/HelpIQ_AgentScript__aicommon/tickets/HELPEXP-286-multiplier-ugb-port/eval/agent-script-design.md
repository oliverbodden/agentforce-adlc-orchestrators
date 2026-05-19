# Stage 0 — Agent Script structural design

**Ticket:** HELPEXP-286. **Iteration:** 1 of 10.
**Decision frame:** which behaviors enforced by Agent Script primitives, which by prompt narrative.
**HITL gate:** APPROVED 2026-05-16T19:50Z by `obguzman`. Option B selected; AC #2 100% with deferred-relax provision.

## The two Agent Script primitives in play

From `actions-reference.md`:

- **`require_user_confirmation: True`** on an action definition → Salesforce-native confirm UI fires before execution. Platform-enforced (model cannot bypass).
- **`available_when @variables.<expr>`** on an action definition → action is invisible to the LLM unless the expression evaluates true. Combined with a `mutable bool` variable set by the model in a preceding turn, this is a structural gate.

Both are real and load-bearing. Neither was in use on the multiplier topic in v7 — `HelpIqAgentMultiplierSoftwareRequests` action has `require_user_confirmation: False` and no `available_when`.

## Per-slot recommendation

**Per HITL 2026-05-16T19:50Z:** Confirm is a conversation turn (model asks slot summary + yes/no, user replies "yes"), not a Salesforce-native UI primitive. Option B selected for Confirm. AC #2 stays at 100% with deferred-relax provision if Stage 1 iteration cannot reliably reach it.

| Slot / behavior | AC | Recommended primitive | Why |
|---|---|---|---|
| **Confirm-before-Submit** on `HelpIqAgentMultiplierSoftwareRequests` | AC #2 (100% blocking, relax on iteration block) | **Prompt slot template** (Service Strategy: Confirm) | Conversation-turn UX per HITL. Model authors slot summary + "yes/no?" question; user replies "yes"; model proceeds to Submit. Surface-independent (Slack and preview render the same). Compliance risk addressed by Stage 1 iteration; if 100% proves unreachable, relax to ≥95% per HITL deferred-relax provision. |
| **Answer-vs-Submit classification** | AC #3 (≥80%) | Prompt only (UGB UNDERSTAND step) | No structural primitive can classify intent. Model decision, guided by a 2-bucket question: "Does the user want information about this app, or do they want me to file a request?" |
| **5-bucket Service Strategy taxonomy** | AC #4 enabler | Prompt only (named slots: Clarify / Answer / Confirm / Submit / Escalate) | Same shape as HELPEXP-274 GeneralQnA. Prompt slot templates beat countable rules per prior HITL. |
| **GATHER-informed Clarify** | AC #6 (≥70% non-blocking) | Prompt only | Model shapes Clarify from retrieval text. No structural way to inject "use these specific options." |
| **Qualifier disambiguation** (Zoom Phone, Claude Code, etc.) | AC #4 category | Prompt only (UGB UNDERSTAND step) | Detection is text-pattern recognition. Model decision. |
| **GATHER tool-call correctness** (right `applicationKey`) | AC #5 (≥90%) | Prompt + action input description | The action's `inputChatMessage` description already says "send only application or software name." Add UGB GATHER discipline in the prompt. Structural overengineering not warranted for a ≥90% threshold. |
| **`HelpIqAgentApplicationAccessDetails` gating** | none directly | No gate | Cheap read-only Glean call; safe to fire on any UNDERSTAND-classified Submit-intent or multi-license question. Don't gate. |
| **Catalog block in topic `description:`** | AC #8 preservation | **Preserve verbatim** | Structural — router classifier reads this. Changing it shifts what utterances route to multiplier. Out of scope to touch. |

## What changes in the `.agent` file

**Structural changes:** zero. No `require_user_confirmation` flip, no `available_when`, no new variables.

**Action wiring changes (`reasoning.actions:`):** zero.

**Topic `description:`:** unchanged (preserves router routing).

**Everything else is prompt** — the `reasoning.instructions:` body. That IS Stage 1.

## Why pure prompt, on the record

Per HITL, Confirm = conversation turn. Three structural alternatives considered and rejected:

- **A1 `require_user_confirmation: True`** — rejected. Salesforce-native UI may not render in Slack (production surface), risking silent degradation to no-gate-at-all in production.
- **A2 `available_when @variables.confirmation_accepted == True` + new bool variable** — rejected. The variable still has to be set by the model on user "yes", so the compliance risk is the same as pure prompt with extra Agent Script surface area.
- **C variable + conditional in `reasoning.instructions:`** — on inspection NOT a structural primitive; it's a fancier prompt rule. Same compliance floor as plain prompt.

The Stage 1 prompt is the entire change. No new variables, no new actions, no new transitions, no `.agent` structural edits.

## Risks of pure prompt

1. **AC #2 100% is not platform-guaranteed.** Stage 1 iteration must demonstrate it empirically on the 12 multi-turn scenarios. Per HITL deferred-relax provision: if iteration cannot reach 100% after iter 7, relax to ≥95% with explicit acknowledgment.
2. **Diagnostic visibility.** The Debug record (carried over from HELPEXP-274 GeneralQnA) is the only signal the model self-reports what Service Strategy it picked and whether it called Submit. Per prior HITL, Debug is evidence not ground truth — rubric grading verifies against actual tool calls in trace, not the Debug self-report.
3. **Heaviest Stage 1 lift is Answer-vs-Submit (AC #3).** Removing the legacy Step 2 PRIORITY mandatory-acknowledgment line ("I can definitely help you request access to [Application] right here!") that commits every utterance to action framing — that's the load-bearing UGB UNDERSTAND-step work, harder than the Confirm slot template.

## What Stage 1 starts with

1. Restructure `reasoning.instructions:` to the UGB shape with 5-bucket Service Strategy + Confirm slot template + Debug record (carry over the HELPEXP-274 debug-record format).
2. Preserve verbatim: catalog block in `description:`, `accessTypeKey`/`applicationKey`/`reasonForAccess` slot names, "General" silencer rule for unspecified access types, no-internal-leaking rule.
3. Validate (`sf agent validate authoring-bundle`), preview via `--authoring-bundle --simulate-actions`, run unit tests.

## Artifacts touched in Stage 0

- Created: this file.
- Read-only: `originals/HelpIqAgentMultiplierSoftwareRequests-v7-subagent-block.txt`, `discovery-context.md`, `multiplier-ticket-draft.md`, `agent-script-core-language.md`, `actions-reference.md`.
- Nothing in the `.agent` file changed.
