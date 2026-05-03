# Agentforce Architecture Playbook

Living architecture reference for project ADLC work. This document explains how to reason about Agentforce systems before deciding whether a ticket should be solved with instructions, topic routing, actions, data/RAG, Flow/Apex/API work, testing changes, or product clarification.

This playbook is local operational guidance for runtime architecture and root-cause surface selection. Salesforce upstream docs remain the standard reference for platform behavior, but local ADLC decisions must also account for live org evidence, traces, Testing Center behavior, and project artifact rules.

---

## Quick Routing Index

Use this index first when deciding whether a ticket is really prompt-facing or belongs to another Agentforce surface.

| Situation | Read |
|---|---|
| Need to decide if this is actually a prompt problem | `Failure Taxonomy` and `Solution Strategy Review` |
| Need to understand possible fix surfaces | `Architecture Surfaces` |
| Need the Phase 3 dependency checklist | `Discover Dependency Map` |
| Topic routing might be wrong | `Runtime Model`, `Architecture Surfaces`, and `Failure Taxonomy` |
| Action/tool behavior might be wrong | `Architecture Surfaces` and `Discover Dependency Map` |
| Data, auth, context, or lower-env setup might be wrong | `Data and context surfaces`, `Testing and observability surfaces`, and `Discover Dependency Map` |
| Trusted layer may be changing output | `Runtime Model` and `Failure Taxonomy` |
| Prompt/instruction is confirmed as the right fix | Hand off to `adlc/playbooks/prompt-engineering-playbook.md` |

---

## Official References

Pinned references:

- Salesforce ADLC guide: https://architect.salesforce.com/docs/architect/fundamentals/guide/agent-development-lifecycle
- Salesforce upstream ADLC repo: https://github.com/SalesforceAIResearch/agentforce-adlc
- Agentforce Developer Guide: https://developer.salesforce.com/docs/ai/agentforce/guide/get-started.html
- Agentforce Trust Layer: https://developer.salesforce.com/docs/ai/agentforce/guide/trust.html

Freshness rule:

- Read this local playbook first.
- Check Salesforce Architect and Agentforce Developer docs when a decision depends on current platform behavior, routing, topic/subagent semantics, action invocation, trust layer behavior, Testing Center behavior, deployment/versioning, STDM/monitoring, or authoring bundle semantics.
- Prefer pinned URLs when citing evidence, but use targeted freshness searches on `architect.salesforce.com` and `developer.salesforce.com/docs/ai/agentforce` if a page appears moved, stale, or insufficient.
- If Salesforce docs conflict with local guidance or live org evidence, pause for HITL and classify the issue as a playbook update, ticket-specific exception, or spike.

---

## Terminology

| Term | Use in ADLC | Notes |
|---|---|---|
| Topic | Default ADLC term for Builder/runtime routing units | Used for discovery, baselines, Testing Center, and artifact paths. |
| Subagent | Agent Script/developer-doc term for a specialized execution unit | Treat as equivalent to topic when reading `.agent` / Agent Script docs, unless a doc distinguishes them explicitly. |
| Action | Tool the agent can invoke | May be backed by Flow, Apex, prompt template, retriever, API, or other Salesforce capability. |
| Instruction | LLM-facing guidance | Can appear at global, topic/subagent, action, input field, output field, or template levels. |
| Retriever/RAG | Knowledge retrieval path | Often a data quality or indexing issue, not an instruction issue. |
| Trusted layer | Salesforce safety/grounding layer after response generation | Can modify or block generated output. |
| STDM | Session Trace Data Model | Used for production observation and root-cause analysis where available. |

ADLC standard: use `topic` in ticket folders, baselines, evals, and user-facing process docs. Use `subagent` when interpreting Salesforce upstream Agent Script docs or `.agent` structures.

---

## Runtime Model

```text
User utterance
  -> Topic/subagent selection
  -> Instruction and tool context assembly
  -> Action selection
  -> Action execution
  -> Tool/data results enter context
  -> Response generation
  -> Trusted layer / safety / grounding checks
  -> Response to user
```

Important implications:

- If routing is wrong, prompt wording inside the intended topic will not run.
- If action selection is wrong, response instructions may be operating on missing or incorrect data.
- If action output is wrong, instructions may only hide the problem.
- If data/RAG retrieval is wrong, prompt edits can create false confidence.
- If the trusted layer changes the response, instruction edits may not fully explain observed behavior.
- If lower environments lack prod-like data, tests may not prove production readiness.

---

## Architecture Surfaces

### Agent-level surfaces

- Agent description/persona/tone
- Global instructions
- Default agent user and permissions
- Deployment, publish, activate, and version state
- Salesforce CLI and org authentication state

### Topic/subagent surfaces

- Classification / routing description
- Scope and guardrails
- Topic/subagent instructions
- Reasoning structure
- Action list available to the topic/subagent
- Variables and context dependencies

### Action surfaces

