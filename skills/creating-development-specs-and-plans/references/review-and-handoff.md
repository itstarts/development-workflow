# Review and Handoff

## Specification Review

Dispatch a fresh read-only spec reviewer that did not write the spec. Give it the user request, applicable rules, current spec, and relevant repository evidence. Do not provide an expected verdict, author defense, or requested approval.

Require findings ordered by severity, open questions, verification gaps, and one final verdict. Fix every finding and re-review the latest file until it is approved or genuinely blocked. The reviewer stays read-only; after approval of the latest file, the main agent updates independent-review metadata. A reviewer verdict does not equal user approval. Ask the user only after independent spec review passes; the user explicitly approves the current written spec before creating the plan. A material spec change invalidates approval from both the independent reviewer and the user, then restarts both gates.

## Plan Review

Dispatch a fresh read-only plan reviewer that did not write the plan. Give it the approved spec, applicable rules, current plan, relevant repository evidence, and available verification evidence. Require coverage, path, interface, ordering, testing, documentation, and validation checks. Include security review only when the spec contains a real security, permission, or sensitive-data boundary.

Fix every finding and re-review the latest plan. Set `review_status: approved` only after an explicit approval with no unresolved blocking finding or verification gap. When a reviewer is unavailable, keep the document pending; pending maps to not-approved. Unreliable review metadata maps to unknown.

## Fixed Handoff Record

Every user-facing response, including a clarification question or blocked response, must end with the complete six-field record below. Use absolute paths and do not omit fields whose value is pending, unknown, or null:

```text
spec_path: <absolute path> | null
spec_user_approval: pending | approved
spec_independent_review: pending | approved
plan_path: <absolute path> | null
plan_review_status: not-approved | approved | unknown
implementation_gate: blocked | open
```

The `|` entries above are reference-only alternatives. In an actual handoff, emit exactly one allowed value for each field and never copy the `|` or unused alternatives.

Open the gate only when the current written spec has explicit user approval and the current plan has real independent approval.

The state mapping is `plan_path: null maps to not-approved` because no plan exists. Use `unknown` only for an existing plan whose review metadata is missing, malformed, duplicate, conflicting, or unreadable. Open the gate only when spec independent review is approved, the user approved that reviewed spec, and plan independent review is approved.

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
