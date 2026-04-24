# ESCHAT Ticket Authoring Guide for adlc-drive

> Use this guide when creating JIRA tickets that will be executed by the `adlc-drive` skill. Following this structure ensures the AI agent can pick up your ticket and execute it autonomously with minimal back-and-forth.

---

## Quick Check: Will adlc-drive understand your ticket?

Before submitting, verify your ticket answers these 5 questions:

1. ☐ **What should change?** — Specific behavior, not vague goals
2. ☐ **Which agent and topic(s)?** — Named explicitly
3. ☐ **What does "done" look like?** — Measurable acceptance criteria
4. ☐ **What exists today?** — Baseline reference or link to current behavior
5. ☐ **Are there examples?** — Before/after, failing conversations, data samples

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

### Strongly Recommended Sections

**Agent & Topic** — Which agent (name + API name if known), which topic(s), which org/environment.

**Baseline** — Where's the current eval data? Attach a CSV, link to a prior eval report, or specify "needs baseline run."

**Before/After Examples** — Show what the agent says today vs what it should say. The more examples, the better the AI can pattern-match.

**Approach** — If you have a preference for how to implement (e.g., "global instructions first" or "per-topic"), state it. Otherwise, the AI will generate plan options.

### Optional Sections

**Implementation Details** — Pre-written instruction text, exact phrases to add/remove. Saves the AI from guessing.

**Testing Notes** — Specific utterances to test, routable ID requirements, multi-turn scenarios.

**Learnings** — Reference prior tickets that inform this work (e.g., "apply practices from ESCHAT-1183").

---

## Good vs Bad Examples

### ✅ Good Ticket (ESCHAT-1192 pattern)

```
Title: ADLC - Implement UXCD Voice & Tone Guidelines for ESA Agents

## Context
During the ESA Chat Review on March 24, the UXCD team identified 
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
- Prior eval: adlc/indeed-service-agent/baselines/v21/
```

**Why it works:** Specific changes per topic, measurable acceptance, baseline referenced, before/after implied.

### ❌ Bad Ticket

```
Title: Ensure "Representative" Consistency

We need to make sure we are being consistent with the use 
of representative. Check all agents.
```

**Why it fails:** No specific agent named, no requirements section, no acceptance criteria, no examples of current inconsistency, no baseline. Drive would have to ask 5+ questions before starting.

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

### Tickets That Change Eval Criteria

If your requirement changes what "good" looks like (e.g., removing a phrase that evals currently check for), call it out:

```
⚠️ Eval impact: This ticket changes the baseline metric for 
"Here's what I found" — currently scored as positive, should 
be scored as absent after implementation.
```

This prevents the AI from flagging a false regression.

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
- [ ] If SPIKE: questions and time-box specified
- [ ] If eval criteria change: flagged explicitly
