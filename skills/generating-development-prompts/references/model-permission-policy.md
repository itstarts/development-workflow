# Model and Permission Policy

Build model, reasoning-effort, and permission records from evidence visible in the current session. Keep evidence field-specific; an object-level source never proves all nested capabilities.

## Resolve Model Evidence

Use this descending source priority without allowing a lower source to overwrite a higher one:

1. Explicit values in the current user message.
2. Actual model, effort, permission, and capability information exposed by the current session.
3. Local Codex configuration and currently available local model information.
4. Official OpenAI documentation, only when permission to query it exists and a necessary fact remains unresolved.
5. A capability recommendation marked `unknown` or a documented default role target.

Never infer a concrete model name, availability, supported effort list, or subagent override ability from memory. For each of `identity`, `current_effort`, `supported_efforts`, and `subagent_overrides_supported`, record `value`, `source`, and `certainty` separately. Use `certainty: confirmed` only for direct evidence. Otherwise use `certainty: unknown`; use JSON `null` with `source: unconfirmed` when no value is established. “不确定” is not a confirmed capability.

Keep the actual current session effort independent from role targets. An unscoped explicit reasoning effort overrides only the main-agent role target; a role-scoped value overrides only that role.

Use these default role targets unless a higher-priority explicit value applies:

| Role | Target effort |
|---|---|
| Main agent | `high` |
| Implementation subagent | `medium` |
| Task and integration review | `high` |
| Final full review | `xhigh` |

Retain `xhigh` as the final-review target when supported efforts are unknown. Downgrade it only when `supported_efforts.certainty` is `confirmed` and its explicit list excludes `xhigh`; then choose the highest confirmed effort in the list. Add a pre-final-review confirmation gate whenever support remains unknown.

When `subagent_overrides_supported` is confirmed `false`, use the portable `assets/final-reviewer.toml` template to establish or confirm a project-level custom `final-reviewer` role before startup. The renderer embeds the complete template in the generated prompt, so the target project never needs access to the installed skill directory. The resulting `.codex/agents/final-reviewer.toml` sets `sandbox_mode = "read-only"` and omits both `model` and `model_reasoning_effort`. Codex automatically discovers project agent roles from the project configuration folder; omitting those fields allows the role to inherit the current thread configuration instead of locking a role-specific value.

Enforce this exact final-review sequence: pause the main thread; confirm the project-level role exists, is read-only, and has no fixed model or effort; wait for the user to switch the current thread to the final target (`xhigh` unless a confirmed supported-effort list requires the documented downgrade); only after that switch start `final-reviewer`; record that it inherits the current thread effort. Apply the same sequence when override capability is unknown. Never claim that the currently exposed collaboration API can select a custom agent type unless that capability is directly confirmed; role startup remains a final-gate action after the user-controlled switch.

A request to run end-to-end without pausing is a preference, not a blocking ambiguity. When confirmed platform capability makes that preference infeasible, do not ask the user to choose between pausing and weakening the requested role efforts during prompt generation; encode the mandatory pause and current-thread switch gate in the generated prompt. Ask a blocking clarification only when capability evidence fields themselves conflict.

## Build the Permission Matrix

Allow these operations by default within the stated development scope:

- Create a development branch or worktree.
- Create local commits.
- Query official OpenAI or relevant third-party documentation.
- Install dependencies explicitly listed by the plan.
- Download Playwright browsers required by the plan.
- Start a local development service.
- Run tests, builds, lint, and local validation.

Forbid these operations by default:

- `push`, `merge`, `rebase`, `tag`, and `release`.
- Production deployment.
- Actual Cloudflare or DNS changes.
- Access to unauthorized secrets, tokens, credentials, or production data.

Apply explicit user permission additions or restrictions exactly and mark the matrix source as `explicit`. If the same operation is explicitly both allowed and forbidden, record an error and ask a blocking clarification; never choose a side. User permission overrides cannot bypass platform safety or approval mechanisms. Require the current session's approval flow for destructive actions, sensitive data, or external-state changes even when the task otherwise permits them.
