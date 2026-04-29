# Project Map

## Current ADLC Model

This map is a current orientation aid. The approved model is:

- Salesforce upstream baseline: `https://github.com/SalesforceAIResearch/agentforce-adlc`
- Consolidated standard skills: `developing-agentforce`, `testing-agentforce`, `observing-agentforce`
- Local wrapper/process skills: `adlc-drive`, `adlc-execute`, `adlc-ticket`
- Local overlay docs:
  - `adlc/playbooks/agentforce-architecture-playbook.md`
  - `adlc/docs/core-process-overlay.md`
  - `adlc/docs/acceptance-eval-hitl-governance.md`
  - `adlc/docs/artifact-repo-workflow.md`
  - `adlc/docs/developer-onboarding.md`

Do not modify Salesforce standard skill content directly. Local behavior belongs in wrappers, overlay docs, project playbooks, bootstrap/install steps, or approved additive patches.

## Install Order

Install in this order:

1. **Salesforce prerequisites** — Install Salesforce CLI, verify required `sf` command surfaces, and authenticate required org aliases.
2. **Salesforce upstream ADLC skills** — Install or verify `developing-agentforce`, `testing-agentforce`, and `observing-agentforce` from `https://github.com/SalesforceAIResearch/agentforce-adlc`.
3. **Project/local overlay** — Install or verify `adlc-drive`, `adlc-execute`, `adlc-ticket`, overlay docs, playbooks, bootstrap/status tooling, and artifact repo routing from this repo.

The local overlay repo should not vendor copied Salesforce upstream skill directories. `tools/bootstrap_it_adlc.py` verifies the expected state and can copy missing consolidated Salesforce skills from a local upstream clone into the user's skill directory, but the repo source remains additive.

Command sketch for Cursor:

```text
# 1. Salesforce prerequisites
node --version
npm --version
npm install --global @salesforce/cli
sf --version
sf agent --help
sf org list

# 2. Salesforce upstream ADLC skills
git clone https://github.com/SalesforceAIResearch/agentforce-adlc.git ~/agentforce-adlc-salesforce
cd ~/agentforce-adlc-salesforce
python3 tools/install.py --target cursor

# Alternative one-command upstream install:
curl -sSL https://raw.githubusercontent.com/SalesforceAIResearch/agentforce-adlc/main/tools/install.sh | bash

# 3. Project/local overlay
git clone https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO.git ~/YOUR_ADLC_ARTIFACT_REPO
cd ~/YOUR_ADLC_ARTIFACT_REPO
python3 tools/bootstrap_it_adlc.py --dry-run
python3 tools/bootstrap_it_adlc.py --status
python3 tools/bootstrap_it_adlc.py --install-additive
```

## Legend

| Symbol | Meaning |
|---|---|
| 🔵 | **Salesforce upstream standard** — comes from Salesforce ADLC upstream. Do not modify directly. |
| 🟢 | **Custom (new)** — created by us. Fully owned. |
| 🟡 | **From repo + our additions** — original content untouched, we added new sections. |
| ⚪ | **Salesforce project scaffolding** — standard SFDX structure, auto-generated. |

---

## Skills (~/.cursor/skills/)

These are global — available across all projects.

```
~/.cursor/skills/
├── 🔵 developing-agentforce/SKILL.md # Author, discover, scaffold, deploy, publish, feedback
├── 🔵 testing-agentforce/SKILL.md    # Preview, Testing Center, action execution
├── 🔵 observing-agentforce/SKILL.md  # Trace/session analysis, reproduce, optimize
├── 🟢 adlc-drive/SKILL.md           # Goal-driven orchestrator (custom wrapper)
├── 🟢 adlc-execute/SKILL.md         # Plan/execute/evaluate orchestrator (custom wrapper)
├── 🟢 adlc-ticket/SKILL.md          # Ticket readiness and ticket authoring helper
├── 🔵 agentforce-testing-analysis/   # Analyze Testing Center CSV exports
└── historical adlc-* standard skills may still be installed for compatibility;
    do not treat them as current orchestration entry points.
```

## Project (agentforce-project/)

