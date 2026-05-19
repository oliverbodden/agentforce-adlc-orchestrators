# v7-proxy multiplier baseline (extracted from v4 999-case run)

**Source:** `HelpIQ_Legacy_v4_999_5_9_1_results.json`
**Multiplier-expected cases:** 78 of 999 (7%)

**Why this is the v7 baseline:** The multiplier sub-agent's
`reasoning.instructions` is byte-identical between v4 and v7 per
`AGENT_VERSION_REGISTRY.md` 2026-05-15 entry. The cross-version
drop on v7 vs v4 is documented as welcome-only-fallback rate
change (47% → 58%), not prompt-driven. For prompt-edit AC #1,
v4 multiplier-row metrics are the canonical baseline; welcome-only
rate is the separately-tracked guardrail.

## Per-metric pass rates (multiplier-expected subset)

| Metric | PASS | Other | Total | Pass rate | AC #1 floor (−5pp) |
|---|---:|---:|---:|---:|---:|
| `topic_assertion` | 57 | 21 | 78 | 73% | ≥ 68% |
| `actions_assertion` | 47 | 31 | 78 | 60% | ≥ 55% |
| `output_validation` | 30 | 48 | 78 | 38% | ≥ 33% |
| `completeness` | 46 | 32 | 78 | 58% | ≥ 53% |
| `coherence` | 77 | 1 | 78 | 98% | ≥ 93% |
| `conciseness` | 64 | 14 | 78 | 82% | ≥ 77% |

## Welcome-only fallback baseline (guardrail metric)

- welcome-only: **0 / 78** (0%)
- substantive (≥25 words): 72 / 78
- empty/short: 6 / 78

Welcome-only rate is the registry-documented separate failure mode
(non-prompt). HELPEXP-286 acceptance must NOT cause this rate to
worsen (≤ +3pp), but does NOT need to improve it.

## Catalog app coverage in multiplier-expected subset

| App | Cases |
|---|---:|
| Idash | 9 |
| N8N | 6 |
| Seismic | 6 |
| Glean | 6 |
| Figma | 6 |
| Claude | 6 |
| Tableau | 6 |
| Waldo | 3 |
| Mechabugs | 3 |
| Floqast | 3 |
| Cursor | 3 |
| Slack | 3 |
| Zoom | 3 |
| Asana | 3 |
| Huddle | 3 |
| Grammarly | 3 |
| DocuSign | 3 |