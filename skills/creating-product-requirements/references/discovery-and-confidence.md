# Discovery and Confidence

## Establish Scope and Evidence

Read rules from the repository root to the working directory, then inspect product documents, current behavior, tests, and relevant history. Separate confirmed facts, repository-answerable questions, user-owned product choices, and minor reversible details.

Identify whether the request changes a relevant approved baseline PRD. Treat a document as an approved baseline only when its current metadata is readable and reliable and both independent review and user approval are approved. If multiple approved documents could be the baseline, or the relationship between the baseline and requested change is material and unclear, ask the user to select one rather than silently choosing. Baseline approval does not approve the new change.

Choose exactly one scope:

- `product`: a complete product and its overall success boundary;
- `phase`: one release, milestone, or delivery phase;
- `feature`: one independently definable and acceptable capability.

Require one stable topic formatted as non-reserved lowercase ASCII kebab-case: lowercase ASCII letters and digits separated only by single hyphens. Null, unknown, and pending are reserved and cannot be topics. Use the same topic in the requirements-understanding summary, PRD frontmatter, default filename, and handoff. When requests contain independent topics, do not combine or silently select them. Present the split and ask the user which topic to handle first.

## Reach the Understanding Gate

Ask one to three material questions per turn. Questions are independent only when every possible answer leaves every other question's applicability, options, meaning, priority, and necessity unchanged. Batch only independent questions, keep their numbering stable, and do not add a fourth substantive question. When one answer selects a branch or changes a later question, ask only one decisive question. If the user provides partial answers, preserve the valid answers and reassess the remaining dependencies instead of repeating the whole batch. Do not use defaults or conventional behavior to manufacture certainty.

An expected discovery or choice question with no damage, conflict, permission failure, capability gap, review blocker, or formal confirmation or approval is an `ordinary-clarification`. A request for a requirements-understanding summary confirmation is a checkpoint, not ordinary clarification. A progress-only status update is also not ordinary clarification.

Do not create the PRD while a material unknown remains. When the evidence supports at least 95 percent confidence, present a requirements-understanding summary containing:

- scope and one stable topic;
- the approved baseline PRD path and the requested delta when a baseline applies;
- product problem, goal, and target users;
- core user scenarios;
- scope and non-goals;
- key business rules and constraints;
- acceptance direction;
- remaining assumptions, or an explicit statement that no material unknown remains.

The user must explicitly confirms the current summary. Agent confidence does not replace user confirmation, and confirmation of an older summary does not carry across a material change.

The confirmed requirements-understanding summary is the exclusive authority for product behavior authored in the current full or incremental PRD. Repository evidence can establish existing facts, reveal conflicts, and support a clarification question; it cannot silently contribute a new behavior, non-goal, default, error rule, acceptance branch, or non-functional requirement. If a product behavior is needed but absent from the summary, ask for confirmation instead of adding it.

## Resolve the Document Path

Use this priority:

1. a valid explicit user path;
2. an existing repository convention for product requirements;
3. `docs/requirements/YYYY-MM-DD-<stable-kebab-topic>.md`.

Resolve relative paths against the repository root. If a valid explicit user path is known while content is unresolved, preserve the absolute candidate path in the handoff. Use `null` only when the path itself cannot be selected. Do not overwrite an existing file unless the user identifies it as the current PRD.

For an incremental PRD, the selected path belongs to the new delta document. Do not reuse or overwrite the approved baseline path unless the user explicitly confirms a consolidated replacement and its full scope in the current summary.
