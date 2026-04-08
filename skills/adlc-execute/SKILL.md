---
name: adlc-execute
description: >-
  Plan and execute Agentforce agent instruction changes iteratively. Takes
  discovery artifacts from adlc-drive (Phase 3), plans the approach, runs
  the edit-test-evaluate loop, presents results, and handles hand off.
  Invoked by adlc-drive after discovery is complete, or directly when
  resuming a session that already completed Phases 1-3.
---

# ADLC Execute

Plan, execute, present, and hand off agent instruction changes.
This skill owns Phases 4-7. It assumes Phases 1-3 (Goal, Refine, Discover)
are complete — the conversation context contains the goal, scope, discovery
findings, acceptance criteria, and approved test specs.

The rules from `adlc-drive` Section 1 (Transparency, Checkpoints, HITL
Logging, Process Failure Recovery) apply here. If you haven't read them
in this session, read `~/.cursor/skills/adlc-drive/SKILL.md` Section 1 now.

---

## Phase 4: Plan

Based on discovery findings, produce the execution plan.

**First: Re-read the Diagnose Before Editing and Editing Instructions sections of `adlc/prompt-engineering-playbook.md` NOW using the Read tool.** Do not proceed from memory. The playbook contains the framework for classifying problems and the rules for making changes. Extract the principles that apply to THIS goal before planning.

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
- **Max iterations:** set explicitly based on scope (narrow: 3-5, moderate: 5-8, broad: 8-12)
- **Pass threshold:** default 90%, adjust per user's acceptance criteria

**4c. Generate plan options:**

For changes with multiple implementation approaches, generate 2-3 plan options with pros/cons/risks. Recommend one. If the change affects architecture, flag for HITL. If eval fails on one approach, try the next.

**⛔ CHECKPOINT:** Present to user and wait for approval:
- Plan options (2-3 if multiple approaches exist) with pros/cons
- Recommended option and WHY
- Triage classification (ship it / proctor / design review)
- Execution order (which topics/changes first)
- Test matrix (utterance counts, multi-turn ratio, run count, pass threshold)
- Max iterations
- Rollback strategy
- Estimated instruction size change (% increase/decrease)
- Any risks or concerns

---

## Phase 5: Execute

The iterative loop. This is where the work happens.

**Loop structure:**

```
FOR each iteration (max N from Phase 4b):

  1. CHANGE — Edit instruction based on the goal
     - Re-read the Editing Instructions and Testing sections of adlc/prompt-engineering-playbook.md NOW using the Read tool. Do not proceed from memory.
     - Refer to the goal and scope documented in goal.md
     - Make the targeted edit (reduce, modify, add, or restructure — whatever the goal requires)
     - If ADDING content: check % increase vs current instruction size. If exceeding playbook guidelines, pause and get user approval before proceeding.
     - If ADDING content: draft 2-3 variants of varying verbosity and placement. Present all variants to the user with pros/cons before deploying any.
     - Save new version to attempts/NN-name/instruction.txt
     - Deploy: Read ~/.cursor/skills/adlc-optimize/SKILL.md
       You need: how to deploy an updated instruction to the org (Tooling API for UI-built agents)
       Execute those steps.
     - I know you'll want to batch several changes into one iteration to move faster — don't. One change per iteration. When things break, you need to know which change caused it.

  2. SMOKE TEST (quick, per-iteration)
     - 3-5 utterances, run each 4 times (3/4 pass = acceptable): at least 1 that exercises the change, at least 1 regression canary
     - Prefer `sf agent preview` (instant, no suite creation) for topics that don't need context variables
     - Use Testing Center only if context variables are required — reuse the same suite with `--force-overwrite`, don't create new ones
     - Goal: confirm the change didn't break the basic flow. Not comprehensive.

  3. EVALUATE
     - Pass rate >= threshold? → proceed to bulk eval
     - Pass rate < threshold? → diagnose, iterate (back to step 1)
     - Ambiguous result? → PULL USER IN to confirm

  4. BULK EVAL (only when smoke tests pass)
     - Run full utterance set via Testing Center — reuse the suite created in Phase 3, `--force-overwrite` if spec changed
     - Compare: python3 adlc/scripts/generate_report.py --prev <baseline-csv> --new <new-csv> --output <report.html>

  5. ACCEPTANCE CHECK
     - All acceptance criteria met? → EXIT loop, proceed to Phase 6
     - Regression detected? → diagnose, iterate (back to step 1)
     - Ambiguous? → PULL USER IN with data

  IF max iterations reached without meeting criteria:
     - STOP
     - Present what was achieved vs what was targeted
     - Ask user: continue with more iterations, adjust criteria, or abandon?
```

Sub-skills are the source of truth for HOW. Execute decides WHAT and WHEN. When a step says "Read adlc-X/SKILL.md", read it, find the relevant section, execute, return here.

**Checkpointing:**

After each iteration, save state so progress isn't lost if the session breaks:

Save state to `.adlc-drive-state.json` in the project root. Include at minimum: goal, agent, org, current phase, iteration count, changes made so far, acceptance criteria, and status. Add whatever metrics are relevant for this specific goal — don't use a fixed schema.

Pull the user in when results are ambiguous, regressions appear, or you're stuck after 3 iterations.

---

## Phase 6: Present

After acceptance criteria are met (or max iterations reached):

1. **Propose playbook updates** — If new patterns were discovered during this ticket, propose additions to `adlc/prompt-engineering-playbook.md`. User approves before changes are made.
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
[Include whatever metrics are relevant for this goal — discovered during Phase 3d]

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

**⛔ CHECKPOINT:** Present to user and wait for approval:
- All changes made (what was edited, in which instruction records)
- Test results: baseline vs final for each metric
- Metrics that improved, held, or regressed
- Whether acceptance criteria were met (per criterion)
- Remaining risks or known gaps
- Recommendation (deploy / proctor / hold / needs more work) and WHY
- Proposed playbook updates (if new patterns discovered)

---

## Phase 7: Hand Off

Clean exit. Two paths depending on whether this goes to prod.

**7a. If deploying to prod (promote to baseline):**

The winning attempt becomes the new baseline. Baselines have two layers: **utterances** (`baselines/{topic}/utterances.txt`) are the permanent test inputs that persist across versions — Phase 7c manages those. **Version snapshots** (`baselines/v{N+1}/`) capture the instruction + eval results for a specific deployment — that's what 7a creates.

1. Ask user: "Attempt NN passed acceptance. Promote to baseline v[N+1]?"
2. If yes, copy the winning attempt's artifacts:
   ```
   adlc/{agent}/baselines/v{N+1}/
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

**7c. Update baseline utterances:**

Review if the ticket introduced behavior not covered by existing baseline utterances:
- Did this ticket add new capabilities that need new test utterances?
- Were new utterances created during Phase 3c (capability spec) that should become permanent?
- Did requirements change what "good" looks like, making some existing utterances obsolete?

If yes, propose additions/removals to the baseline utterance list (`adlc/{agent}/baselines/{topic}/utterances.txt`). Get user approval before modifying.

**7d. Always:**

- Confirm the user has reviewed the Phase 6 summary
- If proctor was recommended, note the flag strategy
- If design review was tagged, note which items need sign-off
- Clean up `.adlc-drive-state.json` (or leave as audit trail)

**Do NOT auto-deploy.** Deployment is a separate decision with its own safety gates.
