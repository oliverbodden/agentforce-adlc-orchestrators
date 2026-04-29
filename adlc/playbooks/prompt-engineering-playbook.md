# Prompt Engineering Playbook

Living document. Updated as we learn from each ticket. The agent consults this when writing, reviewing, or changing Agentforce instructions. Humans consult it when reviewing or writing instructions manually.

This playbook is for prompt and instruction strategy, craft, implementation, and review. For Agentforce runtime architecture, topic/subagent routing, action/data dependencies, non-prompt root-cause selection, and testability classification, read `adlc/playbooks/agentforce-architecture-playbook.md` first.

Do not assume a ticket is an instruction problem. Use the architecture playbook to classify the failure surface before applying prompt guidance here. Once the likely fix is prompt-facing, this playbook owns how to inspect the current prompt, choose the prompt surface, decide targeted edit versus restructure, and validate the prompt change.

---

## Quick Routing Index

Use this index first. The playbook is intentionally detailed, but most runs need only the section that matches the current failure mode.

| Situation | Read |
|---|---|
| Planning a prompt-facing change | `Prompt Strategy` |
| Need to decide targeted edit vs restructure | `Prompt Strategy` → `Targeted Edit Vs Restructure Gate` |
| Prompt edits failed repeatedly | `Diagnostics` → `Diagnostic Logs For Repeated Prompt Failures` |
| Diagnostic logs do not explain the failure | `Diagnostics` → `Prompt Reduction For Failure Isolation` |
| Agent ignores a clear instruction | `Diagnostics` → `Diagnose Before Editing` |
| Agentforce hides internal logs | `Diagnostics` → `Agentforce Diagnostic Trace Pattern` |
| Prompt is too long or redundant | `Editing Patterns` → `Editing Instructions` |
| Output format/template is inconsistent | `Editing Patterns` → `Template Adherence` |
| Need test/eval strategy | `Validation And Evaluation` |
| Need platform/runtime context | `Reference: How Agentforce Works` |

Operational rule: `adlc-execute` owns the trigger; this playbook owns the recipe. When execution says to use diagnostics or prompt reduction, come here for the detailed technique.

---

## Reference: How Agentforce Works

Historical architecture summary retained for context. The authoritative local architecture reference is now `adlc/playbooks/agentforce-architecture-playbook.md`. If this section conflicts with that file or current Salesforce docs, use the architecture playbook and update this summary later.

### The Runtime Flow

```
User utterance
  → TOPIC SELECTION: OpenAI call with all topic classifications
    → "Which topic should handle this?" → Returns topic name
      → INSTRUCTION READING: OpenAI call with topic instructions + tool definitions
        → "Which actions should I call?" → Returns action list
          → ACTION EXECUTION: Call Flows/Apex/Prompt Templates/Retrievers
            → Raw data returned into context window
              → RESPONSE GENERATION: OpenAI call with instructions + tool data
                → Answer generated
                  → TRUSTED LAYER: Grounding/safety check (may loop 1-2x)
                    → Response sent to user
```

### Key Concepts

**Topics are sub-agents.** Each has its own classification (WHEN to call it), instructions (WHAT to do), and actions (HOW to get data). More topics = more maintenance + more classification risk. If classification fails, everything downstream fails — this is the #1 priority to get right.

**Classification lives in `GenAiPlannerAttrDefinition`.** This is the Salesforce object that defines topic routing rules — which utterances get routed to which topic. The ADLC skills do not currently read or edit this table. If a ticket requires changing topic routing or classification boundaries, query `GenAiPlannerAttrDefinition` directly via Tooling API.

**Instructions are the presentation layer for action output.** Actions (Flows, Apex, Prompt Templates) return raw data — invoice details, job status, knowledge articles. Instructions tell the LLM how to format, frame, and present that data to the user. When editing instructions, you're changing the presentation of data that flows through actions. The actions don't change, but their output is referenced in templates within the instruction.

