> **Limitation:** `sf agent preview` does NOT support passing context variables (RoutableId, EndUserId, ContactId). For service agents that depend on linked variables, preview tests run without messaging session context and may produce inaccurate results (e.g., no account data, escalation-heavy behavior). Use Testing Center (Mode B) with `contextVariables` in the YAML spec for accurate testing of service agents.

### Phase 3: Export and Analyze Results

**CSV Export (for regression comparison):**

When called by `adlc-drive` or for regression analysis, export results to CSV:

After a test run, export results to CSV:

```bash
JOB_ID="<from test run>"
sf agent test results --job-id "$JOB_ID" --result-format json -o <org> --json > /tmp/results.json

python3 -c "
import json, csv, re
lines = open('/tmp/results.json').readlines()
s = ''.join(l for l in lines if not l.strip().startswith('\u203a'))
clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
data = json.JSONDecoder(strict=False).decode(clean)
rows = []
for tc in data['result']['testCases']:
    rows.append({
        'Utterance': tc['inputs']['utterance'],
        'Actual Action': tc.get('generatedData', {}).get('actionsSequence', ''),
        'Actual Outcome': tc.get('generatedData', {}).get('outcome', ''),
        'Conversation History': '[]',
        'Output Latency Milliseconds': ''
    })
with open('<output.csv>', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['Utterance','Actual Action','Actual Outcome','Conversation History','Output Latency Milliseconds'])
    w.writeheader()
    w.writerows(rows)
print(f'Exported {len(rows)} rows')
"
```

**Important:** Testing Center output may contain HTML-encoded characters (e.g., `&#39;` for `'`). Always use `html.unescape()` when analyzing response text.

**contextVariables format (MUST be array, NOT object):**
```yaml
contextVariables:
  - name: RoutableId
    value: "0MwEm00000BkDk2KAF"
```
Using flat object format (`contextVariables: {RoutableId: "..."}`) causes `tc.contextVariables?.map is not a function` error.
