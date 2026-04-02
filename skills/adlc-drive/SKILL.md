---
name: adlc-drive
description: >-
  Goal-driven Agentforce agent improvement. Takes a goal or requirement,
  refines it collaboratively, discovers baseline state, plans and triages
  the work (proctor/design review/SPIKE/ship-it), executes changes via
  other ADLC skills, iterates until acceptance criteria are met, and
  presents results. Use when the user has a goal, improvement, bug fix,
  or feature request for an Agentforce agent.
---

# ADLC Drive

Orchestrate goal-driven agent improvements end-to-end: from intake through
execution to verified results. This skill owns the *what* and *why*; it
delegates the *how* to other ADLC skills (`adlc-optimize`, `adlc-test`,
`adlc-author`, `adlc-scaffold`, `adlc-discover`).

---

## 1. ROLE

Drive is the **brain**, not the hands. It:
- Tracks the goal and acceptance criteria across the entire session
- Decides which skill to invoke and when
- Evaluates results against criteria after each iteration
- Pulls the user in when decisions are ambiguous
- Stops when done (or when stuck)

**Delegation map:**

| Capability | Delegated to |
|---|---|
| Evaluate ticket readiness, help write tickets | `adlc-ticket` |
| Read/edit topic instructions, trace analysis, agent improvement | `adlc-optimize` |
| Run tests, bulk evals, export results | `adlc-test` |
| Resolve agent/topic metadata in org | `adlc-discover` |
| Generate missing Flow/Apex stubs | `adlc-scaffold` |
| Build new agent or major rewrite | `adlc-author` |
| Deploy, publish, activate | `adlc-deploy` (user invokes separately) |

---

## 2. PHASES

### Phase 1: Goal

Capture what the user wants to achieve.

**Input:** One of:
- JIRA ticket key/URL → auto-pull goal, requirements, attachments (see Section 4)
- Open text → user describes the goal directly

If no ticket is provided, ask the user to be specific:
```
To get started, I need either:
1. A JIRA ticket key (e.g., ESCHAT-1234)
2. A detailed description covering:
   - What should change in the agent's behavior?
   - Which agent and topic?
   - Do you have examples of current behavior (good or bad)?
   - Do you have a baseline eval CSV or test utterances?
   - What does "done" look like?

The more detail you provide upfront, the fewer back-and-forth questions we'll need.
```

Extract and confirm:

| Field | Required | How to get it |
|---|---|---|
| **Goal** | Yes | What should be different after this work? |
| **Goal type** | Yes | Classify from ticket/description (see below) |
| **Agent name** | Yes | From ticket or ask |
| **Agent version** | Yes | If ticket specifies, confirm. If ambiguous, ask. |
| **Edit strategy** | Yes | Edit in-place or clone first? If ticket specifies, confirm. If ambiguous, ask. |
| **Org alias** | Yes | From project config or ask |
| **Attachments** | No | Baseline CSV, example conversations, data samples — from ticket or user |

**Goal type:** Classify from the ticket description. Common types include compaction, fix, new experience, new data integration, investigation — but any goal is valid. If the ticket describes something new, create an appropriate type label and adapt the phases accordingly.

**Key questions to determine how Phases 3-5 behave:**

1. **Does the instruction get smaller, bigger, or restructured?** → Determines the edit approach.
2. **Are there examples of bad experiences to fix?** → Look for attached conversations, screenshots, or failure descriptions in the ticket.
3. **Does this introduce new data or APIs?** → Understand the schema and where it fits.
4. **Do we need NEW test utterances, or can we reuse existing ones?** → If the goal changes behavior, we need utterances that exercise the new behavior. If it preserves behavior, existing utterances suffice for regression.
5. **Is the problem clear enough to act on?** → If not, SPIKE first.

Document the answers in the ticket folder's `goal.md`.

**1b2. Evaluate ticket readiness:**

→ Read `~/.cursor/skills/adlc-ticket/SKILL.md`
  You need: evaluate if this ticket has enough context for drive to execute
  Execute the assessment. If verdict is "Not ready" or "Out of scope", stop and tell the user.
  If "Needs improvement", present gaps and ask user to fill them before proceeding.
  If "Ready" or "Ready with gap", continue.

**1c. Resolve agent/topic metadata:**

