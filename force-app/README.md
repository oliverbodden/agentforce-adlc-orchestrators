# force-app/ — Agentforce-Focused SFDX Scaffold

This is an empty Salesforce DX source directory scoped to **Agentforce work**.
It ships with empty buckets for Agentforce metadata types only.

## Buckets

| Bucket | Purpose |
|---|---|
| `aiAuthoringBundles/` | Agent Script `.agent` source files + `bundle-meta.xml` |
| `aiEvaluationDefinitions/` | `AiEvaluationDefinition` test specs (generated from YAML via `sf agent test create`) |
| `bots/` | Legacy / runtime agent metadata (`*.bot-meta.xml` + versioned `vN.botVersion-meta.xml`) |
| `genAiPlannerBundles/` | Agent planner bundles (paired with bots, versioned) |
| `genAiPromptTemplates/` | `*.genAiPromptTemplate-meta.xml` files used by agents |
| `classes/` | Apex backing logic for agent actions (invocable Apex) |
| `flows/` | Flow backing logic for agent actions |

## Populating it for your agent

**For an existing agent in your Salesforce org:**

```bash
sf project retrieve start \
  --metadata Bot:<YourAgentApiName>,GenAiPlannerBundle:<YourAgentApiName>_v<N>
```

This pulls the bot, planner bundle, and any associated metadata into the
correct buckets above.

**For a brand-new agent (using Agent Script authoring):**

```bash
sf agent generate authoring-bundle \
  --name "<Display Label>" --api-name <YourAgentApiName>
```

This creates `aiAuthoringBundles/<YourAgentApiName>/<YourAgentApiName>.agent`
and the corresponding `bundle-meta.xml`. Use the `developing-agentforce`
skill (installed by `tools/bootstrap_it_adlc.py`) to write the Agent Script
content.

**For test specs (eval definitions):**

```bash
sf agent test create --spec specs/<your-spec>.yaml --api-name <YourEvalName>
```

Generated XML lands in `aiEvaluationDefinitions/`. Source YAML should live
under the standard `adlc/agents/<agent>__<org>/tickets/<ticket>/specs/` path.

## What does NOT belong here

- ❌ **Specific agent metadata** (`.agent` files, bot XMLs, planner bundles,
  eval XMLs, prompt templates for any real agent) — those live in your
  team's **production agent repo**, not in this default repo.
- ❌ **Generic Salesforce metadata types not used by Agentforce** (LWC, Aura,
  layouts, tabs, applications, contentassets, flexipages, objects,
  permissionsets, staticresources, triggers) — if you need them, add the
  directory yourself or run `sf project generate` to recreate the full SFDX
  scaffold.

## Why empty buckets with `.gitkeep`?

The Agentforce skills (`developing-agentforce`, `testing-agentforce`,
`observing-agentforce`) write to these paths. Pre-creating them avoids
"directory not found" errors on first use.

The `.gitkeep` files are the only way to commit empty directories to git;
they have no other purpose and can be ignored.

## Related conventions

- `adlc/docs/developer-onboarding.md` — first-time setup walkthrough
