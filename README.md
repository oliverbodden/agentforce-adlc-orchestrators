# Agentforce ADLC Custom

Goal-driven Agentforce agent optimization with JIRA integration, eval framework, and prompt engineering playbook.

Built on top of [agentforce-adlc](https://github.com/almandsky/agentforce-adlc) by almandsky.

## What this adds

| Component | What it does |
|---|---|
| **adlc-drive** | Goal-driven orchestrator — takes a JIRA ticket or goal, discovers baseline, plans changes, executes iteratively, evaluates, presents results |
| **adlc-ticket** | Create or evaluate tickets for drive — standalone or called by drive to assess readiness |
| **Eval framework** | Versioned scoring, baselines, ticket-scoped attempts, regression comparison |
| **Playbook** | Prompt engineering principles with rule levels (HARD/STRONG/SOFT) and tie-breaker guidance |
| **Patches** | Additions to base skills: SOQL resolution (discover), Tooling API (optimize), CSV export (test) |
| **JIRA integration** | Read-only access via official Atlassian MCP server (OAuth SSO) |

## Install

```bash
git clone https://github.com/YOUR_ORG/agentforce-adlc-custom.git
cd agentforce-adlc-custom
./install.sh
```

The installer:
1. Installs [agentforce-adlc](https://github.com/almandsky/agentforce-adlc) base skills (if not already installed)
2. Installs custom skills (adlc-drive, adlc-ticket)
3. Applies patches to base skills (additive only — original content untouched)
4. Sets up the eval framework in your project
5. Prompts for Atlassian MCP setup

## Prerequisites

- **Cursor** or **Claude Code** installed
- **Salesforce CLI** (`sf`) v2.x
- **Python 3.9+**
- **Node.js** (for Atlassian MCP server)
- **Salesforce org** with Agentforce enabled

## Usage

### Evaluate a ticket
```
adlc-ticket ESCHAT-1234
```

### Execute a ticket
```
adlc-drive ESCHAT-1234
```

### Write a new ticket
```
adlc-ticket "I need to update the tone for our FAQ agent"
```

## Documentation

Open `PROJECT-MAP.html` in your browser for an interactive guide covering:
- **Repo Structure** — what's from the base repo vs custom
- **How Drive Works** — step-by-step simulation with skill delegation
- **Connections** — what calls what

## Repo Structure

```
skills/
├── adlc-drive/SKILL.md           # Goal-driven orchestrator
├── adlc-ticket/SKILL.md          # Ticket creation/evaluation
└── patches/                      # Additions to base repo skills
    ├── adlc-discover-section0.md  # SOQL-based agent/topic resolution
    ├── adlc-optimize-section3ui.md # Tooling API for UI-built agents
    └── adlc-test-csv-export.md    # CSV export + contextVariables format

evals/
├── prompt-engineering-playbook.md # Principles + rule levels
├── drive-architecture.md          # Delegation map
├── eval-config/                   # Versioned scoring scripts + utterances
├── scripts/                       # Shared utilities (generate_report.py)
└── ticket-guides/                 # Ticket authoring guide + templates + examples
```

## Relationship to agentforce-adlc

This repo extends [agentforce-adlc](https://github.com/almandsky/agentforce-adlc) without forking it:

- **Base skills** are installed from the original repo (unchanged)
- **Patches** add new sections to 3 base skills (additive only — original content untouched)
- **Custom skills** (drive, ticket) are new and don't exist in the base repo
- **Eval framework** is entirely custom

When the base repo updates, re-run `./install.sh` — patches will re-apply cleanly since they only append, never modify.

## License

MIT
