# adlc-execute Output Examples (Phases 4-7)

What each phase checkpoint should look like. Adapt to the specific goal and agent.

---

## Phase 4: Plan (pauses for approval)

```
**Triage:** SHIP IT (score 0 — single topic, easy rollback, no PII impact)
**Design review:** No (no user-facing experience change)

**Plan options:**
  Option A (recommended): Section-by-section compaction, preserving structure
    Pros: Easy to diff, rollback per-section, low regression risk
    Cons: 3-4 iterations, may not hit target if structure is the bloat

  Option B: Full rewrite at target size
    Pros: Might achieve better compaction
    Cons: High regression risk, hard to diff, loses battle-tested phrasing

**Recommendation:** Option A — v22 incident showed aggressive restructuring
breaks classification. Surgical compaction preserves reasoning scaffolding.

**Test matrix:** 5 smoke tests x 4 runs per iteration, bulk eval after pass
**Max iterations:** 5
**Rollback:** Originals in originals/ folder, one Tooling API PATCH to restore
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
| Regression (unchanged) | 95% | 93% | -2% (within threshold) |

### Remaining Risks
- 2% regression on edge-case multi-turn follow-ups (within 10% threshold)

### Recommendation
- [x] Ready to deploy (invoke `adlc-deploy`)

### Artifacts
- Instruction: adlc/indeed-service-agent/tickets/ESCHAT-1234/attempts/03/instruction.txt
- Test suite: ESCHAT-1234-invoice-compaction
- Eval report: adlc/indeed-service-agent/tickets/ESCHAT-1234/attempts/03/eval-report.html
```
