# Review and Handoff

## Requirements Gate

Run `inspect_product_requirements.py` before creating or materially modifying a spec and again before reporting either downstream gate open. Use the explicit repository root, requirements path, expected topic, and expected scope. Do not call a sibling skill or infer the expected values from the document being checked.

Map reliable `pending` or confidence below 95 to `not-approved`. Map a missing path, missing field, invalid value, duplicate, conflict, mismatch, unreadable file, non-Git root, out-of-root path, nonzero inspector exit, or unparseable output to `unknown`. Both states block specification and implementation. Only the inspector's reliable `approved` result opens `specification_gate`.

## Specification Review

Dispatch a fresh read-only spec reviewer that did not write the spec. Give it the user request, applicable rules, current spec, and relevant repository evidence. Do not provide an expected verdict, author defense, or requested approval.

When the reviewer is known to be unavailable, do not dispatch and do not wait. Keep independent review pending, report the blocked gate, and stop after the fixed handoff. Do not probe a known-unavailable channel merely to manufacture an attempted review.

Require findings ordered by severity, open questions, verification gaps, and one final verdict. Fix every finding and re-review the latest file until it is approved or genuinely blocked. The reviewer stays read-only; after approval of the latest file, the main agent updates independent-review metadata. A reviewer verdict does not equal user approval. Ask the user only after independent spec review passes; the user explicitly approves the current written spec before creating the plan. A material spec change invalidates approval from both the independent reviewer and the user, then restarts both gates.

## Plan Review

Dispatch a fresh read-only plan reviewer that did not write the plan. Give it the approved spec, applicable rules, current plan, relevant repository evidence, and available verification evidence. Require coverage, path, interface, ordering, testing, documentation, and validation checks. Include security review only when the spec contains a real security, permission, or sensitive-data boundary.

Apply the same known-unavailable rule: do not dispatch, do not wait, keep the plan pending, and never replace the missing review with author self-review.

Fix every finding and re-review the latest plan. Set `review_status: approved` only after an explicit approval with no unresolved blocking finding or verification gap. When a reviewer is unavailable, keep the document pending; pending maps to not-approved. Unreliable review metadata maps to unknown.

## Fixed Handoff Record

Every user-facing response, including a clarification question or blocked response, must end with the complete fourteen-field record below. Use absolute paths and do not omit fields whose value is pending, unknown, or null:

```text
requirements_path: <absolute path> | null
requirements_topic: <stable-topic> | null | unknown
requirements_scope: product | phase | feature | null | unknown
requirements_understanding_confidence: <integer-0-through-100> | unknown
requirements_understanding_confirmation: pending | approved | unknown
requirements_user_approval: pending | approved | unknown
requirements_independent_review: pending | approved | unknown
specification_gate: blocked | open
spec_path: <absolute path> | null
spec_user_approval: pending | approved
spec_independent_review: pending | approved
plan_path: <absolute path> | null
plan_review_status: not-approved | approved | unknown
implementation_gate: blocked | open
```

The `|` entries above are reference-only alternatives. In an actual handoff, emit exactly one allowed value for each field and never copy the `|` or unused alternatives.

Open `specification_gate` only for the current reliably approved PRD. Open `implementation_gate` only when that requirements gate still remains open, the current written spec has reliable independent review and explicit user approval, and the current plan has real independent approval.

The state mapping is `plan_path: null maps to not-approved` because no plan exists. Use `unknown` only for an existing plan whose review metadata is missing, malformed, duplicate, conflicting, or unreadable. Open the gate only when spec independent review is approved, the user approved that reviewed spec, and plan independent review is approved.

Preserve a reliably selected path even if its document state is unknown. Use `null` only when no single path is reliably selected. For PRD metadata, do not replace missing or invalid content with pending. If a material PRD change invalidates the requirements gate, `implementation_gate` is blocked regardless of older spec or plan metadata.

When no spec exists, report both spec approval fields as `pending`. Their allowed values are only `pending` and `approved`; do not emit `unknown` for these two fields.

## Runtime Boundary

- Do not implement target code.
- Do not call sibling skills.
- Do not create or manage a user-visible task/thread.
- Do not commit.
- Do not push.
- Do not merge.
- Do not rebase.
- Do not tag.
- Do not release.
- Do not install into the real CODEX_HOME.
- Do not change external state.

Report a blocked state truthfully when any required authority, evidence, path, or reviewer is missing.