**The runtime prompt includes (in order):** System rules (can't modify) → Scope → Your topic instructions → Tool/action definitions (auto-initialized with descriptions) → Action input/output field descriptions → Additional system rules. All of this goes to OpenAI as one prompt.

**Action instructions exist at multiple levels:**
- Action-level description: tells the LLM what the action does and when to use it
- Input field descriptions: tells the LLM what data each field expects
- Output field descriptions: tells the LLM what data comes back
- Topic instruction references: your instructions that tell the LLM how to USE the action output

All of these are injected into the same prompt. Contradictions between any of these levels cause inconsistent behavior.

**Prompt templates are nested sub-prompts.** They're stateless — no conversation history, no context unless you pass it in. They can call RAG retrievers and other resources. Their output goes back into the main agent's context window. Latency risk: each sub-prompt adds a round trip.

**Global instructions** are injected at runtime into every topic. Unclear exactly when they appear relative to topic instructions. Duplication between global and topic instructions is common as a workaround, but creates maintenance burden.

**System instructions** are built-in and can't be modified. They sometimes conflict with your custom instructions. When debugging inconsistent behavior, check if a system rule is overriding your instruction.

**The trusted layer** runs after the response is generated. It can loop 1-2 times, re-evaluating and modifying the output. You may see the response change in real time — that's the trusted layer iterating.

### What This Means for Instruction Editing

| When you change... | Also check... |
|---|---|
| Topic instructions | Action descriptions that reference the same behavior |
| Response templates | Field references to action output (invoiceNumber, jobStatus, etc.) |
| Terminology or tone | All levels — global, topic, action descriptions, closing lines |
| Classification/description | Impact on ALL other topics' routing — utterances may shift |
| Closing lines or openers | Content rules and validation checkpoints that enforce them |
| Adding new content | Potential conflicts with system rules you can't see or modify |

### Where Things Break

| Failure point | What happens | How to detect |
|---|---|---|
| Topic classification | Wrong topic selected → wrong instructions run | Check trace: first step shows which topic was picked |
| Action selection | Wrong action called or right action not called | Check trace: action step shows which tools were offered |
| Contradicting instructions | Inconsistent responses (works 9/10, fails 1/10) | One instruction wins over another randomly — check ALL instruction levels |
| Missing input data | Action called before required data is available | Action errors with null fields — check if instructions tell LLM to collect data first |
| Trusted layer loop | Response changes after generation, adds latency | Trace shows multiple grounding steps |
| Prompt template statelessness | Sub-prompt has no conversation context | Template gives generic answer — check if context was passed via input fields |

### Prompt Mental Model Checklist

When you pull an instruction in Phase 3, extract and document:

- [ ] **Prompt purpose:** What job is this prompt trying to do?
- [ ] **Structure:** What sections/phases does it have? (e.g., UNDERSTAND → GATHER → BUILD)
- [ ] **Control flow:** Where does it classify intent, ask clarification, call tools, handle tool output, and compose the final response?
- [ ] **Actions referenced:** Which actions does it call? What data do they return?
- [ ] **Templates:** What response templates are prescribed? (exact openers, closings, formats)
- [ ] **Content rules:** What MUST/NEVER directives exist? (e.g., "MUST include 'Here's what I found'")
- [ ] **Terminology:** What terms are enforced? (e.g., "always say representative")
- [ ] **Formatting:** Bold rules, list rules, link formatting, currency formatting
- [ ] **Field references:** Which action output fields are referenced in templates? (e.g., `invoiceNumber`, `jobStatus`)
- [ ] **Escalation logic:** When/how does it escalate? What triggers it?
- [ ] **Guardrails:** What is the instruction told NOT to do?
- [ ] **Reasoning scaffolding:** Store: blocks, checkpoints, consistency checks — mark these as load-bearing
- [ ] **Conflicts with ticket:** Which of the above conflicts with what the ticket asks to change?
- [ ] **Insertion points:** Where can new content be added without breaking existing logic?
- [ ] **Structure assessment:** Is this `targeted-edit-safe`, `messy-but-workable`, or `restructure-recommended`?

Present this analysis at the Phase 3 checkpoint. Do not proceed to Phase 4 without it.

---

## How to Use This Playbook

- **Before planning:** Read `adlc/playbooks/agentforce-architecture-playbook.md` and confirm the failure belongs in instructions.
- **During instruction edits:** Use the Prompt Implementation Strategy section to decide how to change the prompt, then review the relevant principles below.
- **Tie-breakers:** When a ticket's requirements conflict with a playbook principle, see the Rule Levels section.
- **Evolving:** After each ticket, drive should propose updates to this playbook in Phase 6 if new patterns were discovered. The user approves before changes are made.

---

## Prompt Strategy

Use this section after architecture discovery shows the likely fix is prompt-facing, or when instructions are one viable strategy that must be compared against other surfaces. The architecture playbook decides whether this is really an instruction problem; this playbook decides how to implement instruction changes well.

Phase timing:

- **Phase 2 / Refine:** Use only enough prompt awareness to ask good questions. Do not design exact wording yet.
- **Phase 3 / Discover:** Read the full affected prompt after originals are saved. Build the prompt mental model and structure assessment before baseline/test design.
- **Phase 4 / Plan:** Use the mental model to choose targeted edit versus restructure, prompt surface, prompt goal, options, risks, and validation path.
- **Phase 5 / Execute + Iterative Evaluate:** Implement the approved strategy one logical prompt change at a time and evaluate each iteration.
- **Phase 6 / Present Final Evaluation:** Propose playbook updates only after evidence shows a reusable pattern.

### 1. Question The Ticket Before Editing

Do not treat the ticket's requested implementation as automatically correct. Separate:

- **Business goal:** What user-facing behavior needs to change?
- **Requested method:** Did the ticket ask for topic instructions, global instructions, action descriptions, prompt templates, eval changes, or a new topic/action?
- **Evidence:** Does live prompt/tool/test evidence support that method?
- **Acceptance definition:** Does the ticket change what "good" means?

If the requested method is weaker than another prompt-facing method, present the trade-off before editing. If the best method is not prompt-facing, exit through the architecture playbook and HITL.

### 2. Build A Prompt Mental Model

Before writing new text, explain the current prompt to yourself. This belongs in Phase 3 after originals are saved and before Phase 4 planning:

- What is the prompt's main job?
- Which sections are load-bearing?
- Which steps control understanding, tool calls, response composition, and final checks?
- Which action/tool outputs does the prompt rely on?
- Which rules are global style rules versus task-specific logic?
- Which instructions are likely obsolete, duplicated, or contradicted?
- Where is the prompt already trying to solve the ticket's goal?

Do not edit until you can point to the current lines that govern the behavior or explain why no governing line exists.

### 3. Choose The Prompt Surface

For prompt-facing fixes, choose the narrowest surface that can reliably change behavior:

| Surface | Use when |
|---|---|
| Global instruction | The rule applies consistently across topics and should not be duplicated. |
| Topic instruction | The behavior belongs only to one topic's reasoning or response style. |
| Action description | The model is choosing the wrong tool or missing when to call it. |
| Input field description | The model passes the wrong value, format, context, or search query to a tool. |
| Output field description | The model misunderstands or underuses returned data. |
| Prompt template | The generated tool response itself needs structure, tone, or context changes. |
| Eval criteria | The definition of "good" changed and must be scored separately. |

If two prompt surfaces are viable, produce 2-3 strategies with expected benefits, risks, and validation paths. Eval results decide when the choice is not obvious.

### 4. Pick The Edit Strategy

Match the edit to the observed prompt problem:

| Prompt problem | Preferred strategy |
|---|---|
| Missing rule | Add one concise rule near the relevant decision point. |
| Ambiguous rule | Rewrite the existing rule; do not add a duplicate override. |
| Contradictory rules | Remove or reconcile the conflict instead of adding a louder third rule. |
| Rule buried too late | Move or summarize the rule near the top-level decision point. |
| Tool query is poor | Improve the query-building instruction or input field description. |
| Tool output is good but final response is poor | Adjust BUILD/output rules, not GATHER/tool rules. |
| Prompt is too long | Compact redundancy while preserving load-bearing scaffolding. |
| Ticket asks for style/format | Add measurable output rules plus examples only where needed. |
| Current prompt is structurally unsound | Propose a limited restructure and gate it with fuller eval coverage. |

### 5. Targeted Edit Vs Restructure Gate

Default to a targeted edit. Prompt restructure increases blast radius and should not be used just because the prompt could be cleaner.

Use a targeted edit when:

- The existing prompt has a coherent control flow.
- The desired behavior has a clear insertion point.
- Existing rules mostly agree with the ticket goal.
- The change can be validated with focused smoke tests plus regression coverage.

Use `messy-but-workable` when:

- The prompt has duplication or awkward structure, but a narrow insertion point is still safe.
- The ticket can be solved without changing the prompt's overall control flow.
- Restructure would consume scope without clear validation benefit.

Recommend restructure only when:

- Current instructions directly contradict each other in a way that blocks the goal.
- The prompt lacks a reliable control flow for understanding, gathering, and building responses.
- The targeted edit would require scattered overrides in multiple sections.
- Prior approved targeted iterations failed and evidence suggests structure is the blocker.
- The current structure makes evaluation unreliable because the model cannot consistently follow the intended decision path.

If restructure is recommended, HITL is required before implementation. The Phase 4 plan must explain why targeted edits are insufficient, what structure is proposed, which behavior might regress, and what broader eval coverage will protect against that risk.

### 6. Define The Prompt Goal

For each change, write a one-sentence prompt goal before editing:

```text
Make <specific model decision or output behavior> happen in <specific context> without weakening <existing behavior to preserve>.
```

Examples:

- Make `General FAQ` responses use natural contractions in normal explanatory text without changing escalation wording or quoted knowledge article titles.
- Make list responses use colon-introduced, capitalized, punctuation-free list items without forcing lists when prose is better.
- Reduce redundant instruction text while preserving `Store:` fields, tool-call requirements, and final quality checks.

### 7. Validate The Strategy Before Implementation

Prompt strategy is not complete until it names:

- The exact prompt surface to edit.
- The expected behavior change.
- Existing behavior that must not regress.
- Test cases that prove the change.
- Eval criteria that are unchanged, modified, or new.
- Any product/HITL approval needed because "good" changed.

If a prompt edit cannot be validated in the available environment, do not treat it as complete.

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

## Diagnostics

Use this section when the right prompt edit is not obvious, when a clear rule is not being followed, or when repeated iterations fail without explaining why.

### Diagnose Before Editing

**[STRONG] Classify why something isn't working before deciding how to fix it.**

When a behavior is wrong, the fix depends on the root cause — not the symptom. Before writing any edit, classify. For trivially obvious fixes (typo, missing closing phrase), skip the full classification.

| Root cause | Right fix | Wrong fix |
|---|---|---|
| Instruction is missing | Add it | — |
| Instruction scope is too narrow | Widen the scope | Add a duplicate elsewhere |
| Instruction wording is ambiguous | Clarify the wording | Add more words |
| Instruction is clear but not followed | Investigate why — model limit? context window? contradicted by another instruction? | Make it "louder" or add emphasis |
| Instruction is contradicted by another | Resolve the contradiction | Add a third instruction to override both |
| Problem is outside instructions entirely | Exit ramp (see Editing Instructions) | Attempt an instruction workaround |

**How to classify:** Find the specific line in the current instruction that should govern the behavior. Then:
1. **Line doesn't exist** → missing. Add it.
2. **Line exists but doesn't cover this case** → scope. Widen it.
3. **Line exists, covers this case, but could be read two ways** → ambiguous. Reword it.
4. **Line exists, is clear, and still not followed** → compliance failure. Adding more text won't help. Investigate: is another instruction contradicting it? Is it buried too deep? Is the context window too full?

This applies to both Agentforce agent instructions (Phase 5 edits) and to the ADLC skills themselves (postmortem improvements). Discovered in PROJ-1192.

---

### Diagnostic Logs For Repeated Prompt Failures

**[STRONG] If prompt edits keep failing and you cannot see why, diagnose the decision path before adding more instructions.**

Use diagnostic logs when the agent repeatedly misses a prompt requirement and normal traces, tool outputs, and eval results do not reveal the failing layer. The goal is to identify whether the issue is classification, routing, tool choice, tool input, tool-output interpretation, retrieval, strategy selection, template selection, response construction, or final compliance.

Diagnostic logs must be hypothesis-driven:

1. State the hypothesis for what is causing the failure.
2. Identify the internal decision variables that would confirm or refute it.
3. Add diagnostic fields for those variables.
4. Run focused tests.
5. Use the logs to confirm/refute the hypothesis.
6. If the logs do not explain the failure, revise the hypothesis and update the diagnostic template.

Do not assume every prompt uses `UNDERSTAND / GATHER / BUILD`. First build the prompt mental model, then mirror that prompt's own decision architecture. A routing prompt might log `CLASSIFY / ROUTE / HANDOFF`; a RAG prompt might log `QUERY / RETRIEVE / RANK / ANSWER`; a tool prompt might log `INTENT / TOOL / INPUTS / OUTPUTS / RESPONSE`.

The diagnostic template should be custom, structured, and named after the prompt's real control variables. If the prompt has `RequestType`, `ServiceStrategy`, `KnowledgeData_Usable`, `Goal addressed`, or `Closing line`, log those exact variables. Avoid generic "explain your reasoning" traces because they are noisy and less actionable.

Example hypothesis-to-log mapping:

| Hypothesis | Useful diagnostic fields |
|---|---|
| Wrong routing/classification | Candidate intents/topics considered, selected intent/topic, rejected candidates and why, trigger words, continuity state |
| Wrong tool choice or skipped tool | Tool candidates considered, selected tool, skipped tools and why, tool eligibility gate, required inputs available |
| Bad tool input | Raw user request, generalized query, stripped user-specific details, final tool input, input self-check |
| Tool data misread | Raw key fields, usability decision, data summary, goal addressed, user claim addressed |
| Bad response construction | Selected strategy/template, facts used, facts withheld, abstraction/compression level, redundancy check, closing line |
| Trusted layer / output suppression | Draft output contract, final output contract, forbidden terms, whether diagnostic trace appeared, which insertion points were active |

#### Agentforce Diagnostic Trace Pattern

Agentforce may hide or suppress internal reasoning through its trusted output layer. If internal-only logs are not visible enough to debug the failure, a temporary diagnostic trace may need to be framed as explicit user-facing transparency content. This is a development-only diagnostic override and should be approved by the user.

A single line usually is not enough. To expose logs reliably, reinforce the diagnostic trace in all key prompt layers:

- top-level diagnostic/transparency requirement
- response format after function calls
- strategy/mode templates
- output rules
- diagnostic template section
- final no-exceptions reminder

The trace should tell the agent to report the exact variables the prompt uses, in the same names and order where possible. The point is not to reveal generic chain-of-thought; the point is to reveal the prompt's operational state.

When productionizing, remove or internalize the trace from every insertion point. Missing one insertion point can keep logs leaking. Compare the clean version against the diagnostic version because exposed traces can change behavior by forcing the model to commit to decisions before drafting the user-facing response.

Temporary diagnostic logs are not automatically an acceptance failure during development. They become a production blocker only when the run is ready for final user-facing acceptance and product has not approved exposed transparency output.

---

### Prompt Reduction For Failure Isolation

**[STRONG] When diagnostic logs do not identify the failing layer, reduce the prompt with fast focused tests before broad regression.**

Prompt reduction is a diagnostic technique for isolating the true failure layer. Temporarily remove, neutralize, or simplify one prompt section at a time and run focused canaries to see whether the target behavior starts working. The goal is not to produce the final prompt; the goal is to find the causal layer.

Use prompt reduction after diagnostic logs are active, not as a blind first move. Keep the diagnostic trace on during reduction so each removal can be tied to a change in classification, routing, tool choice, strategy selection, or response construction. Without logs, reduction can show that behavior changed, but not why.

Use prompt reduction when:

- Repeated prompt edits fail and diagnostic logs do not fully explain why.
- The logs show the agent chooses the right path, but final output is still wrong.
- A tool-output pass-through rule, prompt template, global instruction, topic instruction, trusted layer, or final output rule may be overriding the desired behavior.
- The target behavior works only when a prompt section is removed or simplified.

Reduction loop:

1. State the hypothesis, such as "the final output contract is overriding list formatting."
2. Pick one prompt layer or section to neutralize.
3. Save a reversible diagnostic attempt.
4. Run small preview/unit-style canaries, not a full Testing Center regression.
5. Compare behavior and diagnostic variables against the previous attempt.
6. Restore the removed section if it is not causal, or keep reducing around the causal area if behavior changes.
7. Convert the finding into a targeted final edit, then retest normally.

Good reduction targets:

| Suspected blocker | Reduction experiment |
|---|---|
| Final output contract overrides style | Temporarily neutralize only the final output contract or final compliance checklist |
| Tool output pass-through blocks formatting | Temporarily replace "pass through unchanged" with "preserve facts but format per output rules" |
| Prompt template controls final answer | Temporarily simplify or bypass template-specific wording where safe |
| Global and topic rules conflict | Temporarily neutralize one layer and test the same canary |
| Diagnostic scaffold changes behavior | Test with diagnostic trace active, then internalized, then removed |
| Trusted layer suppresses output | Add a diagnostic field for draft-vs-final output contract and test whether suppression is consistent |

Guardrails:

- One section/layer per reduction attempt.
- Always save the exact reduced prompt and the restore point.
- Use focused canaries first; broad regression comes after a candidate fix exists.
- Do not remove safety, escalation, privacy, or authorization behavior without HITL.
- Do not leave a reduced prompt as the final answer unless it is converted into a deliberate, reviewed prompt edit.

---

## Editing Patterns

### Instruction Structure

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

### Editing Instructions

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

### Template Adherence

**[STRONG] Prescribed templates should be enforced through repetition and validation checkpoints.**
If the instruction prescribes specific phrases, formatting, or closing lines, these need:
- Definition in the template section
- Validation checkpoint (e.g., "verify before sending: [phrase] must appear")
- The exact number of mentions needed varies — discover through testing

**[SOFT] Template specifics belong in the ticket eval, not the playbook.**
Phrases like "Here's what I found" or "Did this help?" are topic-specific. The playbook covers the PRINCIPLE of adherence; each ticket's eval defines WHAT to adhere to.

---

## Validation And Evaluation

### Testing & Evaluation

**[HARD] Establish a baseline before making changes.**
Never evaluate a change without knowing what the current behavior is. If the user provides a baseline CSV, use it. Otherwise, run one.

**[STRONG] When new requirements change what "good" means, update eval criteria BEFORE establishing a baseline.**
Never compare new behavior against old criteria. Separate evals into: regression (unchanged), regression (modified by ticket), and new ticket criteria. If a ticket requirement flips a metric (e.g., phrase presence → absence), the metric moves to ticket eval AND regression criteria update for QA. Always HITL when flipping metrics — product may not have reviewed the implications.

**[STRONG] Verify regressions are real before fixing them.**
Deploy the original instruction and run the same test with the same context. If the baseline shows the same "regression," it's a data artifact, not an instruction problem. This check saved 3 wasted iterations in PROJ-345.

**[STRONG] Routable ID handling.**
Some topics need a MessagingSession routable ID for testing (topics that call account-specific actions like Invoice retrieval or Account lookup). RAG/knowledge-only topics (e.g., General FAQ) do NOT need one. When building test specs:
- Ask the user for a fresh routable ID if the topic needs one — they expire hourly
- `sf agent preview` does NOT support context variables — use Testing Center only
- contextVariables in YAML must be array format: `[{name: "RoutableId", value: "0Mw..."}]` — NOT object format
- If tests fail with session errors, the ID likely expired — ask for a new one
- Different routable IDs give different account data — comparisons are only valid with the same ID

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

### Multi-Topic and Regression

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

### HTML & Testing Center Gotchas

**[Reference] Technical issues that affect eval accuracy.**

- Testing Center output HTML-encodes characters (`&#39;` for `'`). Always use `html.unescape()` when analyzing response text.
- `sf agent preview` does NOT support context variables. Use Testing Center for service agents with linked variables.
- contextVariables in YAML must be array format: `[{name: "X", value: "Y"}]`, not object format.
- `sf agent preview` JSON output may contain control characters. Use `json.JSONDecoder(strict=False)`.

---

### Eval Structure

**[Reference] How evals are organized in this project.**

- **Two layers:** `baselines/` (permanent utterances + version snapshots, agent-level) and `tickets/` (work-item scoped with numbered attempts).
- **Baselines are agent-level.** Only winning attempts promote to baseline.
- **Separate raw outputs from scored results.** Raw CSVs are expensive to regenerate. Scored reports are cheap.
- **Two-layer reporting model:**
  - **Layer 1 — Script:** `adlc/scripts/generate_report.py` computes all metrics from CSV data: scorecard (wins/regressions/ties), strategy distribution, formatting compliance, opening behavior, response length buckets, multi-turn awareness, redundancy, consistency, and a filtered response comparison appendix. Outputs HTML report + optional JSON sidecar (`--json-output`).
  - **Layer 2 — AI (Phase 6):** Reads the JSON output, cross-references against the ticket's acceptance criteria from `config.json`, and produces the executive summary, GO/NO-GO recommendation, tool call accuracy analysis, and template adherence checks. Topic-specific intelligence lives here, not in the script.

---

## Evolution Process

After each ticket:
1. **Drive Phase 6** should identify any new patterns discovered during execution
2. Propose specific additions or modifications to this playbook
3. User reviews and approves before changes are made
4. Label new entries with the appropriate rule level
5. Reference the ticket that prompted the addition (e.g., "Discovered in PROJ-345")
