# Initial Skill Regression / Reference Audit

## Scope

Initial Phase 0 audit across upstream Salesforce skills, installed Cursor skills, legacy local custom repo, and current workspace docs. This is a reference audit only; no skill content was modified.

## Checklist

| Check | Status | Evidence |
|---|---|---|
| Skill command names and aliases checked | Complete | Salesforce README maps old `adlc-*` names to `developing-agentforce`, `testing-agentforce`, and `observing-agentforce`. |
| Cross-skill delegation references checked | Partial | Legacy `adlc-drive`/`adlc-execute` delegate to old individual `adlc-*` skills. Needs remapping to consolidated skills. |
| Phase numbers and ownership checked | Partial | Legacy drive/execute use phases 1-7. Salesforce upstream uses task domains and mode-specific phases. Needs target mapping. |
| Installer/bootstrap commands checked | Partial | Salesforce upstream has `tools/install.py` and `tools/install.sh`; legacy repo has custom `install.sh`. Need corporate bootstrap design. |
| Salesforce upstream repo URL and commit checked | Complete | `https://github.com/SalesforceAIResearch/agentforce-adlc`, commit `4fa57e376d7b6f372ba4a765fce475df5924bbfa`, version `0.1.0`. |
| Corporate artifact repo URL checked | Partial | URL recorded as `https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO`; repo not cloned locally during Phase 0. |
| Docs/project map/ticket guides checked | Partial | Current workspace docs match legacy repo; they still describe older custom repo/upstream model and require refresh after target structure approval. |
| Examples/phase outputs checked | Partial | `adlc-drive/examples/phase-outputs.md` differs between legacy repo and installed skills. Needs review during migration. |
| Patch markers and overlay manifest checked | Partial | Installed patch markers found for discover/optimize/test. Draft overlay manifest created. |
| No local addition directly overwrites standard skill content without approval | In force for Phase 0 | No standard Salesforce skill files modified. |

## Stale Reference Risks

- Legacy `adlc-drive` and `adlc-execute` reference old individual skills as first-class delegates.
- Legacy project docs reference the older upstream `almandsky/agentforce-adlc`.
- Installed skills use old `adlc-*` directories, while Salesforce upstream uses consolidated `*-agentforce` directories.
- The old `adlc-optimize` Tooling API guidance may conflict with upstream guidance around `.agent` as source of truth for pro-code agents.
- Installer docs need to reflect Salesforce upstream first, project overlay second.

## Required Follow-Up

1. Approve target structure.
2. Map legacy phase/delegation references to consolidated Salesforce skills.
3. Decide how wrappers/overlays are installed for Cursor.
4. Re-run this audit after overlay and documentation updates.
