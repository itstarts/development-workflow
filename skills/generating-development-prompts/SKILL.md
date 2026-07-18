---
name: generating-development-prompts
description: Use when users ask for a new-session development prompt, want a spec and plan handed to a main agent or subagents for execution, need copyable Codex development task instructions, or provide an approved fourteen-field handoff that requires session routing.
---

# Generating Development Prompts

## Overview

Route an approved implementation handoff to the current session, a new session, or a blocked result. Generate one copyable development prompt only when the route or an explicit prompt request requires it. Preserve unresolved document state and stop on blocking input instead of emitting a partial prompt.

## Workflow

1. Classify the entry as an automatic routing handoff with a verified fourteen-field snapshot, or an explicit manual prompt request. Automatic routing requires `implementation_gate: open`; an explicit prompt request remains allowed when plan review is `not-approved` or `unknown` and must preserve the implementation gate.
2. First read only [references/discovery-policy.md](references/discovery-policy.md). Read each later policy once per workflow only when its stage requires it, unless it changes or the earlier read was unreliable. A missing, unreadable, or conflicting required policy stops that stage.
3. Parse the current user message for explicit `spec`, `plan`, `workdir`, `target_branch`, `permissions`, and `topic` values. Resolve conflicting explicit values with a blocking clarification before continuing.
4. Run [scripts/discover_context.py](scripts/discover_context.py) with `python3`. Pass the complete development request or goal as one `--request` argument and the resolved working directory as one `--cwd` argument. Pass `--topic` only when the user explicitly supplied a topic; pass only the explicit `--spec` and `--plan` overrides that exist. Use an argument array or equivalent structured process API so every request and path remains one inert argument; never concatenate user text into shell syntax.
5. Parse the discovery stdout as JSON and inspect the process exit code:
   - On `0`, continue only if `ambiguities` and `errors` are empty.
   - On `2`, use the reported equal candidates to ask one concise blocking clarification. Do not render a prompt.
   - On `3`, report a blocking clarification from the structured errors. Do not fall back from an invalid explicit path and do not render a prompt.
   - On any other nonzero exit, report the controlled failure as a blocking clarification without partial output.
6. When a permission matrix is needed after successful discovery, read [references/permission-policy.md](references/permission-policy.md) completely and resolve the effective permissions. A manual prompt path needs this policy for prompt rendering but does not load the routing policy when no verified upstream snapshot exists.
7. Only for automatic routing, or for a blocked reply that owns a verified upstream full status, read [references/session-routing-policy.md](references/session-routing-policy.md) completely. Validate and freeze the canonical English snapshot, invoke local [scripts/render_handoff.py](scripts/render_handoff.py) with `handoff_schema: workflow`, `view: full`, `stage: null`, and `next_step: null`, and trust only exit-code-zero stdout before choosing a route. Never import a sibling copy or use partial status output.
8. After full-view validation succeeds, apply the routing policy to discovery JSON, current conversation context, the canonical snapshot, and currently verified permission, tool, and Agent capabilities. For `current-session`, explain the evidence, wait for explicit implementation approval, and do not render a development prompt. For `blocked`, explain the session-independent blocker and do not render unless the user later makes an explicit prompt request. Render only for `new-session` or an explicit prompt request.
9. When rendering, require the target session at its first delegation to build one session-scoped inventory from actually loaded personal global custom agents, recording `name`, `description`, and whether the read was reliable. Later delegations do not rescan. Refresh once when configuration changed, the initial read failed, launch by name fails, an observable capability conflict appears, or the user explicitly requests a refresh. After a failed refresh, preserve the capability gap. Keep this inventory only in conversation context and record each actual delegated Agent name.
10. Extend the discovery JSON with the non-empty development goal, nullable target branch, session rule paths, and permission matrix defined in [references/permission-policy.md](references/permission-policy.md). Keep the discovery object at `schema_version: 1`; preserve its warnings and three-state plan review result. Send it to [scripts/render_prompt.py](scripts/render_prompt.py) on stdin; the renderer uses [assets/development-prompt.md](assets/development-prompt.md).
11. `render_prompt.py` success is exactly one single Markdown code fence using a dynamic backtick fence and `text` info string. A manual prompt request without a verified upstream snapshot returns its stdout verbatim as the entire reply and does not load the routing policy or append status. On automatic routing, place the route and reasons first; when a prompt is required, place `render_prompt.py` stdout before the frozen `render_handoff.py` stdout and outside the dynamic fence, then end with that same renderer-validated handoff view. On prompt-renderer failure, return a blocking clarification based on machine-readable stderr and no partial prompt.

Do not create a task or thread. Generate text in the current conversation only; never create, fork, send, or hand off a user-visible Codex task/thread as part of this workflow.

## Output Contract

- Produce exactly one prompt only after every required path and ambiguity is resolved and the route or explicit request requires it.
- Automatic routing preserves the same snapshot as the canonical English machine authority, ends with its same renderer-validated Chinese view, and does not change document approval state. Manual invocation does not fabricate requirements or gate fields.
- Handoff renderer failure is the only explicit exception to the automatic status-suffix rule. Preserve canonical state, use machine-readable stderr to emit a deterministic Chinese blocker that identifies the failed field or integrity condition, do not append a status view, do not choose any route, do not invoke `render_prompt.py`, and stop the current automatic routing. Retry the handoff renderer only after the canonical source or renderer defect is corrected.
- Preserve explicit user values.
- Prefer a matching personal global custom agent for each delegation and make unavailable named-agent selection an explicit gate.
- Require TDD and affected-scope validation for each implementation task without deriving review gates from task count. Require one implementation-independent review of the latest complete diff after integration, with the same reviewer re-checking in-scope fixes until approval. Add an intermediate milestone review only when the approved plan explicitly identifies a material risk boundary or an otherwise unverified critical foundation needed by later tasks. Use the target session's available agents or independent context without depending on a fixed external review skill.
- Preserve the renderer's requirement that an unapproved or unknown plan review is an implementation gate.
- Use a blocking clarification whenever generation cannot safely reach the success contract.
- Keep [scripts/render_prompt.py](scripts/render_prompt.py) and [assets/development-prompt.md](assets/development-prompt.md) responsible only for the prompt body and dynamic fence; never make the renderer append or translate the routing status view.
