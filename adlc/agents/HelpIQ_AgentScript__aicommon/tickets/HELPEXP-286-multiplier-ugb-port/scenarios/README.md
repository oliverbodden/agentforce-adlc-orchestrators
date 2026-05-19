# Multi-turn scenarios — HELPEXP-286 (Multiplier UGB port)

**Purpose.** Cover AC #2, AC #3, AC #4, AC #6, and AC #7 with deterministic multi-turn fixtures. The 999-case Test Center suite (used for AC #1) is single-turn and cannot exercise the Confirm gate or the Answer-vs-Submit split.

**Format.** Deterministic scripted conversations as YAML, one file per scenario, structured for replay via `sf agent preview send` with sequential `--message` calls or via a small driver script that reads the YAML turns and sequences them. Inherits the existing `SW-ACCESS-*.yaml` shape but moves from `simulator_rules` (free-form simulator behavior) to `script:` (fixed user replies per turn). This addresses the HELPEXP-274 prior HITL insight about deterministic replay — non-deterministic simulators add noise to a 10-scenario suite at the same scale that KB non-determinism does to single-turn batteries.

**Why deterministic, not simulator.** AC #2 / #3 / #7 grade tool-call sequences and Service Strategy classifications. A free-form simulator inserts model noise into the input side (what the user says) on top of model noise on the agent side. Deterministic scripts isolate agent variance, which is what we're trying to measure.

---

## Coverage matrix (proposed at Phase 3 checkpoint)

Target: **12 scenarios**, ≥8 distinct catalog apps, all 5 Service Strategy buckets, all 5 behavioral categories. AC #4 minimum is 10–15, we're targeting the middle of the range for review tractability.

| # | Scenario ID | App(s) | Category | Service Strategy buckets exercised | Determinism subset (AC #7)? |
|---|---|---|---|---|---|
| 1 | `SW-CONFIRM-01-figma-happy-path` | Figma | straightforward-action-Confirm-Submit | Acknowledge → GATHER → **Confirm** → **Submit** | ✓ |
| 2 | `SW-CONFIRM-02-figma-decline-confirm` | Figma | straightforward-action / negative path | Acknowledge → GATHER → **Confirm** → user "no" → re-offer / **Escalate** | |
| 3 | `SW-ANSWER-01-zoom-basic-auto` | Zoom (Basic) | auto-provisioned-Answer-path | UNDERSTAND classifies informational → GATHER → **Answer** (no Submit) | ✓ |
| 4 | `SW-ANSWER-02-tableau-viewer-q` | Tableau (Viewer) | auto-provisioned-Answer-path / qualifier | UNDERSTAND classifies informational + qualifier → **Clarify** then **Answer** | |
| 5 | `SW-CLARIFY-01-zoom-vs-zoom-phone` | Zoom / Zoom Phone | qualifier-disambiguation | **Clarify** (Zoom vs Zoom Phone) → user picks → branch into Answer or Confirm-Submit | ✓ |
| 6 | `SW-CLARIFY-02-claude-desktop-vs-code` | Claude Desktop / Claude Code | qualifier-disambiguation | **Clarify** → user picks → Confirm-Submit | |
| 7 | `SW-CLARIFY-03-tableau-creator-vs-viewer` | Tableau | multi-license-tier + multi-option-retrieval | GATHER returns multi-option → **Clarify** (GATHER-informed) → Confirm-Submit | |
| 8 | `SW-CLARIFY-04-salesforce-multi-org` | Salesforce | multi-license-tier + multi-option-retrieval | GATHER multi-option → **Clarify** → user picks → Confirm-Submit | |
| 9 | `SW-CLARIFY-05-adobe-cc-vs-acrobat` | Adobe Creative Cloud / Acrobat | qualifier-disambiguation + multi-option-retrieval | **Clarify** → GATHER → Confirm-Submit | ✓ |
| 10 | `SW-ESCALATE-01-unsupported-app` | "Tableau Cloud Premium Plus" (catalog miss) | escalate path | UNDERSTAND → GATHER returns empty → **Escalate** (offer ticket) | |
| 11 | `SW-ESCALATE-02-decline-then-frustrated` | Figma | empathy / decline path | Acknowledge → Confirm → user declines + frustrated → **Escalate** (empathic) | |
| 12 | `SW-VAGUE-01-vague-start-must-clarify` | (none) | UNDERSTAND skip-GATHER | "i need software access" → **Clarify** (no Submit, no Glean call) | ✓ |

**Distinct catalog apps covered:** Figma, Zoom (Basic + Phone), Tableau (Viewer + Creator), Claude (Desktop + Code), Salesforce, Adobe (Creative Cloud + Acrobat). Counting variants of the same brand-app as one app for AC #4 minimum: **6 unique brands**. **Adding two more from the existing baseline scenarios brings us to 8:** SW-ACCESS-02 (Zoom multiple types, partial overlap with #3/#5) and a new `SW-CONFIRM-03-asana-happy-path` and `SW-CONFIRM-04-keeper-password-manager` to hit ≥8. Update at Phase 5 authoring.

