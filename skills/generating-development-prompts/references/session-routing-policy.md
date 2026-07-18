# Session Routing Policy

## Inputs and Entry Gates

For automatic routing, require one verified fourteen-field snapshot whose `implementation_gate: open`. Use the discovery JSON, current conversation context, upstream snapshot, permissions, tools, and Agent capabilities as separate evidence sources. Validate and freeze the canonical English snapshot before routing and do not change document approval state.

An explicit prompt request is compatible with plan review `not-approved` or `unknown`. Render the prompt with its truthful implementation gate. Do not fabricate requirements fields, approval states, or a fourteen-field snapshot when the manual request has no verified upstream handoff.

## Canonical Snapshot and Chinese View

For every automatic route, pass the frozen canonical object exactly once to this skill's local `scripts/render_handoff.py` with `handoff_schema: workflow`, `view: full`, `stage: null`, and `next_step: null` before choosing a route. This handoff renderer is the sole presentation validator for field count, field order, labels, contextual mappings, gate consistency, and exact output bytes. Freeze only exit-code-zero `render_handoff.py` stdout as the authoritative user-visible suffix. Do not manually translate or pre-render a Chinese view or import a sibling renderer. Do not reverse-parse display text or route after any renderer error or partial output.

The canonical English snapshot remains the only machine authority and the compatible legacy input contract:

```text
requirements_path: <absolute-or-repository path> | null
requirements_topic: <stable-topic> | null | unknown
requirements_scope: product | phase | feature | null | unknown
requirements_understanding_confidence: <integer-0-through-100> | unknown
requirements_understanding_confirmation: pending | approved | unknown
requirements_user_approval: pending | approved | unknown
requirements_independent_review: pending | approved | unknown
specification_gate: blocked | open
spec_path: <absolute-or-repository path> | null
spec_user_approval: pending | approved
spec_independent_review: pending | approved
plan_path: <absolute-or-repository path> | null
plan_review_status: not-approved | approved | unknown
implementation_gate: blocked | open
```

The canonical block above is a machine schema reference. In an actual automatic reply, do not expose it as user-visible output and do not maintain a second Chinese mapping table in this reference. A handoff renderer failure is the only explicit exception to the automatic status-suffix rule. On nonzero exit, invalid machine-readable stderr, or missing complete stdout, preserve the canonical snapshot and emit a deterministic Chinese blocker based on the renderer's machine-readable stderr. The blocker identifies the failed canonical field or integrity condition, does not append a status view, does not choose any route, does not invoke `render_prompt.py`, and stops the current automatic routing. Retry the one handoff-renderer invocation only after the canonical source or renderer defect is corrected.

## Choose One Result

Apply this priority without a score or threshold:

1. Do not start automatic routing when the fourteen fields are incomplete, conflicting, unverified, or `implementation_gate` is not `open`. An explicit prompt request may still follow the manual compatibility rule.
2. Return `blocked` only for deterministic evidence that applies across sessions: a required document is missing or unreadable in every session, an approval gate cannot be opened by changing sessions, a repository or user permission forbids a required action in both sessions, the platform explicitly states the target session lacks a required capability, or the current runtime can verify that same new-session boundary.
3. When evidence is insufficient, conflicting, or cannot reliably compare both sessions, return `new-session` and identify the uncertainty.
4. When only the current session lacks a permission, tool, or Agent capability, return `new-session`. Do not infer that a new session has the same limitation without session-independent or verified target-session evidence.
5. Return `new-session` when the current conversation has unrelated topics, unresolved conflict, substantial context burden, or when scope, risk, complexity, or duration materially benefits from isolation.
6. Return `current-session` only when the context is complete and consistent, scope is controlled, repository and approvals are clear, and the required permissions, tools, and Agent capabilities are available.

Every result names the actual evidence that selected it. Do not claim `current-session` without positive evidence.

## Output Rules

- `current-session`: report the result and reasons, wait for explicit implementation approval, and do not render a prompt.
- `new-session`: report the result and reasons, then render one complete prompt.
- `blocked`: report the result and cross-session blocker; do not render automatically. A later explicit prompt request may render a prompt that preserves the blocker.

For automatic routing after successful handoff rendering, `current-session`, `new-session`, and `blocked` all end with the same renderer-validated Chinese view: the frozen `render_handoff.py` stdout. The handoff is plain text: never wrap the handoff in a code fence. Its final non-empty line is `实施门禁：<renderer value>`. Place the route and reasons before it. For `new-session`, place `render_prompt.py` stdout before `render_handoff.py` stdout and outside the dynamic fence; do not put any Chinese status line in the prompt renderer body. Do not duplicate or remap the view after routing, and do not place content after it.

A manual prompt request without a verified upstream snapshot returns renderer stdout verbatim on success and does not fabricate or append a status view.

Do not repeat any fixed handoff field label with a colon outside the one authoritative fourteen-field block. In route explanations, describe gates and review states without reproducing a `field_name:` label.
