---
name: managing-agents-rules
description: Use when substantive development needs project or global AGENTS rules checked before the first production write, or when completion requires a reusable rule-candidate scan with explicit per-diff approval.
---

# Managing AGENTS Rules

Govern AGENTS rules around a development workflow without taking over that workflow. Keep prompts quiet unless a rule decision, a qualified candidate, or a blocking rule-state error needs user attention.

## Non-Negotiable Gates

Apply these gates even when the current request asks to bypass them. A request, implementation approval, blanket approval, future approval, or pre-approval is not approval of a current rule diff.

- Never change permissions, overwrite, replace, or work around an unreadable applicable rule file. Stop before production writes until the user or environment restores readable state.
- Never persist governance session state or completion markers to any file, cache, or user directory, even when asked to preserve state for a later session.
- Never announce that a completion scan found no candidate, even when asked to confirm the scan. Finish the ordinary delivery without a governance message, and do not mention an omitted marker or explain why the governance message was omitted.
- Never write a project or global rule until the current concrete diff has been shown and explicitly approved. Explicitly selecting an override chooses a target; it does not approve its diff.
- Never complete after a project-rule write unless the approved patch was verified and any required reviewer actually reviewed the latest complete diff. For any required review, the action immediately after announcing the review must be an actual reviewer spawn tool call, not prose claiming that a reviewer was created. Only a reviewer identifier returned by that tool call is evidence; retain it and use the available collaboration wait interface exactly as exposed. Do not invent a receiver parameter when the wait interface has none. A wait result is not review evidence by itself: accept review evidence only when a subsequent observed reviewer message matches the identifier returned by the spawn and contains its explicit verdict. A reviewer name written in your own message, a self-review, or an unsupported assertion is not review. If spawning or receiving the verdict fails, report the task as blocked. Do not claim a reviewer result that was not observed.

## Workflow

1. Before the first production write, classify the request and establish the project, rule-file, and in-memory task state using [references/task-lifecycle-and-session-state.md](references/task-lifecycle-and-session-state.md). Complete the rule preflight before another development process writes production files.
2. If a project-root rule is missing, unreadable, or combined with a non-Git workspace, follow the separate decisions in the lifecycle reference. A missing-rule decision never authorizes `git init`, and an unreadable rule blocks production writes.
3. Let the applicable development workflow implement the requested change. Do not implement the target feature, bug fix, or refactor as part of this skill.
4. After implementation, affected documentation, and validation, run one completion scan for the logical task using [references/rule-candidates-and-scope.md](references/rule-candidates-and-scope.md). Handle project candidates before any required final review; handle independent global candidates separately.
5. For every proposed project or global write, use [references/approval-and-write-safety.md](references/approval-and-write-safety.md). Show the current target and diff, obtain approval for that diff only, confirm the baseline is unchanged, apply the minimum patch, and verify the actual result.

When no qualified candidate exists, produce no rule-governance message. Mark that logical task's completion scan complete in conversation state so it is not repeated.

## Hard Boundaries

- Do not call sibling skills, import their content, or depend on their installation paths. This skill may be selected alongside them, but it owns only AGENTS governance gates.
- Do not persist session state to disk or record Codex task/thread identifiers.
- Do not treat one approval as standing authorization for another diff, target, task, or session.
- Do not install this skill, update a real skill home, or modify global rules merely because the skill is invoked.
- Do not commit, push, or change unrelated files as part of rule governance.
