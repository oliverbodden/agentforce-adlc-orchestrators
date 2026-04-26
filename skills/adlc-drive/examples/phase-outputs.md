# adlc-drive Output Examples (Phases 1-3)

What each phase checkpoint should look like. Adapt to the specific goal and agent.

---

## Phase 1: Goal (output only)

```
**Goal understanding:**
The ticket asks to compact the Invoice Inquiries topic instruction to ~60% of its
current length without degrading response quality. Current instruction is 2,847 words.

**Ticket readiness:** Ready (score 4/5 — missing: explicit baseline utterances,
but we can derive from instruction).

**What I know:** Target agent, topic, and compaction target.
**What I still need:** Agent version, org environment, edit strategy, which
sections are load-bearing vs removable.

**Assumptions:** The 60% target is word count, not character count. Compaction
means restructuring/tightening, not removing functionality.
```

## Phase 2: Refine (pauses for approval)

```
**Full scope:**
Compact the Invoice Inquiries instruction from ~2,847 words to ~1,700 words.
Preserve all Store directives, step checkpoints, and classification logic.
Target: DEV org, v30, Tooling API edits.

**In scope:** Instruction text compaction, response format tightening.
**NOT in scope:** Action changes, flow modifications, other topics.

**SPIKE gate:** No SPIKE needed — the path is clear (surgical compaction).

**Open questions:** None remaining.
**Assumptions:** Store directives are load-bearing (based on v22 rollback where
removing them caused ESCALATE instead of EXPLAIN). Will verify in Phase 3.
```

## Phase 3: Discover checkpoint (pauses for approval)

```
**Metadata:** indeed-service-agent, BotDef 0XxQi..., Planner v30, 1 instruction record
**Originals:** Saved to originals/invoice-inquiries-1C7Em...txt (2,847 words)
**Conflicts:** None — compaction doesn't contradict existing behavior

**Test specs:** 25 regression + 12 capability = 37 total (5 multi-turn)
**Coverage:** All 4 ticket requirements mapped to utterances

**Baseline (fresh run):**
  Pass rate: 92% (34/37)
  Key features: "Here's what I found" 88%, contractions 45%, EXPLAIN strategy 90%

**Acceptance criteria:**
  1. Regression: no metric drops >10%
  2. Goal: word count ≤1,700 (from 2,847)
  3. Show-stopper: EXPLAIN strategy must stay ≥85%
```

## HITL Log Entry (after any checkpoint)

```json
{"ts":"2026-03-27T15:10:00Z","session_id":"chat-af810067","phase":"2-refine","checkpoint":"scope-approval","type":"approval","asked":"Compact Invoice Inquiries from 2847 to ~1700 words, DEV org, v30, Tooling API","decision":"Approved, preserve Store directives","agent":"indeed-service-agent","topic":"invoice","ticket":"ESCHAT-1234","who":"obguzman","org":"devesa3","agent_version":"30","edit_strategy":"tooling-api"}
```

## Hand off to adlc-execute

After Phase 3 approval:
```
Phase 3 complete. All discovery artifacts approved. Invoking adlc-execute for Phase 4 (Plan).
→ Reading ~/.cursor/skills/adlc-execute/SKILL.md
```
