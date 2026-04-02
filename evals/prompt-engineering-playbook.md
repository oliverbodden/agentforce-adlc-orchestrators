# Prompt Engineering Playbook

Living document. Updated as we learn from each ticket. The agent consults this during Phase 5 (Execute) of `adlc-drive`. Humans consult it when reviewing or writing instructions manually.

---

## How to Use This Playbook

- **During drive Phase 5:** Before editing an instruction, review the relevant principles below.
- **Tie-breakers:** When a ticket's requirements conflict with a playbook principle, see the Rule Levels section.
- **Evolving:** After each ticket, drive should propose updates to this playbook in Phase 6 if new patterns were discovered. The user approves before changes are made.

---

## Rule Levels

Each principle is labeled:

| Level | Meaning | Ticket can override? |
|---|---|---|
| **HARD** | Violating this will break the agent or cause unrecoverable issues | No — adjust the ticket approach instead |
| **STRONG** | Violating this usually causes problems, but exceptions exist | Yes, with documented justification in the ticket's goal.md |
| **SOFT** | Best practice. Context-dependent. | Yes, freely |

When a conflict arises between a ticket requirement and a playbook principle:
1. Identify the rule level
2. If HARD — tell the user the approach needs to change, explain why
3. If STRONG — present the tradeoff, let the user decide, document the decision
4. If SOFT — proceed with the ticket's approach, note the deviation

---

## Instruction Structure

**[STRONG] Follow Understand → Gather → Build as the universal instruction pattern.**
This three-phase flow works across topic types. The AI should adapt it to each topic's needs. If a topic doesn't fit this pattern naturally, HITL — discuss with the user and iterate.

**[HARD] Reasoning scaffolding is load-bearing.**
Store: directives, step checkpoints, and consistency checks force the LLM to reason step-by-step. Removing them causes the LLM to shortcut to default/fallback behaviors. Never remove reasoning scaffolding without testing.

**[STRONG] Early sections have outsized impact.**
The LLM reads top-down and forms its mental model from the first sections it encounters (e.g., Philosophy, Core Principles). Directives placed early in the instruction have more influence on behavior than those placed later. When adding critical rules, put them near the top.

**[SOFT] One responsibility per topic.**
If an instruction covers multiple distinct tasks, consider splitting into multiple topics. But some topics naturally handle related sub-tasks — use judgment.

**[STRONG] Avoid duplicating instructions across topics.**
When the same guideline applies to multiple topics (e.g., tone, terminology), create plan options: global instructions vs per-topic vs merge. Eval success determines the winner, not prompt structure — if "perfect" architecture produces bad evals, the architecture is wrong. HITL for final decision when approaches produce similar eval results.

---

## Editing Instructions

**[HARD] Always backup before editing.**
No version history exists in the Tooling API. Every edit must be preceded by saving the current instruction.

**[STRONG] One change per iteration.**
Whether adding, removing, or modifying — make one targeted change, test, evaluate, then iterate. Batching changes makes it impossible to diagnose which change caused a regression.

**Exception — Consolidation tickets:** When merging multiple previously-validated changes into one prompt, each change was tested individually but never together. Treat as a single large change — run full eval after the merge, don't assume individual validations compose safely.

**[STRONG] Instruction size changes should be incremental.**
When modifying existing instructions:
- Target incremental reductions (e.g., 10-15% per iteration, not 40% at once)
- Test after each increment
- The safe floor is discovered empirically, not predicted

When adding new guidance:
- Come up with 2-3 options of varying verbosity
- Test each option
- Always HITL — present the options with results and let the user choose

**[STRONG] When you lack context to write specific logic, propose options — don't ask open-ended questions.**
Show what data/fields are available from your discovery, suggest 2-3 approaches with tradeoffs, let the user pick. The agent has context from Phase 3 — use it.

**[HARD] Exit ramps.**
If the fix is outside instruction scope (platform config, Apex, Data Cloud), stop and say so — don't attempt a workaround silently. If the fix IS possible via instruction but is a band-aid for a deeper issue, flag it explicitly: "I can do this, but it's a workaround. The real fix is X. Want me to proceed or address the root cause?" Never silently implement a workaround.

**[SOFT] Avoid instruction expansion without evidence.**
Adding more text doesn't always help. The LLM may over-interpret verbose instructions. Prefer:
- A single action reference over a paragraph of explanation
- A single constraint over multiple examples of what not to do
- A single routing directive over a flowchart in prose

---

## Template Adherence

**[STRONG] Prescribed templates should be enforced through repetition and validation checkpoints.**
If the instruction prescribes specific phrases, formatting, or closing lines, these need:
- Definition in the template section
- Validation checkpoint (e.g., "verify before sending: [phrase] must appear")
- The exact number of mentions needed varies — discover through testing

