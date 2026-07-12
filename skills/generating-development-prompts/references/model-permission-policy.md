# New-Session Effort and Permission Policy

Build one effort recommendation for the target new session and one permission record.

## Resolve the New-Session Effort

Use this descending source priority:

1. An explicit `reasoning_effort` in the current user message.
2. The default recommendation `high`.

Accept only `minimal`, `low`, `medium`, `high`, or `xhigh`. Record the result as:

```json
{
  "recommended_effort": "high"
}
```

The generated prompt contains exactly this one effort recommendation. It does not assign efforts to the main agent after startup, implementation subagents, reviewers, or other roles.

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
