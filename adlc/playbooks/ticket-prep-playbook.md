# Ticket Prep Playbook

**Scope:** When and how to gather evidence **before** drafting a ticket via `adlc-ticket`. Keeps ticket-writing grounded in data instead of intuition.

**Audience:** Anyone running `adlc-ticket` on a complex prompt-facing change. Also read by the `adlc-ticket` skill at session start when this file exists in the project.

**What this playbook is NOT:** It is not a list of "lessons learned" from past tickets. Substantive findings live in agent registries and process docs (`AGENT_VERSION_REGISTRY.md`, `adlc/docs/core-process-overlay.md`, `adlc/playbooks/prompt-engineering-playbook.md`). This playbook covers process only — how to prepare to write a ticket.

---

## 1. When to do a pre-ticket evidence brief

A pre-ticket brief is **opt-in**. Most tickets don't need one. Use it only when **all** of the following apply:

- The work is **prompt-facing** on an existing agent topic or sub-agent.
- **Prior eval data exists** and can be filtered or re-analyzed for this topic — running new evals from scratch isn't required.
- **Scope is unclear** enough that drafting requirements directly would be guessing. Multiple plausible scope splits, unclear regression risk, or prior iterations on related topics that may have introduced indirect effects.
- The user has **discovery material** to merge in (transcripts of design conversations, customer reports, prior runs) that the brief should anchor against.

**Do NOT use a pre-ticket brief for:**

- Simple prompt tweaks with clear scope (one rule, one topic, one acceptance criterion).
- Bug fixes with a known cause already identified.
- New agent authoring — the ticket itself drives discovery via `adlc-drive` Phase 3.
- Tickets where requirements are already concrete (e.g., "add this exact phrase", "remove this rule").
- Investigations where the unknown is "what's wrong?" — that's a SPIKE, not a prep brief.

When in doubt, skip the brief and let `adlc-ticket` Mode 1 surface gaps via its 5-question readiness check. The brief exists to prevent obvious data-gathering work from happening **inside** ticket drafting; it doesn't replace `adlc-ticket`'s normal scope and readiness assessment.

---

## 2. What goes in the brief

The brief is **evidence-only**. It records what is known about the current state and surfaces open questions. It does not propose scope, hypotheses, or solutions — those are `adlc-ticket`'s job.

### Required sections

| Section | Content |
|---|---|
| **TL;DR** | Three to six bullets capturing the most decision-relevant findings. Numbered facts, not opinions. |
| **What it does today** | File paths, prompt structure (verbatim outline of major sections), wired actions, dependencies. Anchor links to source files with line numbers. |
| **How it performs today** | Numerical evidence from prior evals filtered to this topic. Per-metric pass rates per version. Action sequence distributions. Routing accuracy. |
| **Concrete failure samples** | Verbatim outputs from prior evals showing specific failures, with the utterance that produced them. Three to five samples is plenty. |
| **Eval-coverage gaps** | What is and isn't tested in the current eval master. Apps/intents/actions that have zero coverage. Sources and counts. |
| **Carry-overs from prior tickets** | Reusable assets (scripts, templates, registries) and operational lessons that apply. Not exhaustive — point at canonical references. |
| **What discovery should answer** | Open questions the discovery transcript or conversation should resolve before the ticket can be drafted. |

### Forbidden in the brief

These belong in the ticket itself (Mode 1 output) or in `adlc-drive` Phase 2/3 — not here:

- **Hypotheses** about what the fix should be.
- **Scope candidates** or split recommendations.
- **Risk flags** or devil's-advocate sections about choices not yet made.
- **Acceptance criteria** drafts.
- **Ticket sections** like "Context", "Requirements" — the brief is not a ticket.

If the brief starts containing any of these, it has slipped from "evidence" to "opinion" and should be split.

### One-file rule

The brief is **a single markdown file**. Multiple files (drafts, latest, approved) caused real friction in prior iterations and should be avoided. If the brief grows large, prune it before splitting it.

---

## 3. Where the brief lives

### Path convention (Indeed project)

```text
adlc/agents/{agent-dev-name}__{org-alias}/{topic-or-subagent}-current-state.md
```

Example:
```text
adlc/agents/HelpIQ_AgentScript__aicommon/multiplier-current-state.md
```

This is **flat by design** — alongside `AGENT_VERSION_REGISTRY.md` and `meta.json`, not inside a sub-folder. Reasons:
- The brief is short-lived; it disappears once a ticket exists.
- Pre-ticket prep is not a versioned artifact; it doesn't need its own folder structure.
- Inventing a new directory layer (`_drafts/`, `pre-tickets/`, etc.) creates a convention that lives forever even when the brief moves on.

### Migration once a ticket key exists

When a ticket is created and `adlc-drive` Phase 3a builds the canonical ticket folder, the brief migrates:

```text
adlc/agents/{agent-dev-name}__{org-alias}/{topic}-current-state.md
  →
adlc/agents/{agent-dev-name}__{org-alias}/tickets/{KEY}-{short-description}/discovery-context.md
```

The brief's content seeds `discovery-context.md` (the canonical Phase 3b artifact). Any open questions answered during Phase 1 / Phase 2 of `adlc-drive` get folded in; new sections (Prompt Mental Model, Dependency Map) are added per the `adlc-drive` Phase 3b spec.

The original `{topic}-current-state.md` should be deleted at that point. Don't leave both files around — that recreates the multi-file confusion the brief is meant to avoid.

### What the brief becomes in the ticket

The brief is **input** to `adlc-ticket`'s Mode 1. When `adlc-ticket` runs, it consumes:

- The brief (evidence + open questions).
- The user's discovery transcript or conversation.
- The user's stated goal.

…and produces the ticket with the standard sections (`Context`, `Requirements`, `Acceptance Criteria`, `Agent & Topic`, `Baseline`, `Examples`). The brief's TL;DR and concrete failure samples typically map to the ticket's `Context` and `Examples` sections; the open questions get resolved during Mode 1 and disappear.

---

## 4. Worked example

The first brief produced under this playbook:

```text
adlc/agents/HelpIQ_AgentScript__aicommon/multiplier-current-state.md
```

It was authored before the JIRA ticket for the `HelpIqAgentMultiplierSoftwareRequests` sub-agent existed, using eval data from HELPEXP-274's 999-case run filtered to the 32 multiplier-mapped utterances. It demonstrates:

- TL;DR with the most decision-relevant findings (regression on the modern stack, welcome-message fallback, eval-coverage gap).
- Verbatim prompt outline with file/line anchors.
- Per-metric pass rates per version.
- Action sequence distribution.
- Three concrete failure samples with verbatim outputs.
- Coverage gaps with counts.
- Carry-overs pointing at HELPEXP-274 assets.
- Open questions for discovery — no hypotheses or scope candidates.

When the JIRA ticket for that work exists, this file will migrate into `tickets/{KEY}-…/discovery-context.md` and the original will be deleted.

---

## 5. When to update this playbook

Update this file when:

- The path convention in Section 3 changes (e.g., agent folder structure changes).
- A new "forbidden in the brief" pattern is discovered through experience.
- The migration step in Section 3 changes because `adlc-drive` Phase 3a changes.

**Do NOT update this file with:**

- Substantive findings from individual tickets (those go in agent registries and per-ticket goal/discovery docs).
- Lessons about prompt engineering (those go in `adlc/playbooks/prompt-engineering-playbook.md`).
- Operational rules about deploying/publishing/testing (those go in `adlc/docs/core-process-overlay.md`).

This playbook is process-only and should stay short.
