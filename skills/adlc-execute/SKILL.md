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

**4-pre. Architecture review:**

Before triaging or generating plan options, determine the work type and what sub-skills Phase 5 will need. Review the Phase 3 discovery artifacts and answer:

1. **Work type:** Is this an instruction edit (modifying existing topic instructions), a new agent authoring (creating an agent via `.agent` file), a scaffold + edit (creating missing actions then editing instructions), or a combination?
2. **Sub-skills needed:** Based on the work type, which skills will the CHANGE step in Phase 5 invoke? Map each planned change to a skill:
   - Instruction edits → `adlc-optimize` (Tooling API)
   - New agent or major rewrite → `adlc-author` (Agent Script bundle)
   - Missing Flow/Apex stubs → `adlc-scaffold`
3. **Iteration model:** For instruction edits, one iteration = one instruction change. For authoring, define what constitutes an iteration explicitly (e.g., "Iteration 1: generate .agent file. Iteration 2: publish and fix validation errors. Iteration 3: verify live actions with --use-live-actions. Iteration 4: run full eval."). Each iteration must be a single logical step with a testable outcome.
4. **Validation model:** For instruction edits, validation = smoke test utterances. For authoring, validation also includes publish success, action invocation (live, not mocked), and org metadata checks. Document what "passing" means for each iteration.
5. **Comparison model:** For instruction edits, comparison is same-agent before/after (baseline.csv vs new.csv). For authoring that replicates a source agent, comparison is cross-agent (source agent outputs vs new agent outputs for the same utterances). Document which model applies.

Log the architecture review to HITL. This review drives everything in Phase 5 — if it's wrong, the execution will be wrong.

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

  1. CHANGE — Execute the change defined by the Phase 4 plan for this iteration.
     - **Log to HITL:** "Entering Phase 5 iteration N, executing CHANGE using [skill] per Phase 4 plan." If the skill you're about to call doesn't match what Phase 4 planned, STOP — that's a process failure.
     - Re-read the Editing Instructions and Testing sections of adlc/prompt-engineering-playbook.md NOW using the Read tool. Do not proceed from memory.
     - Refer to the goal and scope documented in goal.md

     **For instruction edits (adlc-optimize path):**
     - Make the targeted edit (reduce, modify, add, or restructure — whatever the goal requires)
     - If ADDING content: check % increase vs current instruction size. If exceeding playbook guidelines, pause and get user approval before proceeding.
     - If ADDING content: draft 2-3 variants of varying verbosity and placement. Present all variants to the user with pros/cons before deploying any.
     - Save new version to attempts/NN-name/instruction.txt
     - Deploy: Read ~/.cursor/skills/adlc-optimize/SKILL.md
       You need: how to deploy an updated instruction to the org (Tooling API for UI-built agents)
       Execute those steps.
     - One change per iteration. When things break, you need to know which change caused it.

     **For new agent authoring (adlc-author path):**
     - Read ~/.cursor/skills/adlc-author/SKILL.md and execute the generation step.
     - Save the .agent file to the authoring bundle path.
     - Publish: run `sf agent publish authoring-bundle` and treat publish errors as iteration failures (back to step 1 with the fix, not ad-hoc debugging).
     - After publish succeeds, validate with `sf agent preview --authoring-bundle <name> --use-live-actions` — mocked actions do NOT count as validation. Confirm actions execute with real org data.
     - One logical step per iteration. For authoring, the iteration boundaries from Phase 4-pre apply.

     **For scaffold (adlc-scaffold path):**
     - Read ~/.cursor/skills/adlc-scaffold/SKILL.md and generate the missing stubs.
     - Deploy stubs to the org before proceeding to instruction edits or authoring that depend on them.

     The Phase 4 plan determines which path(s) you follow and in what order. Do not deviate.

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
     - Compare: python3 adlc/scripts/generate_report.py --prev <baseline-csv> --new <new-csv> --output <report.html> --json-output <report.json>

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

