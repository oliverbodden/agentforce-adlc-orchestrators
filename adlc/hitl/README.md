# HITL Decision Log

Every human-AI interaction during an ADLC session is logged here in JSONL format.
One JSON object per line, append-only.

## Files

| File | Scope | Purpose |
|---|---|---|
| `{ticket-key}.jsonl` | Per ticket | Granular audit trail for a single drive session |
| `index.jsonl` | Cross-ticket | Central rollup — every entry also appended here |

## Schema

```json
{
  "ts": "2026-03-27T14:32:00Z",
  "session_id": "chat-abc123",
  "phase": "3-discover",
  "checkpoint": "confirm-agent",
  "type": "correction",
  "asked": "Confirm agent, version, org, edit strategy",
  "decision": "v30 not v29, DEV org, Tooling API",
  "agent": "indeed-service-agent",
  "topic": "invoice",
  "ticket": "ESCHAT-1234",
  "who": "obguzman"
}
```

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `ts` | ISO 8601 | yes | When the interaction happened |
| `session_id` | string | yes | Cursor chat/session identifier — correlate entries to a specific conversation |
| `phase` | string | yes | ADLC phase: `1-goal`, `2-refine`, `3-discover`, `4-plan`, `5-execute`, `6-present`, `7-handoff` |
| `checkpoint` | string | yes | Specific pause point: `ticket-readiness`, `scope-alignment`, `confirm-agent`, `approve-plan`, `mid-iteration`, `accept-results`, `promote-baseline`, `early-exit` |
| `type` | enum | yes | One of: `approval`, `correction`, `rejection`, `context`, `escalation`, `early-exit` |
| `asked` | string | yes | What the skill presented or asked |
| `decision` | string | yes | What the user said or decided |
| `agent` | string | no | Agent name (if known at this point) |
| `topic` | string | no | Topic name (if applicable) |
| `ticket` | string | no | Ticket key (if applicable) |
| `who` | string | yes | Who made the decision |

## Type definitions

| Type | When to use |
|---|---|
| `approval` | User approved a checkpoint as-is |
| `correction` | User changed something the skill proposed or assumed |
| `rejection` | User rejected a plan, approach, or result |
| `context` | User provided information the skill didn't have |
| `escalation` | Skill couldn't decide, pulled user in for ambiguous result |
| `early-exit` | Session ended before Phase 7 (crash, user stopped, or pivot) |

## How to analyze

Load `index.jsonl` into any tool that reads JSON lines:

```python
import json
entries = [json.loads(line) for line in open("index.jsonl")]

# Correction rate by phase
from collections import Counter
corrections = [e["phase"] for e in entries if e["type"] == "correction"]
print(Counter(corrections))

# Most common correction patterns
for e in entries:
    if e["type"] == "correction":
        print(f'{e["phase"]} | {e["asked"][:60]} → {e["decision"][:60]}')
```

Or ask an AI: "Read adlc/hitl/index.jsonl and tell me what patterns you see in corrections and rejections."

## Rotation

Roll `index.jsonl` quarterly or when it exceeds ~1000 entries:
```bash
mv index.jsonl archive/index-2026-Q1.jsonl
```
Per-ticket files stay with their ticket folders permanently.
