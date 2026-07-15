# Discovery and Clarification

## Establish Evidence

1. Read every session-supplied rule. Discover filesystem `AGENTS.md` or `CLAUDE.md` from the repository root to the working directory, outermost to innermost. Never recursively search above the repository root.
2. Inspect repository status, relevant documentation, existing implementations, tests, and recent history. Do not infer behavior from filenames.
3. Classify scope using the repository's task grading rules. Split independent subsystems into separate spec → plan cycles.
4. Separate repository-answerable facts from choices only the user can make.

## Clarify Material Decisions

Ask one question at a time only when the answer changes scope, public behavior, data, permissions, security, consistency, or another important contract. Use repository evidence for small technical details and record the assumption.

When such a choice remains unresolved, ask one material question. Do not write or review either document, run document validation, or enter a later workflow stage in that turn. Immediately end the reply with the fixed handoff record from `review-and-handoff.md`.

Keep reliably selected explicit paths in the handoff even when a material content question blocks document creation. Normalize them to absolute paths and preserve their priority; only use `null` when the path itself is unresolved.

When multiple topics remain equally plausible, do not select a topic or document path. Report both `spec_path` and `plan_path` as `null` until the user chooses.

When a real design choice exists, present two or three viable approaches with impact, risks, and a recommendation. When only one approach fits the evidence and constraints, state that directly instead of inventing alternatives.

## Resolve Document Paths

- An explicit user path wins when it is valid. Resolve a relative explicit path against the working directory.
- Otherwise use `docs/specs/YYYY-MM-DD-<topic>-design.md` and `docs/plans/YYYY-MM-DD-<topic>.md`.
- Derive one stable kebab-case topic from the approved scope. Ask when multiple topics remain equally plausible.
- Do not overwrite an existing document without explicit authorization. Resume it only when the user identifies it as the current document.
- Keep links written inside versioned documents repository-relative. Report selected documents with normalized absolute paths in the handoff.

## Bound Scope

The planning workflow may read and write planning documents and run read-only or document-focused checks. It does not authorize target implementation, commits, installation, publication, deployment, or other external-state changes.
