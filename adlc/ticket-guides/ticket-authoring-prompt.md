# PROJECT Ticket Authoring Guide for adlc-drive

> Use this guide when creating JIRA tickets that will be executed by the `adlc-drive` skill. Following this structure ensures the AI agent can pick up your ticket and execute it autonomously with minimal back-and-forth.

---

## Quick Check: Will adlc-drive understand your ticket?

Before submitting, verify your ticket answers these questions:

1. ☐ **What should change?** — Specific behavior, not vague goals
2. ☐ **Which agent and topic(s)?** — Named explicitly
3. ☐ **What does "done" look like?** — Measurable acceptance criteria
4. ☐ **What exists today?** — Baseline reference or link to current behavior
5. ☐ **Are there examples?** — Before/after, failing conversations, data samples
6. ☐ **Is the scope staged or split?** — Say whether style polish, broad restructures, global instructions, or eval changes should be separate stages/tickets

Also include any known dependencies or testability limits:

- Required context variables, routable IDs, user/account/contact data, permissions, tokens, connected systems, or retriever/RAG sources
- Whether the behavior is fully testable in lower env, requires prod-like data, requires external systems, or is not lower-env testable
- Product acceptance needs for representative scenarios, tone, escalation, refusal, safety, auth, PII, or payment behavior
- Known instruction source of truth if available: `.agent` authoring bundle, UI-built Tooling API records, or unknown

If you can't answer all 5, your ticket may need a **SPIKE** first.

---

## Ticket Structure

### Required Sections

**Context** — Why are we doing this? What triggered it? Link to source docs, reviews, or conversations.

**Requirements** — What specifically needs to change. Be explicit:
- ❌ "Improve the agent's tone" (too vague)
- ✅ "Use contractions: 'you're' not 'you are'. Remove 'Here's what I found' opener. Replace closing with 'Let me know if you'd like more details about billing.'"

**Acceptance Criteria** — How we know it's done. Must be measurable:
- ❌ "Agent sounds better" (not measurable)
- ✅ "Contractions appear in >80% of responses. No individual eval metric regresses >10%."

`adlc-drive` will translate approved acceptance into `config.json` during Phase 3d. If precision matters, include explicit thresholds such as minimum pass rate, max regression delta, target word count, or required scenario count.

### Strongly Recommended Sections

**Agent & Topic** — Which agent (name + API name if known), which topic(s), which org/environment.

**Baseline** — Where's the current eval data? Attach a CSV, link to a prior eval report, or specify "needs baseline run."

**Before/After Examples** — Show what the agent says today vs what it should say. The more examples, the better the AI can pattern-match.

**Approach** — If you have a preference for how to implement (e.g., "global instructions first" or "per-topic"), state it. Otherwise, the AI will generate plan options.

**Staging / Split Guidance** — If the ticket combines broad prompt restructuring with output-style polish, global instruction changes, or eval criteria changes, state whether to split into separate tickets or stage the work.

### Optional Sections

**Implementation Details** — Pre-written instruction text, exact phrases to add/remove. Saves the AI from guessing.

**Testing Notes** — Specific utterances to test, routable ID requirements, multi-turn scenarios.

**Dependencies / Testability** — Context variables, data setup, permissions, tokens, external systems, RAG sources, and whether the scenarios are lower-env testable.

**Product Acceptance Notes** — Representative scenarios or reviewer expectations for business correctness, tone, escalation/refusal behavior, and safety-sensitive flows.

**Learnings** — Reference prior tickets that inform this work (e.g., "apply practices from PROJ-1183").

---

## Good vs Bad Examples

### ✅ Good Ticket (PROJ-1192 pattern)

