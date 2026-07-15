# Review and Handoff

## Review Sequence

Self-review the PRD, then dispatch a fresh read-only reviewer that did not write it. Give the reviewer the request, confirmed requirements-understanding summary, applicable rules, current PRD, and necessary repository evidence without an expected verdict or author defense.

Require findings ordered by severity, open questions, verification gaps, and one final verdict. Accept only `APPROVED`, `CHANGES_REQUESTED`, or `BLOCKED`. Fix every finding and re-review the latest file. After `APPROVED`, the main agent records a generic reviewer role and date. Independent approval does not equal user approval; the user explicitly approves the current PRD only after being directed to that reviewed file.

## State Mapping and Invalidation

Use `pending` when a confirmation or approval has not happened. Use `unknown` for an existing file whose relevant metadata is missing, unreadable, unsupported, duplicate, conflicting, or cannot be tied to the current version. Preserve a reliably selected path even when content state is unknown.

A material change to PRD meaning must reset independent review and user approval to pending, remove stale reviewer identity, and remove all related approval and review dates. If it also changes the confirmed summary, reset understanding confirmation, reassess confidence truthfully from 0 through 100, and repeat summary confirmation. A confidence score at or above 95 does not replace a pending confirmation.

For a read-only handoff check, do not re-litigate the content quality of a PRD whose current metadata is complete, reliable, and approved. Report specification_gate open when every recorded gate is satisfied. If new evidence requires a content change, report that separately; change the file and reset approvals only through the material change workflow rather than silently overturning valid approval metadata.

## Fixed Handoff

Every user-facing response, including a question or blocked response, must end with exactly one value for each field in this order:

```text
requirements_path: <absolute-path> | null
requirements_topic: <stable-kebab-topic> | null | unknown
requirements_scope: product | phase | feature | null | unknown
understanding_confidence: <integer-0-through-100> | unknown
understanding_user_confirmation: pending | approved | unknown
requirements_user_approval: pending | approved | unknown
requirements_independent_review: pending | approved | unknown
specification_gate: blocked | open
```

The alternatives are reference-only; never copy unused alternatives or the separator. Open the gate only when the PRD exists and confidence is at least 95, summary confirmation is approved, metadata is reliable, and both document approvals are approved.

Whenever a topic is known, report the same non-reserved lowercase ASCII kebab-case topic used by the confirmed summary and PRD frontmatter. `null`, `unknown`, and `pending` are reserved and cannot be topic values.

## Runtime Boundary

- Do not create a design spec.
- Do not create an implementation plan.
- Do not implement target code.
- Do not call sibling skills.
- Do not create or manage a user-visible task/thread.
- Do not install into a real skill home.
- Do not commit.
- Do not push, merge, rebase, tag, or release.
- Do not change external state.