- Action description
- Action availability and invocation name
- Input field descriptions and required data
- Output field descriptions and returned data shape
- Backing target: Flow, Apex, prompt template, retriever, API, or other integration
- Auth, permissions, external system behavior, and error handling

### Data and context surfaces

- Linked variables
- Mutable variables
- MessagingSession / RoutableId
- User/account/contact records
- Sandbox seed data
- Knowledge indexes and retriever state
- Feature flags and org permissions
- Expiring tokens or credentials

### Testing and observability surfaces

- `sf agent preview`
- Testing Center / `sf agent test`
- Static `conversationHistory`
- Live scenario simulation
- STDM session traces
- Local trace files from `--authoring-bundle`
- Eval reports and raw CSV outputs

---

## Failure Taxonomy

Use this taxonomy before choosing a fix.

| Failure class | Signal | Likely fix location |
|---|---|---|
| Topic classification | Wrong topic handles the utterance | Topic classification/scope, adjacent topic boundaries, routing tests |
| Instruction gap | No instruction governs the behavior | Topic/global instruction, with eval coverage |
| Instruction ambiguity | Instruction can be read multiple ways | Reword or restructure instruction |
| Instruction conflict | Two levels give competing guidance | Resolve conflict across global/topic/action/field/template instructions |
| Action selection | Wrong action called, or right action not called | Action description, action availability, input collection, topic action list |
| Action execution | Action errors or returns wrong shape/data | Flow/Apex/API/retriever implementation, auth, permissions, data setup |
| Missing context | Agent asks/escalates because context is absent | Context variables, session setup, Testing Center context, data seeding |
| Knowledge retrieval | Irrelevant, stale, or missing retrieved content | Knowledge/RAG source, indexing, retriever config, query generation |
| Prompt template statelessness | Template ignores conversation context | Pass required context explicitly or change template/action inputs |
| Trusted layer behavior | Response changes/blocks after generation | Safety/grounding review, policy, product decision, residual risk |
| Environment gap | QA cannot reproduce production dependency | Testability classification, prod-like data, proctor validation, sign-off |
| Product ambiguity | No clear definition of correct behavior | Product acceptance criteria, HITL, ticket refinement |

Wrong fix pattern: adding louder prompt text for a routing, action, data, auth, or environment problem.

---

## Discover Dependency Map

Discovery must produce a dependency map before strategy planning.

For each affected topic/subagent and likely scenario, capture:

- Topic/subagent name and routing/classification surface
- Instruction records and global instruction interactions
- Actions available and actions expected
- Backing targets for each action
- Input fields, output fields, and data dependencies
- Variables: linked, mutable, session, user, account, contact, or custom
- Required org permissions, default agent user, and feature flags
- External APIs, auth tokens, connected app access, or credentials
- Knowledge/RAG sources, retriever names, and indexing assumptions
- Lower-env vs production differences
- Whether `sf agent preview`, Testing Center, STDM, or live proctor validation is the right validation path

Testability classifications:

- `fully-testable-lower-env`
- `partially-testable-lower-env`
- `requires-prod-like-data`
- `requires-token-or-context`
- `requires-external-system`
- `not-lower-env-testable`

If a scenario is not lower-env testable, do not mark it passed. Document the limitation, propose the next-best validation path, and require product/technical/proctor sign-off for residual risk.

---

## Solution Strategy Review

Before editing, answer:

1. Is this actually a prompt/instruction problem?
2. Is the current topic/subagent the right place?
3. Does the ticket-requested approach conflict with architecture evidence?
4. Is the right fix global instruction, topic instruction, action description, field description, new topic, new action, retriever/RAG, Flow/Apex/API, test setup, or product clarification?
5. Which 2-3 strategies are viable, and what are their trade-offs?
6. What is the validation path for each strategy?
7. Which requirements cannot be tested accurately in the current lower environment?

Hard gate: if the recommended strategy contradicts the ticket, changes product behavior, changes eval criteria, touches routing, requires new action/topic/data work, or accepts untestable risk, pause for HITL.

If the best surface is prompt-facing, hand the implementation strategy to `adlc/playbooks/prompt-engineering-playbook.md`: prompt mental model, prompt surface selection, targeted-edit versus restructure gate, insertion point, prompt goal, and prompt-specific validation. This file decides whether the problem belongs in prompts; the prompt playbook decides how to make the prompt change safely.

---

## Relationship To Local Playbooks

- Use this file for architecture, dependency mapping, runtime/root-cause surface selection, and non-prompt root cause analysis.
- Use `adlc/playbooks/prompt-engineering-playbook.md` for prompt implementation strategy, instruction writing, prompt structure, insertion points, targeted-edit versus restructure decisions, and prompt-specific testing principles.
- Use `adlc/docs/core-process-overlay.md` for local ADLC process overlays that coordinate Salesforce upstream skills with project ticket/HITL/eval workflows.
- Use Salesforce upstream skills as standard implementation capabilities. Layer project workflow additively.