→ Read `~/.cursor/skills/adlc-discover/SKILL.md`
  You need: how to resolve agent and topic IDs for a Salesforce org (may or may not have an authoring bundle)
  Execute those steps. Store: agent_api_name, plugin_definition_id, instruction_def_ids, has_authoring_bundle
  These IDs are used throughout Phases 3-5.

Do NOT ask for acceptance criteria yet — that comes in Phase 3 after discovery.

### Phase 2: Refine

Collaborative back-and-forth to ensure alignment before any work starts.

**2a. Scope the change:**

Discuss with the user until these are clear:
- Which **topic(s)** are involved? (or is it a new topic?)
- Which **actions** are affected? (existing, new, or broken?)
- Which **prompt templates** or instructions need attention?
- Which **channels/surfaces** does this affect? (chat, phone, messaging, FAQ)
- Are there **dependencies** (new Flows, Apex, knowledge articles)?

**2b. Early uncertainty check (SPIKE gate):**

Before investing in discovery, ask:

> "Do we understand the problem AND the solution well enough to proceed?"

| Answer | Action |
|---|---|
| Problem unclear | **SPIKE** — exit early with investigation plan (see SPIKE template below) |
| Problem clear, solution unclear | **SPIKE** — focused on solution design |
| Both clear enough | Proceed to Phase 3 |

**SPIKE output (if triggered):**

```markdown
## SPIKE: <title>
Goal: <what we need to learn>
Time-box: <N days>
Output: Findings that re-enter this flow at Phase 1
Questions to answer:
1. <specific question>
2. <specific question>
Suggested investigation:
- <step — e.g., "run adlc-optimize Phase 1 to pull STDM sessions">
- <step — e.g., "review Data Cloud for escalation patterns">
```

If SPIKE, present it and stop. Do not proceed to Phase 3.

**2c. Confirm alignment:**

Summarize what you understood back to the user. Get explicit confirmation before Phase 3.

```
Here's what I understand:
  Goal: <goal>
  Agent: <name> on <org>
  Scope: <topics/actions affected>
  Surfaces: <channels>
  Dependencies: <any>

Does this look right? Anything I'm missing?
```

### Phase 3: Discover

Gather evidence about the current state. This phase establishes the **baseline** that Phase 5 will measure against.

**3a. Pull current instructions + audit for conflicts:**

Use the agent/topic IDs resolved in Phase 1 step 1c.

→ Read `~/.cursor/skills/adlc-optimize/SKILL.md`
  You need: how to read the current topic instruction from the org (for UI-built agents without authoring bundles, look for the Tooling API path)
  Execute those steps. Store: instruction text, word count for ALL affected instruction records (global + per-topic).

Then audit: do any existing instructions contradict the new guidelines? Flag conflicts (e.g., existing instruction says "use Here's what I found" but ticket says remove it). Document conflicts in goal.md.
  Then continue to 3c.

**3c. Check existing evals:**

→ Read `~/.cursor/skills/adlc-test/SKILL.md`
  You need: how to check if a Testing Center test suite already exists for this agent
  Execute those steps. Note any recent results.
  Then continue to 3d.

**3d. Establish baseline + build test utterances:**

**Combine ALL available sources (AND, not OR):**
1. **Baseline CSV** (from user or run via `adlc-test`) → regression utterances
2. **Ticket attachments** → examples of bad/new behavior
3. **Derived from instruction + requirements** → edge cases, gaps

**Coverage check:** Map every ticket requirement to at least one test utterance. If a requirement has no utterance exercising it, derive one.

**Multi-turn awareness:** Consider if the goal changes behavior across turns. For each requirement, classify:
- "First response changes" → single-turn test
- "Follow-up behavior changes" → multi-turn test (use `conversationHistory` in YAML spec)
- Topics that naturally require multiple turns (e.g., invoice selection → explanation) need multi-turn even for single-turn changes

**Guardrails:**
- Minimum 5 multi-turn test cases per ticket (catches conversation continuity issues)
- Maximum ~50 utterances per ticket. If the change is comprehensive and needs more, HITL — ask user if scope should be split.

**Split eval criteria into three buckets:**
1. **Regression (unchanged)** — existing criteria that still apply as-is
2. **Regression (modified)** — existing criteria the ticket changes. These move to ticket eval AND update regression for QA.
3. **New ticket criteria** — entirely new metrics from requirements

