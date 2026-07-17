# Rule Candidates and Scope

## Completion Scan

Run one completion scan after implementation, affected documentation, and applicable validation, but before the final delivery. Use only current task evidence: the repository content actually read, the actual diff, validation results, confirmed corrections, and stable operating facts.

A candidate must be evidence-backed, reusable in future work, not merely a temporary task detail, and likely to reduce future repeated questions, mistakes, or validation cost. Reject results-only notes, guesses, personal temporary preferences, duplicates of an existing rule, and statements without a clear applicability boundary.

## Classification

Classify project commands, technology, directory or architecture boundaries, business constraints, and project-specific validation as a project candidate. Classify stable cross-project collaboration, engineering, safety, or validation principles as a global candidate. Attach the evidence and classification reason to every candidate. If the project/global classification remains uncertain, ask the user to choose the scope before constructing a write.

When `project_rules_check` is `declined`, discard project candidates without prompting, but a separate batch of qualified global candidates may still be shown once. Group candidates by target rather than prompting once per rule.

## Review Ordering

Project candidates must be written and verified before the repository final review when that review is required, so the rule change is part of the latest complete diff and affected validation. Project rule changes after review invalidate the prior review. Re-run the affected validation. The same review channel must re-review the latest complete diff.

Global candidates are outside the repository diff and may be handled after the repository final review as a separate approval and verification flow. If the target task does not require independent review, do not invent a review gate.

If there is no candidate after filtering, remain silent and produce no governance message, including no "no candidate" status, even if the user asks for confirmation. Do not create a marker file. Do not explain the omission or mention the refused marker in the ordinary delivery. Mark only that logical task's in-memory `completion_scan` as `completed` so other tasks and projects retain their own state.
