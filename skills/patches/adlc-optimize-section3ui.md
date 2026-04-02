### 3.UI: Tooling API Path (UI-built agents)

When the agent has no authoring bundle (built through Agent Builder UI), edit topic instructions directly via the Salesforce Tooling API.

**Read current instruction:**
```bash
sf data query -q "SELECT Id, DeveloperName, Description FROM GenAiPluginInstructionDef WHERE GenAiPluginDefinitionId = '<plugin_def_id>'" -o <org> --json
```
The `Description` field contains the full instruction text. A topic may have multiple instruction records (e.g., main instruction + voice/tone).

**Backup before editing:**
Back up the current instruction first (save Description field to a file), then deploy. Alternatively, save manually:
```bash
# Manual backup
sf data query -q "SELECT Description FROM GenAiPluginInstructionDef WHERE Id = '<id>'" -o <org> --json > backup.json
```

**Deploy updated instruction via Tooling API:**
```bash
TOKEN=$(sf org display -o <org> --json | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['accessToken'])")
INSTANCE=$(sf org display -o <org> --json | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['instanceUrl'])")
curl -s -X PATCH "$INSTANCE/services/data/v63.0/tooling/sobjects/GenAiPluginInstructionDef/<id>" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "$(python3 -c "import json; print(json.dumps({'Description': open('<file>').read()}))")"
# HTTP 204 = success
```

**Rollback:** Deploy the backup file using the same Tooling API PATCH command above, pointing `<file>` to the backup.

**Key differences from authoring bundle path:**
- No `sf agent validate authoring-bundle` (no bundle to validate)
- No `sf agent publish authoring-bundle` (changes take effect immediately on Tooling API write)
- No `.agent` file syntax to maintain
- Changes are live immediately — no publish/activate step needed
- **Always backup before writing** — there is no version history in the Tooling API

**When called by drive:** Drive calls this phase with:
- `record_id` — the `GenAiPluginInstructionDef` ID (from `adlc-discover` step 0)
- `instruction_file` — path to the new instruction text
- `backup_dir` — path to the ticket attempts folder