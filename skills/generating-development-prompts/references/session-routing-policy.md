# Session Routing Policy

## Inputs and Entry Gates

For automatic routing, require one verified fourteen-field snapshot whose `implementation_gate: open`. Use the discovery JSON, current conversation context, upstream snapshot, permissions, tools, and Agent capabilities as separate evidence sources. Validate and freeze the canonical English snapshot before routing and do not change document approval state.

An explicit prompt request is compatible with plan review `not-approved` or `unknown`. Render the prompt with its truthful implementation gate. Do not fabricate requirements fields, approval states, or a fourteen-field snapshot when the manual request has no verified upstream handoff.

## Canonical Snapshot and Chinese View

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

Pre-render this authoritative Chinese view from the frozen canonical English snapshot:

```text
需求文档：<路径> | 未确定
需求主题：<稳定主题> | 未确定 | 未知
需求范围：产品 | 阶段 | 功能 | 未确定 | 未知
需求理解置信度：<0 到 100 的整数> | 未知
需求理解确认：待确认 | 已确认 | 未知
需求文档用户批准：待批准 | 已批准 | 未知
需求文档独立评审：待评审 | 已通过 | 未知
技术规格门禁：未开放 | 已开放
技术规格：<路径> | 未确定
技术规格用户批准：待批准 | 已批准
技术规格独立评审：待评审 | 已通过
实施计划：<路径> | 尚未创建
计划评审状态：未开始 | 未通过 | 已通过 | 未知
实施门禁：未开放 | 已开放
```

The two blocks above are schema references. In an actual automatic reply, do not expose the canonical English snapshot as user-visible output. Emit exactly one value per Chinese field, never copy `|` alternatives, and do not reverse-parse the Chinese view into machine state.

Apply values by field context:

- Preserve non-null paths, topic, and integer confidence exactly. Map requirements or spec path `null` and topic `null` to `未确定`; map plan path `null` to `尚未创建`.
- Map requirements scope `product | phase | feature | null | unknown` to `产品 | 阶段 | 功能 | 未确定 | 未知`.
- Map requirements understanding confirmation `pending | approved | unknown` to `待确认 | 已确认 | 未知`.
- Map requirements user approval `pending | approved | unknown` to `待批准 | 已批准 | 未知`.
- Map requirements independent review `pending | approved | unknown` to `待评审 | 已通过 | 未知`.
- Map spec user approval `pending | approved` to `待批准 | 已批准`; map spec independent review `pending | approved` to `待评审 | 已通过`. These spec fields do not accept `unknown`.
- Map both gates `blocked | open` to `未开放 | 已开放`.
- Map `plan_path: null` with `plan_review_status: not-approved` to `未开始`; for an existing plan map `not-approved | approved | unknown` to `未通过 | 已通过 | 未知`.

Before choosing a route and before invoking the renderer, validate that the Chinese view's field count is fourteen, field order and labels exactly match the schema, and every mapping is complete and unique. If validation fails, preserve the canonical snapshot and emit a deterministic Chinese blocker that identifies the unmapped field or failed integrity condition. Mapping failure is the only explicit exception to the status-suffix rule: the reply does not append a status view. Do not emit a partial, mixed, or English fallback block; do not choose any route; do not invoke the renderer; and stop the current automatic routing. Retry from the preserved canonical source only after the mapping is corrected.

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

For automatic routing after successful mapping validation, `current-session`, `new-session`, and `blocked` all end with the same prevalidated Chinese view derived from the frozen snapshot. The handoff is plain text: never wrap the handoff in a code fence. Its final non-empty line is `实施门禁：未开放 | 已开放` with the view's one actual value. Place the route and reasons before it. For `new-session`, place renderer stdout before the Chinese view and outside the dynamic fence; do not put any Chinese status line in the renderer body. Do not duplicate or remap the view after routing, and do not place content after it.

A manual prompt request without a verified upstream snapshot returns renderer stdout verbatim on success and does not fabricate or append a status view.

Do not repeat any fixed handoff field label with a colon outside the one authoritative fourteen-field block. In route explanations, describe gates and review states without reproducing a `field_name:` label.
