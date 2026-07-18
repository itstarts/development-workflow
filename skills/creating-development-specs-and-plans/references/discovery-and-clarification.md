# Discovery and Clarification

## Establish Evidence

1. Read every session-supplied rule. Discover filesystem `AGENTS.md` or `CLAUDE.md` from the repository root to the working directory, outermost to innermost. Never recursively search above the repository root.
2. Inspect repository status, relevant documentation, existing implementations, tests, and recent history. Do not infer behavior from filenames.
3. Read the explicit eight-field handoff from the approved product requirements workflow when supplied. Require `requirements_path`, expected topic, and expected scope as independent inputs; do not infer them from PRD contents or its filename. The expected topic must be a non-empty, non-reserved kebab-case stable topic; `null`, `unknown`, and `pending` are invalid inputs and block the gate.
4. Run `python3 <this-skill-directory>/scripts/inspect_product_requirements.py --repo-root <repository-root> --requirements <requirements-path> --expected-topic <expected-topic> --expected-scope <expected-scope>`. Treat a nonzero exit or unparseable JSON as unknown.
5. Classify the technical work using the repository's task grading rules. Split independent technical subsystems into separate spec → plan cycles only within the single approved PRD topic.
6. Separate repository-answerable technical facts from choices only the user can make.

## Clarify Material Decisions

Do not reopen approved product scope in this skill. Ask one to three questions per turn only when unresolved technical choices change public interfaces, data, permissions, security, consistency, migration, or another important design contract. Questions are independent only when every possible answer leaves every other question's applicability, options, meaning, priority, and necessity unchanged. Batch only independent questions and do not add a fourth substantive question. When one answer selects a later branch, ask only one decisive question. If the user supplies partial answers, preserve valid answers and reassess remaining dependencies. Use repository evidence for small technical details and record the assumption.

When choices remain unresolved, do not write or review either document, run document validation, or enter a later workflow stage in that turn. An expected nonblocking discovery or choice question with no damage, conflict, permission failure, capability gap, review blocker, or formal confirmation or approval is an `ordinary-clarification`. A spec approval request, document-stage checkpoint, blocked reply, routing transition, or progress-only update is not ordinary clarification.

An ordinary clarification does not load `review-and-handoff.md`. Build one complete compact renderer input directly from verified discovery state and invoke local `scripts/render_handoff.py` through a structured process API; do not inspect the renderer source to reconstruct its interface. Never use a shell heredoc or a temporary input file. If the available command interface exposes only a shell command, serialize the complete JSON first, shell-quote it as one inert argument to `printf '%s'`, and pipe only that byte string to the renderer; never interpolate individual user values into shell syntax. The top-level object has exactly `schema_version: 1`, `handoff_schema: workflow`, `view: compact`, `canonical`, `stage`, and `next_step`. Its complete `canonical` object has exactly these fields:

```text
requirements_path
requirements_topic
requirements_scope
requirements_understanding_confidence
requirements_understanding_confirmation
requirements_user_approval
requirements_independent_review
specification_gate
spec_path
spec_user_approval
spec_independent_review
plan_path
plan_review_status
implementation_gate
```

Preserve every verified upstream value. A non-reserved stable topic explicitly supplied by the user is reliable independently of a still-missing requirements path or scope; preserve that topic in canonical state instead of replacing it with `null`. When converting an upstream requirements snapshot, rename `understanding_confidence` to `requirements_understanding_confidence` and `understanding_user_confirmation` to `requirements_understanding_confirmation`. Use the canonical contract's truthful `null`, `unknown`, `pending`, `not-approved`, or `blocked` state for unavailable or not-started facts; never upgrade a gate. Before any spec exists, both spec approval fields are `pending`. A plan that does not exist or has not passed review always uses `plan_review_status: not-approved`; `pending` is not an allowed plan-review value. Keep `specification_gate` and `implementation_gate` blocked unless their complete approval truth tables are already verified. Set `stage` to `技术规格澄清` or `实施计划澄清` according to the actual discovery stage and set `next_step` to one verified, single-line action. Successful stdout is the entire three-line compact suffix. The renderer owns its exact Chinese labels and topic mapping; use no partial stdout. If invocation fails, reclassify the reply as blocked and then load the later review/handoff reference required for that blocked path.

Keep reliably selected explicit paths in the handoff even when a material content question blocks document creation. Normalize them to absolute paths and preserve their priority; only use `null` when the path itself is unresolved.

When the requirements path, expected topic, or expected scope is missing or multiple values remain plausible, do not select one. Keep the PRD gate blocked and do not create or materially modify a spec. Report unresolved paths as `null` and unresolved identity as `null` or `unknown` according to the handoff mapping.

When a real design choice exists, present two or three viable approaches with impact, risks, and a recommendation. When only one approach fits the evidence and constraints, state that directly instead of inventing alternatives.

## Resolve Document Paths

- An explicit user path wins when it is valid. Resolve a relative explicit path against the working directory.
- Otherwise use `docs/specs/YYYY-MM-DD-<topic>-design.md` and `docs/plans/YYYY-MM-DD-<topic>.md`.
- Use the expected stable topic from the approved requirements handoff. Never derive it from a PRD filename or silently replace it.
- Preserve each reliable default absolute path in the handoff before the spec or plan exists. Use `null` only when a single path cannot be selected reliably.
- Do not overwrite an existing document without explicit authorization. Resume it only when the user identifies it as the current document.
- Keep links written inside versioned documents repository-relative. Report selected documents with normalized absolute paths in the handoff.

## Bound Scope

The planning workflow may read and write planning documents and run read-only or document-focused checks. It does not authorize target implementation, commits, installation, publication, deployment, or other external-state changes.