1. **Generate the regression report:**
   ```bash
   python3 adlc/scripts/generate_report.py \
     --prev <baseline.csv> --new <final.csv> \
     --output <ticket-folder>/eval-report.html \
     --json-output <ticket-folder>/eval-report.json \
     --title "<goal summary>"
   ```

2. **Read the JSON output and produce the AI analysis layer.** The script handles metrics; you handle judgment. Read `eval-report.json` and cross-reference against the ticket's acceptance criteria from `config.json`:

   - **Scorecard interpretation:** Are the wins in areas the ticket targeted? Are regressions in areas the ticket didn't touch (unexpected) or expected trade-offs?
   - **Acceptance criteria check:** For each criterion in `config.json`, map it to specific metrics from the JSON. State pass/fail with evidence.
   - **Tool call accuracy** (if applicable): Compute from the raw CSV using the ticket's test spec annotations — which utterances should trigger which tools. The script doesn't do this; you do.
   - **Template adherence** (if applicable): Check topic-specific response patterns from the ticket spec against the raw responses.
   - **Regression explanation:** For each regression the scorecard flagged, explain whether it's blocking or acceptable and why. Reference the specific metric values.

3. **Propose playbook updates** — If new patterns were discovered during this ticket, propose additions to `adlc/prompt-engineering-playbook.md`. User approves before changes are made.

4. Present a summary:

```markdown
## Drive Summary: <goal>

### Recommendation: [GO | NO-GO | CONDITIONAL]

### Executive Summary
<2-3 sentences: what changed, key wins, key risks. Written from the JSON scorecard data.>

### Changes Made
| # | Change | File/Topic | Iteration |
|---|--------|-----------|-----------|
| 1 | <what changed> | <where> | <which iteration> |

### Scorecard
<wins> wins | <regressions> regressions | <ties> ties

### Acceptance Criteria
| Criterion | Status | Evidence |
|---|---|---|
| <from config.json> | PASS/FAIL | <metric name: baseline → new, delta> |

### Key Metrics
| Metric | Baseline | Final | Delta | Verdict |
|---|---|---|---|---|
[Pull from JSON — focus on metrics relevant to this goal, not all 35+]

### Regressions
| Metric | Baseline | Final | Delta | Blocking? | Explanation |
|---|---|---|---|---|---|
[Only regressions. State whether each is blocking or acceptable and why.]

### Remaining Risks
- <any known gaps or edge cases>

### Artifacts
- Instruction file: <path>
- Test suite: <name in org>
- Eval report (HTML): <path>
- Eval report (JSON): <path>
- Ticket folder: <path>
```

**⛔ CHECKPOINT:** Present to user and wait for approval:
- GO / NO-GO / CONDITIONAL recommendation and WHY
- All changes made (what was edited, in which instruction records)
- Acceptance criteria: pass/fail per criterion with evidence
- Scorecard summary + key metrics
- Each regression explained (blocking vs acceptable)
- Remaining risks or known gaps
- Proposed playbook updates (if new patterns discovered)

---

## Phase 7: Hand Off

Clean exit. Two paths depending on whether this goes to prod.

**7a. If deploying to prod (promote to baseline):**

The winning attempt becomes the new baseline. Baselines have two layers: **utterances** (`baselines/{topic}/utterances.txt`) are the permanent test inputs that persist across versions — Phase 7c manages those. **Version snapshots** (`baselines/v{N+1}/`) capture the instruction + eval results for a specific deployment — that's what 7a creates.

1. Ask user: "Attempt NN passed acceptance. Promote to baseline v[N+1]?"
2. If yes, copy the winning attempt's artifacts:
   ```
   adlc/{agent-dev-name}__{org-alias}/baselines/v{N+1}/
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

If yes, propose additions/removals to the baseline utterance list (`adlc/{agent-dev-name}__{org-alias}/baselines/{topic}/utterances.txt`). Get user approval before modifying.

**7d. Always:**

- Confirm the user has reviewed the Phase 6 summary
- If proctor was recommended, note the flag strategy
- If design review was tagged, note which items need sign-off
- Clean up `.adlc-drive-state.json` (or leave as audit trail)

**Do NOT auto-deploy.** Deployment is a separate decision with its own safety gates.
