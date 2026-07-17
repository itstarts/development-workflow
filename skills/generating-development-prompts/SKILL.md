---
name: generating-development-prompts
description: Use when users ask for a new-session development prompt, want a spec and plan handed to a main agent or subagents for execution, need copyable Codex development task instructions, or provide an approved fourteen-field handoff that requires session routing.
---

# Generating Development Prompts

## Overview

Route an approved implementation handoff to the current session, a new session, or a blocked result. Generate one copyable development prompt only when the route or an explicit prompt request requires it. Preserve unresolved document state and stop on blocking input instead of emitting a partial prompt.

## Workflow

1. Classify the request as an automatic routing handoff with a verified fourteen-field snapshot, or an explicit prompt request. Automatic routing requires `implementation_gate: open`; an explicit prompt request remains allowed when plan review is `not-approved` or `unknown` and must preserve the implementation gate.
2. Read [references/discovery-policy.md](references/discovery-policy.md), [references/permission-policy.md](references/permission-policy.md), and [references/session-routing-policy.md](references/session-routing-policy.md) completely. Apply their path, source, permission, and routing rules without inventing evidence.
3. Parse the current user message for explicit `spec`, `plan`, `workdir`, `target_branch`, `permissions`, and `topic` values. Resolve conflicting explicit values with a blocking clarification before continuing.
4. Run [scripts/discover_context.py](scripts/discover_context.py) with `python3`. Pass the complete development request or goal as one `--request` argument and the resolved working directory as one `--cwd` argument. Pass `--topic` only when the user explicitly supplied a topic; pass only the explicit `--spec` and `--plan` overrides that exist. Use an argument array or equivalent structured process API so every request and path remains one inert argument; never concatenate user text into shell syntax.
5. Parse the discovery stdout as JSON and inspect the process exit code:
   - On `0`, continue only if `ambiguities` and `errors` are empty.
   - On `2`, use the reported equal candidates to ask one concise blocking clarification. Do not render a prompt.
   - On `3`, report a blocking clarification from the structured errors. Do not fall back from an invalid explicit path and do not render a prompt.
   - On any other nonzero exit, report the controlled failure as a blocking clarification without partial output.
6. Resolve the effective permissions from [references/permission-policy.md](references/permission-policy.md). For automatic routing, validate and freeze the canonical English snapshot, pre-render the Chinese fourteen-field view, and validate its field count, field order, exact labels, and that every contextual mapping is complete and unique before choosing a route and before invoking the renderer.
7. After Chinese view validation succeeds, apply the routing policy to discovery JSON, current conversation context, the canonical snapshot, and currently verified permission, tool, and Agent capabilities. For `current-session`, explain the evidence, wait for explicit implementation approval, and do not render. For `blocked`, explain the session-independent blocker and do not render unless the user later makes an explicit prompt request. Render only for `new-session` or an explicit prompt request.
8. When rendering, require the target new session to inspect its actually loaded personal global custom agents before every delegation. Match the task against each agent's `name` and `description`; use a matching global agent when one exists, use built-in or generic agents only when none matches, and stop that delegation with a capability-gap report when a matching agent exists but cannot be started by name. Require the execution report to record the actual agent name used for every delegation.
9. Extend the discovery JSON with the non-empty development goal, nullable target branch, session rule paths, and permission matrix defined in [references/permission-policy.md](references/permission-policy.md). Keep the discovery object at `schema_version: 1`; preserve its warnings and three-state plan review result. Send it to [scripts/render_prompt.py](scripts/render_prompt.py) on stdin; the renderer uses [assets/development-prompt.md](assets/development-prompt.md).
10. Renderer success is exactly one single Markdown code fence using a dynamic backtick fence and `text` info string. A manual prompt request without a verified upstream snapshot returns renderer stdout verbatim as the entire reply. On automatic routing, place the route and reasons before renderer stdout when present, place renderer stdout before the Chinese view and outside the dynamic fence, then end with the same prevalidated Chinese view. On renderer failure, return a blocking clarification based on machine-readable stderr and no partial prompt.

Do not create a task or thread. Generate text in the current conversation only; never create, fork, send, or hand off a user-visible Codex task/thread as part of this workflow.

## Output Contract

- Produce exactly one prompt only after every required path and ambiguity is resolved and the route or explicit request requires it.
- Automatic routing preserves the same snapshot as the canonical English machine authority, ends with its same prevalidated Chinese view, and does not change document approval state. Manual invocation does not fabricate requirements or gate fields.
- Chinese mapping failure is the only explicit exception to the automatic status-suffix rule. Preserve canonical state, emit a deterministic Chinese blocker that identifies the failed field or integrity condition, do not append a status view, do not choose a route, do not invoke the renderer, and stop the current automatic routing. Retry only after the mapping is corrected.
- Preserve explicit user values.
- Prefer a matching personal global custom agent for each delegation and make unavailable named-agent selection an explicit gate.
- Require TDD for each implementation task, repeated implementation-independent review until approval, and a repeated whole-scope review after integration through the target session's available agents or independent context without depending on a fixed external review skill.
- Preserve the renderer's requirement that an unapproved or unknown plan review is an implementation gate.
- Use a blocking clarification whenever generation cannot safely reach the success contract.
- Keep [scripts/render_prompt.py](scripts/render_prompt.py) and [assets/development-prompt.md](assets/development-prompt.md) responsible only for the prompt body and dynamic fence; never make the renderer append or translate the routing status view.