Store regression spec and capability spec separately in `specs/`.
  Then continue to 3e.

**3e. Analyze baseline and establish acceptance criteria:**

Before proposing criteria, analyze the baseline CSV to understand current metrics:
- Run `python3 evals/scripts/generate_report.py --prev <baseline.csv> --new <baseline.csv> --output /tmp/baseline-analysis.html` (comparing baseline to itself gives you the feature profile)
- Or manually: count utterances, compute response feature rates, check redundancy, measure response lengths
- Identify which metrics are relevant for THIS topic (not all topics have the same features)

Then propose acceptance criteria based on goal type:

```
Baseline: X utterances, key features: [list discovered from CSV]

Proposed criteria:
  1. Regression: no existing metric drops more than [threshold from ticket, default 10%]
  2. Goal-specific: [derived from the goal — e.g., "bad experience fixed in N/N cases" or "new behavior works in >X% of relevant utterances"]
  3. Show-stoppers: [from ticket AC]
  4. New test utterances (if applicable): [list]
```

Document the criteria in the ticket folder's `config.json`.

**⚠️ HITL required** when existing eval criteria are being modified or flipped. The user must confirm that changing what "good" means was intentional — product or dev may not have reviewed the implications of flipping a metric.

Get explicit user confirmation before proceeding.

### Phase 4: Plan

Based on discovery findings, produce the execution plan.

**4a. Triage classification:**

