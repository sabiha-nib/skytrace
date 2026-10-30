# Multi-agent research: design only (not implemented)

**Status: BLOCKED.** Multi-agent research needs a verified model provider, and this environment has none. The Meta Model API is
refused by the proxy (403) and no key is configured (`scripts/diagnose_environment.py`, `docs/TEST_REPORT.md` G12). Nothing in
Skytrace 0.7 runs agents, and no screen shows a conversation between agents. The five Review Room roles (REVIEW-1) are
deterministic rule sets. They are labelled "software reviewer" and are not agents.

This document records how agents would fit once a provider is verified, so that the existing integrity rules carry over
unchanged.

## Principles

1. **Agents propose; the registry decides.** An agent's output is a structured proposal: a plan of CAPREG actions, a
   challenge, a draft paragraph or a candidate test. It runs only through the same validation the planner and autopilot use:
   `planner.validate_intent`, the registered action list, preconditions, permission class and your authorization. An agent cannot
   call the network, export or run an action that the autopilot level does not allow.
2. **Agents never measure.** Every number comes from the deterministic tools (`ai/tools.py`, `science/`). As in the copilot, an
   agent's claims are checked against tool outputs (GUARD-3), and unsupported numbers are withheld.
3. **Outputs are records, not dialogue.** Each agent result is stored as a typed, hashed item in the session. It holds the role,
   provider, model identifier, prompt hash, tool calls, cited record fields, output and validation verdict. The interface shows
   these records side by side. It never presents them as a chat between personas.
4. **Disagreement is data.** When two agents disagree, the comparison shows which record fields each cited and which rule or tool
   output decides the question. If nothing decides it, the result is "unresolved". There is no vote and no confidence score.
5. **A person approves.** Results enter the notebook as labelled drafts (like copilot drafts). Plans need the same authorization
   as the autopilot.

## Components (planned)

| Component | Role | Reuses |
|---|---|---|
| Agent capability registry | Role → allowed tools and actions, maximum permission class | CAPREG-3 `PERMISSION`, `AUTOPILOT_LEVELS` |
| Provider adapter | One interface for any verified provider; keys from the environment only | `ai/meta_client.py`, `ai/copilot.py` |
| Structured output schema | SCHEMA-1 spec per role (proposal, citations, tool calls) | `schema.py` |
| Validator | Tool-output check, action validation, citation resolution | GUARD-3, `planner.validate_intent`, LEDGER-1 |
| Execution log | Hashed agent records in the session | SESSION-1 history |
| Comparison view | Side-by-side records and the rule or tool that decides | REVIEW-1 findings, ASL-1 rules |

## What unblocks it

There are two ways forward. One is a reachable provider with a key in the environment, plus a passing
`scripts/meta_smoke_test.py` and recorded live tests. The other is an organization-approved local model server. Until one of
these is in place, the catalogue keeps the related concepts (P7-141–143, P7-147, P7-148) BLOCKED.
