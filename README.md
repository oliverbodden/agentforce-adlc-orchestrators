# Agentforce ADLC Overlay

This workspace contains the Project/local overlay for Agentforce ADLC work: wrapper skills, local process docs, playbooks, bootstrap/status tooling, ticket guides, and artifact conventions.

Salesforce upstream ADLC standard skills are the baseline and are installed from `https://github.com/SalesforceAIResearch/agentforce-adlc`. Do not vendor copied Salesforce upstream skill directories into this repo.

## Install Order

Install in this order:

1. Salesforce prerequisites: Salesforce CLI, required `sf` command surfaces, and org auth.
2. Salesforce upstream ADLC baseline: `developing-agentforce`, `testing-agentforce`, and `observing-agentforce`.
3. Project/local overlay: `adlc-drive`, `adlc-execute`, `adlc-ticket`, overlay docs, playbooks, and artifact workflow.

See `adlc/docs/developer-onboarding.md` for the full setup flow.

## Start Here

- `adlc/docs/developer-onboarding.md`
- `adlc/docs/PROJECT-MAP.md`
- `adlc/docs/drive-architecture.md`
- `adlc/docs/core-process-overlay.md`
- `adlc/docs/acceptance-eval-hitl-governance.md`
- `adlc/docs/artifact-repo-workflow.md`

## Useful Commands

Install Salesforce CLI if needed:

```text
node --version
npm --version
npm install --global @salesforce/cli
sf --version
```

Install Salesforce upstream skills for Cursor:

```text
# Option A: one-command upstream install
curl -sSL https://raw.githubusercontent.com/SalesforceAIResearch/agentforce-adlc/main/tools/install.sh | bash

# Option B: local upstream clone
git clone https://github.com/SalesforceAIResearch/agentforce-adlc.git ~/agentforce-adlc-salesforce
cd ~/agentforce-adlc-salesforce
python3 tools/install.py --target cursor
```

Then verify/apply the Project/local overlay:

```text
cd ~/YOUR_ADLC_ARTIFACT_REPO
python3 tools/bootstrap_it_adlc.py --dry-run
python3 tools/bootstrap_it_adlc.py --status
python3 tools/bootstrap_it_adlc.py --install-additive
```

The bootstrap helper is conservative. It verifies prerequisites and installs missing consolidated Salesforce skills only when the upstream clone is present locally. It must not overwrite local wrapper skills, delete legacy skills, or copy Salesforce upstream skill source into this repo.

## Repository Boundaries

- Keep local overlay source, docs, ticket guides, and artifact conventions here.
- Keep production Salesforce agent source such as `force-app/` out of this repo unless governance explicitly changes.
- Keep generated local install evidence such as `adlc/versioning/bootstrap-*.json` out of commits.
- Keep installed Salesforce upstream skill directories out of this repo.
