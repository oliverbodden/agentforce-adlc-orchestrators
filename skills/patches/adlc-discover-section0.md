### 0. Agent/Topic Resolution (UI-built agents)

When no `.agent` file exists (agent was built through Agent Builder UI), resolve agent and topic metadata directly from the org via SOQL. This is used by `adlc-drive` step 1c.

```bash
# Find agent by name
sf data query -q "SELECT Id, DeveloperName, MasterLabel FROM BotDefinition WHERE MasterLabel LIKE '%<name>%'" -o <org> --json

# Find planner (for STDM queries)
sf data query -q "SELECT Id, MasterLabel, DeveloperName FROM GenAiPlannerDefinition WHERE MasterLabel LIKE '%<name>%'" -o <org> --json

# Find topics for an agent (use key prefix from GenAiPluginDefinition IDs)
sf data query -q "SELECT Id, DeveloperName, Description FROM GenAiPluginDefinition WHERE DeveloperName LIKE '%<topic_name>%'" -o <org> --json

# Find instruction records for a topic
sf data query -q "SELECT Id, DeveloperName, Description FROM GenAiPluginInstructionDef WHERE GenAiPluginDefinitionId = '<plugin_def_id>'" -o <org> --json
```

**Output:** Return a resolution object with:

| Field | Source |
|---|---|
| `agent_api_name` | `BotDefinition.DeveloperName` |
| `agent_label` | `BotDefinition.MasterLabel` |
| `bot_definition_id` | `BotDefinition.Id` |
| `planner_id` | `GenAiPlannerDefinition.Id` |
| `topics` | List of `{developer_name, plugin_definition_id, description}` from `GenAiPluginDefinition` |
| `instruction_ids` | List of `GenAiPluginInstructionDef.Id` per topic |
| `has_authoring_bundle` | `true` if `.agent` file found, `false` if UI-built |

**When called by drive:** Drive passes agent name + topic name. Discover returns the IDs needed for optimize and test to operate.