```
agentforce-project/
│
├── 🟢 adlc/                                  # Eval framework (ALL custom)
│   ├── 🟢 playbooks/prompt-engineering-playbook.md       # Living doc — principles, rule levels, patterns
│   ├── 🟢 playbooks/agentforce-architecture-playbook.md  # Root-cause routing and dependency mapping
│   ├── 🟢 docs/core-process-overlay.md         # Local ADLC exceptions, handoff state, acceptance state
│   ├── 🟢 docs/drive-architecture.md           # Drive/execute delegation map + sub-skill requirements
│   ├── 🟢 docs/PROJECT-MAP.md                  # This map
│   ├── 🟢 docs/PROJECT-MAP.html                # Interactive companion map
│   ├── 🟢 docs/artifact-repo-workflow.md       # Shared artifact repo routing and closeout package
│   ├── 🟢 docs/developer-onboarding.md         # Bootstrap/status and workstation readiness
│   ├── 🟢 ticket-guides/ticket-template.md     # Generic ticket template
│   ├── 🟢 ticket-guides/ticket-template-generalfaq.md # Pre-filled for GeneralFAQ
│   │
│   ├── 🟢 scripts/                             # Shared utilities
│   │   └── generate_report.py                   # Regression report: scorecard, strategy, formatting,
│   │                                            #   opening behavior, length buckets, multi-turn,
│   │                                            #   consistency, tool-calling/quality sections,
│   │                                            #   and response comparison appendix.
│   │                                            #   Outputs HTML + optional JSON (--json-output).
│   │
│   └── 🟢 agents/                               # Agent/org scoped ADLC artifacts
│       └── <agent-dev-name>__<org-alias>/
│           ├── meta.json
│           ├── baselines/
│           │   └── <topic>/
│           │       └── utterances.txt
│           └── tickets/
│               └── <ticket-key-or-NOTICKET-NN-short-description>/
│                   ├── goal.md
│                   ├── hitl.jsonl
│                   ├── discovery.json
│                   ├── config.json
│                   ├── status.md
│                   ├── dependency-map.md
│                   ├── prompt-mental-model.md
│                   ├── originals/
│                   ├── specs/
│                   └── attempts/
│
├── ⚪ force-app/                               # Salesforce DX project
│   └── main/default/
│       ├── aiAuthoringBundles/                  # Agent Script authoring bundle source
│       └── genAiPlannerBundles/                 # Retrieved/generated planner metadata
│
├── 🟢 tools/
│   └── bootstrap_it_adlc.py                     # Conservative status/dry-run/additive install helper
│
├── ⚪ sfdx-project.json                        # SFDX config
├── ⚪ package.json                              # Node config
├── ⚪ .forceignore / .prettierrc / etc          # Standard tooling config
└── ⚪ README.md                                 # Project readme
```

## MCP Servers (~/.cursor/mcp.json)

```
🟢 user-atlassian                    # Official Atlassian MCP (OAuth SSO, read-only)
    └── JIRA access: getJiraIssue, searchJiraIssuesUsingJql, etc.
    └── ⛔ Write tools blocked by skill policy (not by MCP config)
```

## What's Connected to What

```
JIRA ticket
    │
    ▼
adlc-drive (orchestrator)
    ├── reads: playbooks/agentforce-architecture-playbook.md
    ├── reads: docs/core-process-overlay.md
    ├── reads: docs/acceptance-eval-hitl-governance.md
    ├── reads: playbooks/prompt-engineering-playbook.md
    ├── owns: Phases 1-3 only, then stops at the Phase 3 approval handoff
    ├── calls: developing-agentforce → resolve metadata, author/scaffold/deploy as needed
    ├── calls: observing-agentforce  → trace/optimize/read-write instruction workflows
    ├── calls: testing-agentforce    → preview, Testing Center, export/action testing
    ├── calls: generate_report.py → regression comparison + HTML
    ├── creates: discovery.json + config.json as durable handoff state
    ├── Phase 3c: builds fresh baseline/test specs from canonical utterances
    ├── Phase 3d: analyzes baseline and proposes acceptance criteria
    ├── hands off to: adlc-execute after Phase 3 approval for Phases 4-7
    └── writes to: adlc/agents/{agent}__{org}/tickets/{ticket-key}/
```
