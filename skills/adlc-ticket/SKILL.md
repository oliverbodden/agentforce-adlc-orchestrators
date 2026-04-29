---
name: adlc-ticket
description: >-
  Create or evaluate Agentforce agent tickets for adlc-drive. Use standalone
  to help write drive-ready tickets, or called by adlc-drive to assess if a
  ticket has enough context to execute. Supports JIRA tickets and free text.
---

# ADLC Ticket

Create well-structured tickets or evaluate existing ones for `adlc-drive` readiness.

## Two Modes

**Standalone:** User wants help writing or improving a ticket.
```
adlc-ticket "I need to update the tone for our FAQ agent"
adlc-ticket ESCHAT-1117
```

**Called by drive:** Drive Phase 1 needs to know if a ticket is ready.
```
(drive reads this skill → evaluates ticket → returns readiness assessment)
```

Same evaluation logic. Output format differs by mode.

---

## Quick Routing

| Situation | Read |
|---|---|
| User wants to write or improve a ticket | `Mode 1: Write / Improve Ticket` |
| User provides an existing JIRA ticket | `Mode 2: Evaluate Existing Ticket` |
| `adlc-drive` calls this skill for readiness | `Mode 3: Called By Drive` |
| Ticket is prompt-facing with multiple requirements | `Readiness Checks` → `Prompt Modification Breadth Assessment` |
| Ticket changes what "good" means | `Readiness Checks` → `Eval Criteria Assessment` |
| Ticket might be a SPIKE | `Readiness Checks` → `Scope Check` and `Mode 1` SPIKE template |

---

## Readiness Checks

### 5 Required Elements

Every drive-ready ticket must answer:

| # | Question | What to look for | Weight |
|---|---|---|---|
| 1 | **What should change?** | Specific behavior changes, not vague goals. Before/after examples. | Critical |
| 2 | **Which agent and topic(s)?** | Named explicitly — agent name, topic name, org. | Critical |
| 3 | **What does "done" look like?** | Measurable acceptance criteria — percentages, counts, pass/fail. | Critical |
| 4 | **What exists today?** | Baseline reference — CSV, prior eval, link to current behavior. | Important |
| 5 | **Are there examples?** | Before/after responses, failing conversations, data samples. | Important |

### Scoring

| Score | Meaning | Verdict |
|---|---|---|
| 5/5 | All elements present and specific | **Ready** — drive can execute |
| 4/5 | One element missing or vague | **Ready with gap** — drive can proceed but will need to ask 1 question |
| 3/5 | Two elements missing | **Needs improvement** — return gaps to user before proceeding |
| 2/5 or below | Multiple critical elements missing | **Not ready** — suggest rewrite or convert to SPIKE |

### Scope Check

Before scoring, determine if the ticket is even in scope for drive:

| Ticket is about... | In scope? | Action |
|---|---|---|
| Instruction/prompt changes (tone, format, logic, templates) | **Yes** | Evaluate and proceed |
| Investigation with unclear problem | **Yes — as SPIKE** | Evaluate for SPIKE readiness |
| Apex/Flow/infrastructure changes | **No** | Flag as out of scope for drive |
| UI/frontend changes | **No** | Flag as out of scope |
| Process/monitoring/dashboards | **No** | Flag as out of scope |
| Mixed (instruction + infrastructure) | **Partial** | Identify which parts drive can handle |

### Quality Signals

Beyond the 5 required elements, check for:

**Good signals** (increase confidence):
- Structured sections (Context, Requirements, Acceptance)
- Before/after examples with exact text
- References to prior tickets or learnings
- Explicit eval criteria or baseline data
- Agent and topic API names (not just display names)
- Implementation details or suggested approach

**Warning signals** (decrease confidence):
- Vague goals ("improve", "fix", "update" without specifics)
- No examples of current behavior
- No acceptance criteria or just "it should work better"
- Multiple unrelated changes in one ticket
- References to people but not to systems/agents
- Screenshots with no text description

### Eval Criteria Assessment

If the ticket introduces changes that affect what "good" looks like:
- Flag any existing eval metrics that would need to flip (e.g., removing a prescribed phrase)
- Flag any new metrics that don't exist in current evals
- Note: "This ticket changes eval criteria — HITL required before drive proceeds"

### Prompt Modification Breadth Assessment

For prompt-facing tickets, assess whether the requested changes should be split or explicitly staged before `adlc-drive` starts:

| Prompt change shape | Recommendation |
|---|---|
| Localized rule change on one response surface | Keep one ticket |
| Multiple style/output rules on the same response surface | Keep one ticket, but recommend staged execution |
| Broad compaction, restructure, or prompt rewrite plus style/output polish | Recommend separate tickets, or one ticket with explicit staged acceptance |
| Multiple topics/actions affected | Recommend split unless a true global instruction layer intentionally owns the behavior |
| Structural prompt change that other requirements depend on | Recommend that structural work be its own first-stage ticket or first-stage acceptance gate |