```
Title: ADLC - Implement UX/content Voice & Tone Guidelines for service agents

## Context
During the service-agent review on March 24, the UX/content team identified
inconsistencies in tone across agents. Most are quick fixes.

## Requirements
### 1. Global Instructions
- Use contractions: "you're" not "you are"
- Prohibited terms: "assist", "retrieve", "fetch"
- Use "a representative" consistently

### 2. General FAQ
- Introduce lists with a colon
- Begin items with capital letter, no end punctuation

### 3. Invoice Inquiries
- Remove "Here's what I found" opening
- Replace closing: "Let me know if you'd like more details about billing"

## Acceptance
1. All guidelines implemented in instruction records
2. Full eval per agent, no metric regresses >10%
3. Before/after examples documented

## Baseline
- Baseline CSV: attached
- Prior eval: adlc/agents/example-service-agent__org-unknown/baselines/general-faq/
```

**Why it works:** Specific changes per topic, measurable acceptance, baseline referenced, before/after implied.

### ❌ Bad Ticket

```
Title: Ensure "Representative" Consistency

We need to make sure we are being consistent with the use
of representative. Check all agents.
```

**Why it fails:** No specific agent named, no requirements section, no acceptance criteria, no examples of current inconsistency, no baseline. Drive would have to ask several questions before starting.

### ❌ Bad Ticket (empty)

```
Title: Incorporate Official Content Guidelines

[no description]
```

**Why it fails:** Drive has nothing to work with. This needs to be a SPIKE first to identify what the guidelines are and which agents they apply to.

---

## Special Cases

### SPIKE Tickets

If the problem or solution is unclear, create a SPIKE:

```
Title: [SPIKE] Investigate <what>

## Goal
What do we need to learn?

## Questions
1. <specific question>
2. <specific question>

## Time-box
N days

## Output
Findings document that leads to an implementation ticket.
```

Drive will output an investigation plan and stop — it won't try to implement.

### Multi-Topic Tickets

When changes span multiple topics, specify:
- Which changes are **global** (apply to all topics)
- Which are **topic-specific**
- Suggested execution order (or let the AI decide)

If the work spans multiple response surfaces or prompt layers, prefer separate tickets unless the shared eval path and risk are clearly the same. If you keep one ticket, define stages so current-stage acceptance can pass without treating future-stage work as failure.

### Prompt Modification Breadth

Broad prompt substrate changes and output-style changes have different risk profiles. Call this out explicitly:

```
Scope plan: Stage 1 compacts/restructures the prompt while preserving current behavior. Stage 2 handles list formatting and contraction polish after Stage 1 passes.
```

This helps `adlc-drive` confirm split/staged execution during Phase 2.

### Tickets That Change Eval Criteria

If your requirement changes what "good" looks like (e.g., removing a phrase that evals currently check for), call it out:

```
⚠️ Eval impact: This ticket changes the baseline metric for
"Here's what I found" — currently scored as positive, should
be scored as absent after implementation.
```

This prevents the AI from flagging a false regression.

### Diagnostic Mode

Temporary diagnostic traces are allowed only for repeated prompt failures that cannot be diagnosed from normal traces, tool outputs, or eval data. If likely, state it as a caveat. `adlc-drive` / `adlc-execute` must get HITL approval before adding exposed user-facing diagnostic traces, record diagnostic mode in `discovery.json`, and remove/internalize traces or get product approval before final `GO`.

---

## Checklist Before Submitting

- [ ] Title starts with `ADLC -` if it's an instruction change (helps the AI identify scope)
- [ ] Context section explains WHY
- [ ] Requirements section has specific, actionable changes (not vague goals)
- [ ] Acceptance criteria are measurable (percentages, counts, or explicit pass/fail conditions)
- [ ] Agent and topic(s) named explicitly
- [ ] Baseline referenced or "needs baseline" noted
- [ ] At least one before/after example (or link to Figma/doc with examples)
- [ ] If multi-topic: global vs topic-specific changes clearly separated
- [ ] If broad prompt work plus style/output polish: split or staged execution preference stated
- [ ] If SPIKE: questions and time-box specified
- [ ] If eval criteria change: flagged explicitly
- [ ] If diagnostic traces may be needed: caveat stated and HITL expected
