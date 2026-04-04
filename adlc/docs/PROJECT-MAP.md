# Project Map

## Legend

| Symbol | Meaning |
|---|---|
| 🔵 | **From repo** — came from [agentforce-adlc](https://github.com/almandsky/agentforce-adlc). Do not modify unless necessary. |
| 🟢 | **Custom (new)** — created by us. Fully owned. |
| 🟡 | **From repo + our additions** — original content untouched, we added new sections. |
| ⚪ | **Salesforce project scaffolding** — standard SFDX structure, auto-generated. |

---

## Skills (~/.cursor/skills/)

These are global — available across all projects.

```
~/.cursor/skills/
├── 🔵 adlc-author/SKILL.md          # Generate .agent files from requirements
├── 🔵 adlc-deploy/SKILL.md          # Deploy, publish, activate agent bundles
├── 🟡 adlc-discover/SKILL.md        # Check targets in org + [ADDED: Section 0 SOQL resolution]
├── 🟢 adlc-drive/SKILL.md           # Goal-driven orchestrator (NEW — created by us)
├── 🔵 adlc-feedback/SKILL.md        # Collect feedback on ADLC skills
├── 🟡 adlc-optimize/SKILL.md        # Analyze + improve agents + [ADDED: Section 3.UI Tooling API]
├── 🔵 adlc-run/SKILL.md             # Execute individual actions via REST
├── 🔵 adlc-scaffold/SKILL.md        # Generate Flow/Apex stubs
├── 🟡 adlc-test/SKILL.md            # Test agents + [ADDED: CSV export, HTML unescape, contextVars format]
└── 🔵 agentforce-testing-analysis/   # Analyze Testing Center CSV exports
```

## Project (agentforce-project/)

```
agentforce-project/
│
├── 🟢 adlc/                                  # Eval framework (ALL custom)
│   ├── 🟢 prompt-engineering-playbook.md       # Living doc — principles, rule levels, patterns
│   ├── 🟢 drive-architecture.md                # Drive delegation map + sub-skill requirements
│   ├── 🟢 ticket-template.md                   # Generic ticket template
│   ├── 🟢 ticket-template-generalfaq.md        # Pre-filled for GeneralFAQ
│   │
│   ├── 🟢 eval-config/                         # Versioned eval methodology
│   │   ├── CHANGELOG.md
│   │   ├── scoring/
│   │   │   ├── current/                         # Active scoring scripts
│   │   │   │   ├── run_regression.py            # Metrics comparison (Invoice-era, topic-agnostic now)
│   │   │   │   ├── analyze_response.py          # Response quality checker
│   │   │   │   └── version.json                 # s1
│   │   │   └── versions/s1/                     # Archived
│   │   └── utterances/
│   │       ├── current/
│   │       │   ├── all-topics-102.yaml          # Canonical utterance set
│   │       │   └── version.json                 # u1
│   │       └── versions/u1/                     # Archived
│   │
│   ├── 🟢 scripts/                             # Shared utilities
│   │   ├── generate_report.py                   # Topic-agnostic regression + HTML report
│   │   └── _archived/                           # Replaced by sub-skills
│   │       ├── update_instruction.py            # → now in adlc-optimize
│   │       └── run_eval.py                      # → now in adlc-test
│   │
│   └── 🟢 indeed-service-agent/                # Agent-level eval data
│       ├── baselines/
│       │   └── v21/                             # Production baseline
│       │       ├── instruction-invoice.txt      # 7,422 words (original)
│       │       ├── raw-outputs.csv              # 850 rows, 8 runs per utterance
│       │       ├── eval-report.html
│       │       └── metadata.json
│       └── tickets/
│           └── PROJ-345-compact-invoice-instructions/
│               ├── goal.md
│               ├── config.json
│               ├── CHANGELOG.md
│               ├── STATUS.md
│               ├── specs/
│               │   ├── smoke-5.yaml
│               │   └── full-102.yaml
│               └── attempts/
│                   ├── 01-v22-full-rewrite/     # Failed
│                   ├── 02-v22c-surgical-28pct/  # Full eval done
│                   ├── 03-v22d-surgical-37pct/  # 20-test only
│                   ├── 04-v22c-fixed-explain/   # ← DEPLOYED to devesa3
│                   ├── 05-v22c-fix-nomatch/     # Failed
│                   ├── 06-v22c-fix-nomatch-v2/  # Failed (data artifact)
│                   └── 07-v22c-restore-philosophy/ # Failed (data artifact)
│
├── ⚪ force-app/                               # Salesforce DX project
│   └── main/default/
│       ├── aiEvaluationDefinitions/             # Testing Center specs (deployed to org)
│       └── bots/                                # Agent metadata (retrieved from org)
│
├── 🟢 scripts/                                 # Ad-hoc analysis scripts
│   └── compare_strategies.py                    # Strategy shift analysis (PROJ-345)
│
├── 🟢 report/                                  # Pre-existing reports
│   ├── deviation-analysis-how-do-i-post-a-job.md
│   └── report-ESA-FAQ-SingleTurn-v28-*.md/html
│
├── 🟢 tickets/                                 # Non-eval ticket work
│   └── ESCHAT-946-url-redaction/
│
├── 🟢 .skills -> ~/.cursor/skills              # Symlink for browsing skills in IDE
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
    ├── reads: prompt-engineering-playbook.md
    ├── calls: adlc-discover    → resolve agent/topic IDs
    ├── calls: adlc-optimize    → read/write instructions (Tooling API or .agent)
    ├── calls: adlc-test        → run Testing Center, export CSV
    ├── calls: generate_report.py → regression comparison + HTML
    └── writes to: adlc/{agent}/tickets/{ticket-key}/
```
