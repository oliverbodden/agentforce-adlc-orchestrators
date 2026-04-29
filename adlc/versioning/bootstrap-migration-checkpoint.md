# Bootstrap Migration Checkpoint

## Summary

Created and ran a non-destructive Cursor ADLC bootstrap/status helper:

```text
tools/bootstrap_it_adlc.py
```

Dry-run report:

```text
adlc/versioning/bootstrap-status-2026-04-25.json
```

No installed skills were copied, deleted, or overwritten.

After user approval, ran additive install only:

```text
python3 tools/bootstrap_it_adlc.py --install-additive --write-report adlc/versioning/bootstrap-install-2026-04-25.json
```

The additive install copied only missing consolidated Salesforce skills. It did not delete or overwrite legacy `adlc-*` skills.

## Current Machine State

| Area | Status |
|---|---|
| Salesforce CLI | Pass: `sf --version` works and required command surfaces respond. |
| Salesforce upstream clone | Pass: `/Users/obguzman/agentforce-adlc-salesforce` exists at commit `4fa57e376d7b6f372ba4a765fce475df5924bbfa`. |
| Consolidated Cursor skills | Present: `developing-agentforce`, `testing-agentforce`, `observing-agentforce`. |
| Local wrapper skills | Present: `adlc-drive`, `adlc-execute`, `adlc-ticket`. |
| Legacy standard skills | Present: `adlc-author`, `adlc-discover`, `adlc-scaffold`, `adlc-deploy`, `adlc-feedback`, `adlc-test`, `adlc-run`, `adlc-optimize`. |
| Local overlay docs | Present. |
| Corporate artifact repo | Not cloned/open in this workspace. |

## Completed Additive Action

Copied the consolidated Salesforce upstream skills into Cursor:

```text
/Users/obguzman/agentforce-adlc-salesforce/skills/developing-agentforce
  -> /Users/obguzman/.cursor/skills/developing-agentforce

/Users/obguzman/agentforce-adlc-salesforce/skills/testing-agentforce
  -> /Users/obguzman/.cursor/skills/testing-agentforce

/Users/obguzman/agentforce-adlc-salesforce/skills/observing-agentforce
  -> /Users/obguzman/.cursor/skills/observing-agentforce
```

Do not delete legacy `adlc-*` standard skills yet. Keep them until alias/delegation behavior is verified and a cleanup gate is approved.

## Why Not Run Upstream Installer Directly Yet

Salesforce upstream `tools/install.py` knows about old `adlc-*` skill directories as cleanup targets. Running it directly could remove legacy installed skills before local wrapper compatibility and alias behavior are verified.

The safer path is:

1. Add consolidated skills side-by-side.
2. Run reference checks.
3. Confirm `adlc-drive` / `adlc-execute` still work.
4. Decide whether old `adlc-*` standard skills become aliases, wrappers, archived backups, or are removed.

## Remaining Approval Gate

Pending approval:

- Decide whether old `adlc-*` standard skills become aliases, wrappers, archived backups, or are removed.
- No deletion or cleanup of old `adlc-*` skills is approved yet.
