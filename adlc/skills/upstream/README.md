# Upstream Salesforce Skills

This folder vendors the upstream Salesforce ADLC skills from
[`SalesforceAIResearch/agentforce-adlc`](https://github.com/SalesforceAIResearch/agentforce-adlc)
into this repo's folder structure for a single-source install path.

## What is and isn't tracked

| Path | Tracked in git | Purpose |
|---|---|---|
| `README.md` | yes | This file. Explains the vendor model. |
| `.gitkeep` | yes | Ensures the folder always exists in fresh clones. |
| `SOURCE.md` | no (gitignored) | Runtime metadata written by bootstrap (commit hash, fetch date). Local-only. |
| `developing-agentforce/` | no (gitignored) | Vendored skill content. Populated by bootstrap. |
| `observing-agentforce/` | no (gitignored) | Vendored skill content. Populated by bootstrap. |
| `testing-agentforce/` | no (gitignored) | Vendored skill content. Populated by bootstrap. |

## Why this design

We want the repo's folder structure to reflect the full skill landscape
(custom + upstream side-by-side under `adlc/skills/`) **without** committing
copies of upstream content. This avoids fork-drift while keeping setup
self-contained.

Trade-off: a fresh clone has empty subfolders here until bootstrap runs.
That's intentional — bootstrap is required to make the workspace usable.

## How to populate this folder

```bash
python3 tools/bootstrap_it_adlc.py --update-upstream-skills
```

This will:
1. Clone or pull the upstream repo into `~/agentforce-adlc-salesforce/` (the cache).
2. Copy the three skills from the cache into this folder.
3. Write `SOURCE.md` with the vendored commit hash and fetch timestamp.

You can also run `--install-additive`, which auto-vendors if any upstream
skill folder is missing here, then installs everything to `~/.cursor/skills/`.

## How to upgrade upstream skills

When SalesforceAIResearch ships new versions:

```bash
python3 tools/bootstrap_it_adlc.py --update-upstream-skills
python3 tools/bootstrap_it_adlc.py --install-additive
```

Review what changed by comparing `SOURCE.md`'s previous commit hash to the
new one against the upstream repo's git log.

## What lives where

- **Source repo:** https://github.com/SalesforceAIResearch/agentforce-adlc
- **Cache (full clone):** `~/agentforce-adlc-salesforce/` — the bootstrap
  fetches into here, then copies relevant skill folders into this directory.
- **This folder:** the vendored skill subfolders (gitignored content) that
  bootstrap installs from.
- **Installed:** `~/.cursor/skills/<skill>/` — what Cursor actually loads.
