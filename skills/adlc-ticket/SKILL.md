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

## Evaluation Criteria

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

---

## Standalone Mode: Help Write a Ticket

When user provides a rough description or asks for help writing a ticket:

1. **Ask the 5 key questions** (skip any already answered)
2. **Determine scope** — is this instruction work, investigation, or infrastructure?
3. **Generate a structured ticket** following this template:

```markdown
## Context
[Why are we doing this? What triggered it?]

## Requirements
[Specific, actionable changes. Number them.]

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

4. **Present the generated ticket** for user review
5. User copies into JIRA

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

## Standalone Mode: Evaluate Existing Ticket

When user provides a JIRA key:

1. **Pull the ticket** via `user-atlassian` MCP → `getJiraIssue`
   (Cloud ID: discover via `getAccessibleAtlassianResources` on first use)
2. **Run scope check** — is this in scope for drive?
3. **Score against 5 criteria** — what's present, what's missing
4. **Check for eval criteria impact** — does this change what "good" means?
5. **Present assessment:**

```
Ticket: ESCHAT-XXXX
Score: N/5

✅ Present:
  - [element]: [what the ticket says]

❌ Missing:
  - [element]: [what's needed]

⚠️ Eval impact:
  - [any metrics that would flip or need creating]

Verdict: [Ready / Ready with gap / Needs improvement / Not ready / Out of scope]

Suggested additions:
  - [specific text to add to the ticket]
```

---

## Called by Drive: Readiness Assessment

When drive reads this skill during Phase 1:

1. Evaluate the ticket using the same criteria above
2. Return one of:

| Verdict | Drive action |
|---|---|
| **Ready** (4-5/5) | Proceed to Phase 2 |
| **Ready with gap** (4/5) | Proceed, but note the gap — drive will ask user during Phase 2 |
| **Needs improvement** (3/5) | Present gaps to user, ask them to update the ticket or provide missing info in chat |
| **Not ready** (≤2/5) | Suggest converting to SPIKE or rewriting. Do not proceed. |
| **Out of scope** | Tell user this isn't instruction work. Suggest appropriate approach. |

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

The detailed ticket guides are at `evals/ticket-guides/`:
- `ticket-authoring-prompt.md` — how to write drive-ready tickets, good/bad examples, checklist
- `ticket-evaluation-samples.md` — 15 real tickets evaluated (training material)
- `ticket-template.md` — generic JIRA template to copy
- `ticket-rewrites-internal.md` — 11 weak tickets rewritten (internal reference)