**[SOFT] Template specifics belong in the ticket eval, not the playbook.**
Phrases like "Here's what I found" or "Did this help?" are topic-specific. The playbook covers the PRINCIPLE of adherence; each ticket's eval defines WHAT to adhere to.

---

## Testing & Evaluation

**[HARD] Establish a baseline before making changes.**
Never evaluate a change without knowing what the current behavior is. If the user provides a baseline CSV, use it. Otherwise, run one.

**[STRONG] When new requirements change what "good" means, update eval criteria BEFORE establishing a baseline.**
Never compare new behavior against old criteria. Separate evals into: regression (unchanged), regression (modified by ticket), and new ticket criteria. If a ticket requirement flips a metric (e.g., phrase presence → absence), the metric moves to ticket eval AND regression criteria update for QA. Always HITL when flipping metrics — product may not have reviewed the implications.

**[STRONG] Verify regressions are real before fixing them.**
Deploy the original instruction and run the same test with the same context. If the baseline shows the same "regression," it's a data artifact, not an instruction problem. This check saved 3 wasted iterations in PROJ-345.

**[STRONG] Multi-turn testing is required, not optional.**
Current average conversation length is ~2.83 turns (expected to increase as agent improves). Every ticket needs at least 5 multi-turn test cases. Classify each requirement: first-response-only → single-turn, follow-up behavior → multi-turn, unclear → both.

**[STRONG] Testing depth matches the phase:**

| Phase | Utterances | Runs per utterance | Acceptance | When |
|---|---|---|---|---|
| Sandbox (dev) | Ticket-specific | 4x | 3/4 (75%) OK to iterate | During editing, per-ticket work |
| QA (pre-go-live) | Full regression set | 8x | Per ticket AC (typically stricter) | Before promoting to production |

1x runs give a false sense of accuracy — a response can pass once and fail the next 3 times. 4x minimum in sandbox catches inconsistency early.

The ticket specifies which phase applies. Default to sandbox.

**[SOFT] Account data affects results.**
Different routable IDs = different data = different behavior. Comparisons are only valid with the same account context. Not all topics need routable IDs — RAG/knowledge topics are context-independent.

---

## Multi-Topic and Regression

**[STRONG] Changes to one topic can affect other topics.**
Modifying a topic's description can reroute utterances away from other topics. Test adjacent topics when making routing-related changes.

**[SOFT] Cross-topic regression is not always required during dev.**
Two testing phases exist:
1. **Dev testing** — focused on the work itself. Test the changed topic + a few adjacent utterances.
2. **QA regression** — full regression across all topics before go-live. Required when promoting to production.

The ticket defines which phase applies. Not every ticket needs full cross-topic regression during dev.

---

## Common Failure Patterns

**[Reference] Patterns discovered across tickets. Not rules — just awareness.**

| Pattern | What happens | How to detect | How to fix |
|---|---|---|---|
| Full rewrite breaks everything | LLM shortcuts to default behavior | All utterances produce same response | Restore original, switch to surgical edits |
| Formatting drift | LLM stops using prescribed phrases | Eval shows template adherence drop | Add/strengthen validation checkpoint in instruction |
| Redundancy regression | Shorter instruction loses formatting guards | Redundancy metric increases | Restore specific formatting guidance that was removed |
| Publish drift | Bundle deployed but not published | Agent ignores instruction changes | Re-publish authoring bundle |
| Identical instructions across topics | Multiple topics share same text | Manual review or structural check | Give each topic distinct, specific instructions |

---

## HTML & Testing Center Gotchas

**[Reference] Technical issues that affect eval accuracy.**

- Testing Center output HTML-encodes characters (`&#39;` for `'`). Always use `html.unescape()` when analyzing response text.
- `sf agent preview` does NOT support context variables. Use Testing Center for service agents with linked variables.
- contextVariables in YAML must be array format: `[{name: "X", value: "Y"}]`, not object format.
- `sf agent preview` JSON output may contain control characters. Use `json.JSONDecoder(strict=False)`.

---

## Eval Structure

**[Reference] How evals are organized in this project.**

- **Three layers:** `eval-config/` (versioned scoring scripts), `baselines/` (agent-level, one per shipped version), `tickets/` (work-item scoped with numbered attempts).
- **Baselines are agent-level.** Only winning attempts promote to baseline.
- **Separate raw outputs from scored results.** Raw CSVs are expensive to regenerate. Scored reports are cheap.
- **Regression script is topic-agnostic.** `evals/scripts/generate_report.py` discovers features from data. Topic-specific eval criteria live in the ticket's config.json and specs.

---

## Evolution Process

After each ticket:
1. **Drive Phase 6** should identify any new patterns discovered during execution
2. Propose specific additions or modifications to this playbook
3. User reviews and approves before changes are made
4. Label new entries with the appropriate rule level
5. Reference the ticket that prompted the addition (e.g., "Discovered in PROJ-345")

This playbook is versioned alongside the eval-config. Major changes should be noted in `eval-config/CHANGELOG.md`.
