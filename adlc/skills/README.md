# Skills Directory

This is the single source for all skills installed by the bootstrap script.
Custom skills live alongside vendored upstream skills under one root.

## Layout

```text
adlc/skills/
├── README.md                          # This file
├── adlc-drive/                        # Custom (committed)
├── adlc-execute/                      # Custom (committed)
├── adlc-ticket/                       # Custom (committed)
└── upstream/                          # Vendored from SalesforceAIResearch/agentforce-adlc
    ├── README.md                      # Committed; explains the vendor model
    ├── .gitkeep                       # Committed
    ├── SOURCE.md                      # Gitignored; runtime state
    ├── developing-agentforce/         # Gitignored; populated by bootstrap
    ├── observing-agentforce/          # Gitignored; populated by bootstrap
    └── testing-agentforce/            # Gitignored; populated by bootstrap
```

## Custom vs upstream

| | Custom | Upstream |
|---|---|---|
| **Owned by** | This project | SalesforceAIResearch |
| **Source of truth** | This repo | https://github.com/SalesforceAIResearch/agentforce-adlc |
| **Committed?** | Yes | No (only README + .gitkeep are committed) |
| **Updated how?** | Edit in place, commit | `bootstrap --update-upstream-skills` |

## Install flow

```bash
python3 tools/bootstrap_it_adlc.py --install-additive
```

The bootstrap script:
1. Auto-vendors upstream skills into `upstream/` if missing (clones/pulls
   `~/agentforce-adlc-salesforce/` cache, then copies into `upstream/<skill>/`).
2. Copies all skills (custom + upstream) into `~/.cursor/skills/`.
3. Skips skills already present in `~/.cursor/skills/` (additive only —
   never overwrites or deletes).

See `upstream/README.md` for upstream-specific details.

## Why this layout

The repo's folder structure tells the story of the complete skill landscape.
Custom skills are under git control. Upstream skills are runtime-fetched
into a known location so that bootstrap, install, and discovery all use a
single source.