| Gate | Question | Outcome |
|---|---|---|
| Design review | Does this change what users see or how they interact? | Tag for **DESIGN REVIEW** (parallel — doesn't block execution planning) |
| Risk score | See blast radius scoring below | **SHIP IT** (0) / **JUDGMENT CALL** (1) / **PROCTOR** (2+) |

**Blast radius scoring (1 point each):**

- Touches more than one topic?
- Affects >10% of sessions (estimate from baseline data)?
- Hard to roll back?
- Touches PII, auth, payment, or escalation flows?
- Changes system-level instructions (affects all topics)?

| Score | Verdict |
|---|---|
| 0 | **SHIP IT** |
| 1 | **JUDGMENT CALL** — default to proctor if unsure |
| 2+ | **PROCTOR** — feature flag, gradual ramp |

**4b. Determine test matrix:**

Scale testing to the change scope. These are starting guidelines — adjust based on the topic's complexity and the user's requirements:
- **Narrow change** (single instruction edit): ~5 smoke tests, 3 scenarios
- **Moderate change** (new behavior or multi-section edit): ~10 tests, 5 scenarios
- **Broad change** (system-level or multi-topic): ~15 tests, 7 scenarios
- **Pass threshold:** default 90%, adjust per user's acceptance criteria

**4c. Generate plan options:**

For changes that could be implemented multiple ways (e.g., global vs per-topic, merge vs separate), generate 2-3 plan options:

```markdown
## Plan Options

### Option A: <approach name>
- Strategy: <e.g., add guidelines to global instructions>
- Pros: <e.g., single source of truth, no duplication>
- Cons: <e.g., may not be granular enough per topic>
- Risk: <impact on architecture>

### Option B: <approach name>
- Strategy: <e.g., per-topic instructions>
- Pros/Cons/Risk...

### Option C: <hybrid>
...

### Recommended: <which option and why>

Classification: [SHIP IT | PROCTOR | DESIGN REVIEW]
Risk score: N/5
Test Matrix: <N tests, threshold, max iterations>
Rollback: <how to undo>
```

The AI evaluates the impact of each option. If the change affects architecture (e.g., moving logic between global and topic-level), flag for HITL. Otherwise, AI can pick the best option, execute it, and let eval results determine if the approach works. If eval fails, try next option.

Get user approval on the recommended plan before executing.

### Phase 5: Execute

The iterative loop. This is where the work happens.

**Loop structure:**

```
FOR each iteration (max N per Phase 4b):

  1. CHANGE — Edit instruction based on the goal
     - Consult evals/prompt-engineering-playbook.md for editing principles and rule levels
     - Refer to the key questions answered in Phase 1 and documented in goal.md
     - Make the targeted edit (reduce, modify, add, or restructure — whatever the goal requires)
     - If ADDING content: check % increase vs current instruction size. If exceeding playbook guidelines, pause and get user approval before proceeding.
     - Save new version to attempts/NN-name/instruction.txt
     - Deploy: Read ~/.cursor/skills/adlc-optimize/SKILL.md
       You need: how to deploy an updated instruction to the org (Tooling API for UI-built agents)
       Execute those steps.
     - One change per iteration (don't batch multiple changes)

  2. SMOKE TEST
     - Read ~/.cursor/skills/adlc-test/SKILL.md
       You need: how to create a YAML spec, run a Testing Center suite, and export results to CSV
       Use a small spec (5 utterances). Execute, store CSV.

  3. EVALUATE
     - Pass rate >= threshold? → proceed to bulk eval
     - Pass rate < threshold? → diagnose, iterate (back to step 1)
     - Ambiguous result? → PULL USER IN to confirm

  4. BULK EVAL (only when smoke tests pass)
     - Read ~/.cursor/skills/adlc-test/SKILL.md
       You need: run full Testing Center suite (all utterances), export CSV
       Execute, store CSV.
     - Compare: python3 evals/scripts/generate_report.py --prev <baseline-csv> --new <new-csv> --output <report.html>

  5. ACCEPTANCE CHECK
     - All acceptance criteria met? → EXIT loop, proceed to Phase 6
     - Regression detected? → diagnose, iterate (back to step 1)
     - Ambiguous? → PULL USER IN with data

  IF max iterations reached without meeting criteria:
     - STOP
     - Present what was achieved vs what was targeted
     - Ask user: continue with more iterations, adjust criteria, or abandon?
```

**How delegation works in this skill:**

When a step says "Read ~/.cursor/skills/adlc-X/SKILL.md", do this:
1. Read the skill file
2. Find the section that matches the stated need (use reasoning — don't scan the whole file if you can identify the right section quickly)
3. Follow those instructions to complete the step
4. Return to the drive flow and continue with the next step

Sub-skills are the source of truth for HOW to do things. Drive decides WHAT and WHEN.

If you already read a sub-skill earlier in this session, reuse what you learned — don't re-read the full file. Only re-read if you need a different section than before.

**Shared script** (regression comparison — not a sub-skill):
- `evals/scripts/generate_report.py` — run regression comparison, generate HTML report

**Principles and learnings are in `evals/prompt-engineering-playbook.md`.** Consult it before editing instructions. The playbook has rule levels (HARD/STRONG/SOFT) and tie-breaker guidance for when ticket requirements conflict with principles.

**Checkpointing:**

After each iteration, save state so progress isn't lost if the session breaks:

Save state to `.adlc-drive-state.json` in the project root. Include at minimum: goal, agent, org, current phase, iteration count, changes made so far, acceptance criteria, and status. Add whatever metrics are relevant for this specific goal — don't use a fixed schema.

**When to pull the user in:**

- Pass rate is between 80-90% (close but not meeting threshold)
- A previously passing test now fails (regression trade-off)
- The fix for issue A breaks issue B
- Three consecutive iterations without improvement
- Bulk eval results are mixed (some dimensions improved, others regressed)

### Phase 6: Present

After acceptance criteria are met (or max iterations reached):

1. **Propose playbook updates** — If new patterns were discovered during this ticket, propose additions to `evals/prompt-engineering-playbook.md`. User approves before changes are made.
2. Present a summary:

```markdown
## Drive Summary: <goal>

### Result: [ACHIEVED | PARTIALLY ACHIEVED | NOT ACHIEVED]

### Changes Made
| # | Change | File/Topic | Iteration |
|---|--------|-----------|-----------|
| 1 | <what changed> | <where> | <which iteration> |

### Test Results
| Metric | Baseline | Final | Delta |
|---|---|---|---|
[Include whatever metrics are relevant for this goal — discovered during Phase 3e]

### Remaining Risks
- <any known gaps or edge cases>

### Recommendation
- [ ] Ready to deploy (invoke `adlc-deploy`)
- [ ] Needs design review on: <items>
- [ ] Deploy behind proctor — flag: <name>, ramp: <plan>

### Artifacts
- Instruction file: <path>
- Test suite: <name in org>
- Eval report: <path to HTML>
- Ticket folder: <path>
```

### Phase 7: Hand Off

Clean exit. Two paths depending on whether this goes to prod.

**7a. If deploying to prod (promote to baseline):**

The winning attempt becomes the new baseline. This is the ONLY way baselines are created.

1. Ask user: "Attempt NN passed acceptance. Promote to baseline v[N+1]?"
2. If yes, copy the winning attempt's artifacts:
   ```
   evals/{agent}/baselines/v{N+1}/
     instruction-{topic}.txt    ← from attempts/NN/instruction.txt
     raw-outputs.csv            ← from attempts/NN/ (QA 8x run, not dev 4x)
     metadata.json              ← record: version, date, ticket, scoring version, org state
     eval-report.html           ← from attempts/NN/
   ```
3. The baseline raw-outputs.csv should be from a **QA-level eval (8x runs)**, not the dev smoke test. If only dev-level (4x) exists, run a QA eval before promoting.
4. Remind user to invoke `adlc-deploy` for the actual org deployment.

**7b. If NOT deploying yet (keep in sandbox):**

- Roll back org to previous baseline instruction
- Leave the winning attempt in the ticket folder — it's ready for promotion later
- Note in STATUS.md which attempt is the candidate

**7c. Always:**

- Confirm the user has reviewed the Phase 6 summary
- If proctor was recommended, note the flag strategy
- If design review was tagged, note which items need sign-off
- Clean up `.adlc-drive-state.json` (or leave as audit trail)

**Do NOT auto-deploy.** Deployment is a separate decision with its own safety gates.

---

## 3. RESUMPTION

If a session breaks mid-execution, check for `.adlc-drive-state.json` at startup:

```bash
if [ -f .adlc-drive-state.json ]; then
  echo "Found in-progress drive session"
  cat .adlc-drive-state.json
fi
```

If found, offer to resume:

```
I found an in-progress drive session:
  Goal: <goal>
  Phase: <phase>, iteration <N>
  Current pass rate: <X%>

Resume from where we left off, or start fresh?
```

---

## 4. JIRA INTEGRATION

### Connection

Uses the official Atlassian MCP server (`user-atlassian`) via OAuth SSO. No credentials stored locally.

**First use:** Call `getAccessibleAtlassianResources` to discover available cloud IDs. Store the cloud ID for subsequent calls. If multiple resources exist, ask the user which one.

### Allowed Tools (READ-ONLY)

| Tool | Purpose |
|---|---|
| `getJiraIssue` | Fetch a ticket by key |
| `searchJiraIssuesUsingJql` | Search tickets with JQL |
| `getVisibleJiraProjects` | List projects |
| `searchAtlassian` | Full-text search |

**⛔ NEVER call these tools:** `createJiraIssue`, `editJiraIssue`, `addCommentToJiraIssue`, `transitionJiraIssue`, `addWorklogToJiraIssue`, `createIssueLink`. This skill is read-only.

### Usage in Phase 1 (Goal)

When user provides a JIRA ticket (URL or key):

```
adlc-drive ESCHAT-1234
adlc-drive https://indeed.atlassian.net/browse/ESCHAT-1234
```

1. Extract the ticket key (e.g., `ESCHAT-1234`)
2. Call `getJiraIssue` with `cloudId` and `issueIdOrKey`
3. Extract and map fields:

| JIRA field | Maps to |
|---|---|
| `fields.summary` | Goal title |
| `fields.description` | Goal details, requirements |
| `fields.issuetype.name` | Goal type hint (Story/Bug/Task) |
| `fields.status.name` | Current status |
| `fields.assignee.displayName` | Owner (informational) |
| `fields.priority` (if present) | Urgency |
| `fields.labels` (if present) | Affected surfaces, topic hints |

4. Parse description for acceptance criteria (look for "Requirements", "AC", "Acceptance Criteria" headings)
5. Present the normalized goal to user for confirmation (Phase 1 output)
6. Use the ticket key as the eval ticket folder name: `tickets/ESCHAT-1234-<short-description>/`

### Authentication

If `getJiraIssue` fails with auth error, call `mcp_auth` on the `user-atlassian` server to trigger browser OAuth flow. The user authenticates via SSO — no tokens stored.

```
CallMcpTool(server="user-atlassian", toolName="mcp_auth", arguments={})
```

### Example

```
User: "adlc-drive PROJ-123"

→ getAccessibleAtlassianResources() → get cloudId
→ getJiraIssue(cloudId=<discovered>, issueIdOrKey="PROJ-123")
→ Extract: goal, requirements, attachments
→ Present to user for confirmation
→ Proceed to Phase 2 (Refine)
```