When recommending split/stage, do not mark the ticket "Not ready" solely for breadth if the goal and acceptance criteria are otherwise clear. Instead, add a **Scope warning** and a concrete recommendation:

```text
Scope warning: This ticket combines broad prompt substrate work with output-style criteria. Recommend splitting compaction/restructure into its own ticket, or explicitly approving staged execution where Stage 1 reaches compaction acceptance before style criteria are attempted.
```

---

## Mode 1: Write / Improve Ticket

When user provides a rough description or asks for help writing a ticket:

1. **Ask the 5 key questions** (skip any already answered)
2. **Determine scope** — is this instruction work, investigation, or infrastructure?
3. **Assess prompt modification breadth** if this is prompt-facing. If the request combines broad compaction/restructure with style/output polish, ask whether the user wants separate tickets or one explicitly staged ticket before drafting.
4. **Generate a structured ticket** following this template:

```markdown
## Context
[Why are we doing this? What triggered it?]

## Requirements
[Specific, actionable changes. Number them.]

## Execution / Staging
[If broad prompt substrate work is combined with output polish, state the approved staging: e.g., Stage 1 compaction acceptance, Stage 2 list formatting, Stage 3 contractions. If split into separate tickets, list the proposed ticket split.]

### [Sub-section per topic if multi-topic]

## Acceptance Criteria
[Measurable. Percentages, counts, or explicit pass/fail.]

## Agent & Topic
- Agent: [name] ([API name])
- Topic(s): [list]
- Org: [alias]
- Version: [which version to edit]

## Baseline
[Link to CSV, prior eval, or "needs baseline run"]

## Examples
[Before/after response text, or link to doc with examples]
```

5. **Present the generated ticket** for user review
6. User copies into JIRA

### For SPIKE tickets:

```markdown
## Goal
[What do we need to learn?]

## Questions
1. [Specific question]
2. [Specific question]

## Time-box
[N days]

## Output
[What the investigation produces — findings doc, recommendation, implementation ticket]
```

---

## Mode 2: Evaluate Existing Ticket

When user provides a JIRA key:

1. **Pull the ticket** via `user-atlassian` MCP → `getJiraIssue`
   (Cloud ID: discover via `getAccessibleAtlassianResources` on first use)
2. **Run scope check** — is this in scope for drive?
3. **Score against 5 criteria** — what's present, what's missing
4. **Check for eval criteria impact** — does this change what "good" means?
5. **Assess prompt modification breadth** — should this be split or staged before drive?
6. **Present assessment:**

```
Ticket: ESCHAT-XXXX
Score: N/5

✅ Present:
  - [element]: [what the ticket says]

❌ Missing:
  - [element]: [what's needed]

⚠️ Eval impact:
  - [any metrics that would flip or need creating]

⚠️ Scope / staging:
  - [prompt modification breadth warning, split recommendation, or "none"]

Verdict: [Ready / Ready with gap / Needs improvement / Not ready / Out of scope]

Suggested additions:
  - [specific text to add to the ticket]
```

---

## Mode 3: Called By Drive

When drive reads this skill during Phase 1:

1. Evaluate the ticket using the same criteria above
2. Include eval impact and prompt modification breadth warnings in the readiness response
3. Return one of:

| Verdict | Drive action |
|---|---|
| **Ready** (4-5/5) | Proceed to Phase 2 |
| **Ready with gap** (4/5) | Proceed, but note the gap — drive will ask user during Phase 2 |
| **Needs improvement** (3/5) | Present gaps to user, ask them to update the ticket or provide missing info in chat |
| **Not ready** (≤2/5) | Suggest converting to SPIKE or rewriting. Do not proceed. |
| **Out of scope** | Tell user this isn't instruction work. Suggest appropriate approach. |

If a ticket is otherwise ready but has prompt modification breadth risk, return `Ready with scope warning` in the narrative and tell drive to confirm split/staged execution during Phase 2.

---

## JIRA Access

Same as adlc-drive:
- Uses `user-atlassian` MCP server (OAuth SSO, read-only)
- `getJiraIssue` with cloudId + issueIdOrKey
- `getAccessibleAtlassianResources` to discover cloudId on first use
- If auth fails, call `mcp_auth`

**⛔ NEVER call write tools.** This skill is read-only.

---

## Reference

The detailed ticket guides are at `adlc/ticket-guides/`:
- `ticket-authoring-prompt.md` — how to write drive-ready tickets, good/bad examples, checklist
- `ticket-evaluation-samples.md` — 15 real tickets evaluated (training material)
- `ticket-template.md` — generic JIRA template to copy
- `ticket-rewrites-internal.md` — 11 weak tickets rewritten (internal reference)
