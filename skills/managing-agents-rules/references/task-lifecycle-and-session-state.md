# Task Lifecycle and Session State

## Trigger Classification

Treat feature implementation, a bug fix, a refactor, and a behavior-changing test, configuration, or engineering documentation change as substantive development. Run the preflight before its first production write.

Read-only analysis does not trigger this governance skill. Explanation does not trigger this governance skill. Review does not trigger this governance skill. A status query, log inspection, branch creation, or pure Git operation also does not trigger it. When classification is genuinely uncertain, ask before a possible production write rather than silently skipping the gate.

## Project Root and Rule State

For a Git workspace, use successful `git rev-parse --show-toplevel` output as the normalized project root. Outside Git, use only the runtime-provided workspace root; never infer an arbitrary current subdirectory. If neither root is reliable, stop production writes and report the unresolved root while allowing safe read-only diagnosis.

Check the project root `AGENTS.md`. A subdirectory `AGENTS.md` remains applicable in its scope but cannot replace the project root file. A non-empty `AGENTS.override.md` must still be followed under Codex precedence, but it does not replace the base AGENTS.md existence check.

Track `project_rules_check` as `unchecked | readable | missing | declined | created | unreadable`. An unreadable root rule is not missing: report the read error; do not change its permissions, propose an overwrite, or bypass it; and block production writes until the user or environment makes it readable and it is checked again. A readable root needs no governance prompt. For a missing root, derive only evidence-backed project rules and present a proposed creation diff; a user decline changes the project state to `declined` and suppresses further project-rule prompts for that project in this session.

## In-Memory Isolation

Maintain a conversation-only state table keyed by normalized project root. Each project owns `project_rules_check`, `git_init_prompt`, and one `TaskCompletionState` per logical development task. Each task state has a temporary logical key, a scope summary, and `completion_scan: pending | completed`.

Do not persist this state to disk, a cache, a user directory, or project files, even if the user requests a marker or continuation file. Do not use or record Codex task/thread identifiers. A new project starts from `unchecked`; a new session does not inherit prior declines or checks. Independent logical development tasks in one project keep separate completion scans, while implementation slices delivered as one integrated scope share one scan.

## Non-Git Decision

On the first check of a confirmed non-Git workspace, recommend initializing Git even when the requested change is small. Keep that recommendation separate from the project-rule decision, but present both decisions in the same preflight response so the user can approve or decline each action independently.

For a confirmed non-Git workspace, project rule creation and `git init` are separate actions requiring separate explicit approval. Approval of a rule diff does not approve Git initialization, and approval of `git init` does not approve a rule diff.

Track `git_init_prompt` as `unchecked | not-applicable | declined | initialized | failed`. Run `git init` only at the confirmed workspace root after current explicit approval. If declined, remain silent for that project during the session. If it fails, report the observed error and do not retry automatically; the failure does not cancel a separately approved rule action or the original development task.
