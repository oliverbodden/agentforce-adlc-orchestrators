# adlc-drive Output Examples

What each phase checkpoint should look like. These are representative — adapt
to the specific goal and agent.

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

## Phase 4: Plan (pauses for approval)

```
**Plan options:**

Option A (recommended): Section-by-section compaction
  - Pros: Preserves structure, easy to diff, rollback per-section
  - Cons: Slower (3-4 iterations), may not hit 60% if structure is the bloat
  - Risk: Low

Option B: Full rewrite with same requirements
  - Pros: Might achieve better compaction, fresh structure
  - Cons: High regression risk, hard to diff, loses battle-tested phrasing
  - Risk: High

**Recommendation:** Option A — the v22 incident showed that aggressive restructuring
breaks classification. Surgical compaction preserves the reasoning scaffolding.

**Triage:** SHIP IT (score 0 — single topic, easy rollback, no PII impact)
**Design review:** No (no user-facing experience change)

**Test matrix:** 10 smoke tests, 5 scenarios, 90% pass threshold
**Rollback:** Original saved in originals/ folder, one Tooling API PATCH to restore
**Estimated size:** 2,847 → ~1,700 words (40% reduction)
```

## Phase 6: Present (pauses for approval)

```
## Drive Summary: Compact Invoice Inquiries instruction

### Result: ACHIEVED

### Changes Made
| # | Change | File/Topic | Iteration |
|---|--------|-----------|-----------|
| 1 | Merged duplicate validation blocks | Invoice Inquiries | 1 |
| 2 | Collapsed response templates | Invoice Inquiries | 2 |
| 3 | Tightened step descriptions | Invoice Inquiries | 3 |

### Test Results
| Metric | Baseline | Final | Delta |
|---|---|---|---|
| Word count | 2,847 | 1,682 | -41% |
| Overall pass rate | 92% | 94% | +2% |
| EXPLAIN strategy accuracy | 88% | 90% | +2% |
| Regression (unchanged utterances) | 95% | 93% | -2% (within threshold) |

### Remaining Risks
- 2% regression on edge-case multi-turn follow-ups (within 10% threshold)

### Recommendation
- [x] Ready to deploy (invoke `adlc-deploy`)
- [ ] Needs design review on: n/a
- [ ] Deploy behind proctor: n/a

### Artifacts
- Instruction file: evals/indeed-service-agent/tickets/ESCHAT-1234/attempts/03/instruction.txt
- Test suite: ESCHAT-1234-invoice-compaction
- Eval report: evals/indeed-service-agent/tickets/ESCHAT-1234/attempts/03/eval-report.html
- Ticket folder: evals/indeed-service-agent/tickets/ESCHAT-1234/
```

## HITL Log Entry (what gets appended after each checkpoint)

```json
{"ts":"2026-03-27T15:10:00Z","session_id":"chat-af810067","phase":"4-plan","checkpoint":"approve-plan","type":"approval","asked":"Approve Option A: section-by-section compaction, 10 tests, 90% threshold","decision":"Approved, but preserve Store directives — they're load-bearing","agent":"indeed-service-agent","topic":"invoice","ticket":"ESCHAT-1234","who":"obguzman"}
```
