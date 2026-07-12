---
name: generating-development-prompts
description: Use when users ask for a new-session development prompt, want a spec and plan handed to a main agent or subagents for execution, or need copyable Codex development task instructions.
---

# Generating Development Prompts

## Overview

Generate one copyable development prompt from explicit user inputs, repository evidence, session capabilities, and fixed execution policy. Preserve uncertainty and stop on unresolved input instead of emitting a partial prompt.

## Workflow

1. Parse the current user message for explicit `spec`, `plan`, `workdir`, `target_branch`, `permissions`, `model`, `reasoning_effort`, and `topic` values. Resolve conflicting explicit values with a blocking clarification before continuing.
2. Read [references/discovery-policy.md](references/discovery-policy.md) and [references/model-permission-policy.md](references/model-permission-policy.md) completely. Apply their source precedence and uncertainty rules without inventing evidence.
3. Run [scripts/discover_context.py](scripts/discover_context.py) with `python3`. Pass the complete development request or goal as one `--request` argument and the resolved working directory as one `--cwd` argument. Pass `--topic` only when the user explicitly supplied a topic; pass only the explicit `--spec` and `--plan` overrides that exist. Use an argument array or equivalent structured process API so every request and path remains one inert argument; never concatenate user text into shell syntax.
4. Parse the discovery stdout as JSON and inspect the process exit code:
   - On `0`, continue only if `ambiguities` and `errors` are empty.
   - On `2`, use the reported equal candidates to ask one concise blocking clarification. Do not render a prompt.
   - On `3`, report a blocking clarification from the structured errors. Do not fall back from an invalid explicit path and do not render a prompt.
   - On any other nonzero exit, report the controlled failure as a blocking clarification without partial output.
5. Read the model identity, current reasoning effort, supported efforts, subagent override capability, session-exposed rule files, and effective permissions from actual current-session evidence. Consult local Codex configuration only when session evidence is absent. Query only official documentation, and only when current permission allows it and the unresolved capability is necessary. Record separate `value`, `source`, and `certainty` evidence for every model field. When per-subagent effort overrides are unavailable or unknown, use the portable [assets/final-reviewer.toml](assets/final-reviewer.toml) role template and apply the project-level `final-reviewer` inheritance sequence from the model policy; the renderer embeds the complete template in the generated prompt so the target project does not depend on this skill's installation path. Do not claim that the current collaboration API can select that role without direct evidence. A request to run end-to-end without pausing is a preference, not a blocking ambiguity: when confirmed platform capability makes that preference infeasible, do not ask the user to choose a weaker execution mode during generation; encode the mandatory pause and current-thread switch gate in the generated prompt. Ask a blocking clarification only if the capability evidence fields themselves conflict.
6. Extend the discovery JSON with the non-empty development goal, nullable target branch, session rule paths, model evidence and role efforts, and permission matrix defined in [references/model-permission-policy.md](references/model-permission-policy.md). Keep the discovery object at `schema_version: 1`; preserve its warnings and three-state plan review result.
7. Send the complete JSON object to [scripts/render_prompt.py](scripts/render_prompt.py) on stdin. The renderer uses [assets/development-prompt.md](assets/development-prompt.md); do not substitute user text through a shell or edit the template during generation.
8. On renderer success, return the renderer stdout verbatim as the entire current reply. Renderer stdout remains the complete reply even when the user requests a presentation wrapper such as a Markdown code fence. Add no heading, code fence, preface, summary, or commentary. On renderer failure, return a blocking clarification based on its machine-readable stderr and no partial prompt.

Do not create a task or thread. Generate text in the current conversation only; never create, fork, send, or hand off a user-visible Codex task/thread as part of this workflow.

## Output Contract

- Produce exactly one prompt only after every required path and ambiguity is resolved.
- Preserve explicit user values and source certainty; never present an unknown model capability as confirmed.
- Preserve the renderer's requirement that an unapproved or unknown plan review is an implementation gate.
- Use a blocking clarification whenever generation cannot safely reach the success contract.
