# Discovery and Confidence

## Establish Scope and Evidence

Read rules from the repository root to the working directory, then inspect product documents, current behavior, tests, and relevant history. Separate confirmed facts, repository-answerable questions, user-owned product choices, and minor reversible details.

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
- product problem, goal, and target users;
- core user scenarios;
- scope and non-goals;
- key business rules and constraints;
- acceptance direction;
- remaining assumptions, or an explicit statement that no material unknown remains.

The user must explicitly confirms the current summary. Agent confidence does not replace user confirmation, and confirmation of an older summary does not carry across a material change.

## Resolve the Document Path

Use this priority:

1. a valid explicit user path;
2. an existing repository convention for product requirements;
3. `docs/requirements/YYYY-MM-DD-<stable-kebab-topic>.md`.

Resolve relative paths against the repository root. If a valid explicit user path is known while content is unresolved, preserve the absolute candidate path in the handoff. Use `null` only when the path itself cannot be selected. Do not overwrite an existing file unless the user identifies it as the current PRD.