**Determinism subset (AC #7):** scenarios 1, 3, 5, 9, 12 = 5 scenarios × N=3 = 15 runs. Covers each of Confirm-Submit, Answer, Clarify-disambiguation, Clarify-multi-option, and skip-GATHER paths.

**Service Strategy bucket coverage:**
- Clarify: 1, 4, 5, 6, 7, 8, 9, 12 (8 scenarios)
- Answer: 3, 4 (2 scenarios)
- Confirm: 1, 2, 5 (Zoom-Phone branch), 6, 7, 8, 9, 11 (most)
- Submit: 1, 5 (Zoom-Phone branch), 6, 7, 8, 9 (most)
- Escalate: 2, 10, 11 (3 scenarios)

All 5 buckets ✓.

**Behavioral category coverage:**
- multi-license-tier: 7, 8
- qualifier-disambiguation: 4, 5, 6, 9
- multi-option-retrieval: 7, 8, 9
- auto-provisioned-Answer-path: 3, 4
- straightforward-action-Confirm-Submit: 1, 2, 11

All 5 categories ✓.

---

## Existing reusable fixtures (from `baselines/HelpIqAgentMultiplierSoftwareRequests/scenarios/`)

| File | Status for HELPEXP-286 |
|---|---|
| `SW-ACCESS-01-figma-happy-path.yaml` | Adapt → `SW-CONFIRM-01-figma-happy-path` (add Confirm turn + Confirm acceptance criteria) |
| `SW-ACCESS-02-zoom-multiple-access-types.yaml` | Adapt → `SW-CLARIFY-07-zoom-multiple-tiers` (8th scenario for ≥8 apps) |
| `SW-ACCESS-03-vague-start-must-probe.yaml` | Adapt → `SW-VAGUE-01-vague-start-must-clarify` (#12) |
| `SW-ACCESS-04-unsupported-app.yaml` | Adapt → `SW-ESCALATE-01-unsupported-app` (#10) |

All four existing fixtures use `simulator_rules:` style. They convert to scripted `script:` style by inlining the simulator's branch behavior as fixed user replies (using the most-realistic branch for the primary scenario and adding a `*-decline` or `*-counter` variant for negative paths).

---

## File template (to be authored in Phase 5)

```yaml
id: SW-CONFIRM-01-figma-happy-path
title: Figma access request — Confirm-Submit happy path
topic: HelpIqAgentMultiplierSoftwareRequests
category: straightforward-action-Confirm-Submit
service_strategy_targets: [Acknowledge, Confirm, Submit]

determinism_subset: true        # included in AC #7 N=3 runs

script:
  - user: "I need figma access"
    expected:
      service_strategy: Clarify       # ask for reason (no slot summary yet)
      tools_called: []
  - user: "I need to review design mocks from the brand team for our Monday launch"
    expected:
      service_strategy: Acknowledge   # internal — GATHER on next turn
      tools_called: [HelpIqAgentApplicationAccessDetails]
      tool_inputs:
        HelpIqAgentApplicationAccessDetails:
          inputChatMessage: "Figma"   # ±case-insensitive
  - user: "Editor please"
    expected:
      service_strategy: Confirm
      slot_summary_includes:
        application: Figma
        access_type: Editor
        reason: "design mocks"
      tools_called: []
  - user: "yes go ahead"
    expected:
      service_strategy: Submit
      tools_called: [HelpIqAgentMultiplierSoftwareRequests]
      tool_inputs:
        HelpIqAgentMultiplierSoftwareRequests:
          applicationKey: "Figma"
          accessTypeKey: "Editor"
          reasonForAccess: "*"        # any non-empty value
      no_internal_keys_in_reply: true
      contains_ticket_link: true

rubric_grading:
  source: trace                       # .sfdx/.../traces/<traceId>.json LLMStep raw output
  not_user_facing: true               # planner strips markdown — see HELPEXP-274 HITL
```

---

## What this README does NOT do

- **Does not author the actual YAML files** — that's Phase 5, after Stage 0 structural design HITL approval.
- **Does not commit to the multi-turn driver script** — Phase 5 will decide between (a) a thin Python wrapper around `sf agent preview send`, (b) authoring `AiEvaluationDefinition` records with multi-turn `expectedConversationFlow` (Test Center native, but limited shape), or (c) `sf agent test run` with custom expectation matchers. (a) is the leanest path with least platform commitment.
- **Does not lock the 12 specific scenarios** — the coverage targets (5 buckets × 5 categories × ≥8 apps) are firm; the specific apps per row may shift based on Glean catalog reality discovered in Phase 5.
