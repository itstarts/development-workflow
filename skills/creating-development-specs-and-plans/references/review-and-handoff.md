# Review and Handoff

## Requirements Gate

Run `inspect_product_requirements.py` before creating or materially modifying a spec and again before reporting either downstream gate open. Use the explicit repository root, requirements path, expected topic, and expected scope. Do not call a sibling skill or infer the expected values from the document being checked.

Map reliable `pending` or confidence below 95 to `not-approved`. Map a missing path, missing field, invalid value, duplicate, conflict, mismatch, unreadable file, non-Git root, out-of-root path, nonzero inspector exit, or unparseable output to `unknown`. Both states block specification and implementation. Only the inspector's reliable `approved` result opens `specification_gate`.

After this workflow has been selected from an upstream eight-field handoff, it owns the downstream response contract. If PRD revalidation fails, emit the complete fourteen-field handoff rather than falling back to eight fields. Map unreliable requirements values to `unknown` or `not-approved` as defined above, preserve reliably selected spec and plan paths, keep `specification_gate: blocked` and `implementation_gate: blocked`, and report the validation failure.

## Specification Review

Dispatch a fresh read-only spec reviewer that did not write the spec. Give it the user request, applicable rules, current spec, and relevant repository evidence. Do not provide an expected verdict, author defense, or requested approval.

When the reviewer is known to be unavailable, do not dispatch and do not wait. Keep independent review pending, report the blocked gate, and stop after the fixed handoff. Do not probe a known-unavailable channel merely to manufacture an attempted review.

Require findings ordered by severity, open questions, verification gaps, and one final verdict. Fix every finding and re-review the latest file until it is approved or genuinely blocked. The reviewer stays read-only; after approval of the latest file, the main agent updates independent-review metadata. A reviewer verdict does not equal user approval. Ask the user only after independent spec review passes; the user explicitly approves the current written spec before creating the plan. A material spec change invalidates approval from both the independent reviewer and the user, then restarts both gates.

## Plan Review

Dispatch a fresh read-only plan reviewer that did not write the plan. Give it the approved spec, applicable rules, current plan, relevant repository evidence, and available verification evidence. Require coverage, path, interface, ordering, testing, documentation, and validation checks. Include security review only when the spec contains a real security, permission, or sensitive-data boundary.

Apply the same known-unavailable rule: do not dispatch, do not wait, keep the plan pending, and never replace the missing review with author self-review.

Fix every finding and re-review the latest plan. Set `review_status: approved` only after an explicit approval with no unresolved blocking finding or verification gap. When a reviewer is unavailable, keep the document pending; pending maps to not-approved. Unreliable review metadata maps to unknown.

## Reply Classification

Classify each reply before rendering:

- `ordinary-clarification`: an expected nonblocking technical discovery or choice question. Invoke `scripts/render_handoff.py` with `handoff_schema: workflow`, `view: compact`, the complete canonical object, the verified clarification `stage`, and verified `next_step`.
- `checkpoint`: a pause or recovery point, spec approval request, plan approval or document-stage completion, implementation approval handoff, or route selection. Invoke the same local script with `view: full`, `stage: null`, and `next_step: null`.
- `blocked`: a deterministic requirements, document, metadata, permission, reviewer, tool, reference, renderer, or capability problem that prevents progress. Use `full` when canonical state can be rendered; renderer failure itself emits no partial status.
- `routing`: every automatic downstream route uses `full`.

A progress-only update is not ordinary clarification. Conservatively use full when classification is uncertain. Invoke the renderer through a structured process API, trust only exit-code-zero stdout, never import a sibling skill copy, and preserve canonical English state on any failure.

## Fixed Handoff Record

Maintain the following canonical English snapshot as the machine-readable authority. It also preserves the legacy English handoff input contract. Use absolute paths and do not omit fields whose value is pending, unknown, or null:

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

The `|` entries above are reference-only alternatives. In a canonical handoff, emit exactly one allowed value for each field and never copy the `|` or unused alternatives. Do not reverse-parse the Chinese view into canonical state; always render it forward from the preserved canonical English snapshot.

Every checkpoint, blocked response, progress-only update, approval request, document-stage completion, conservative fallback, and routing response must end with the complete fourteen-field record as one authoritative Chinese fourteen-field view in this exact order and with these exact full-width-colon labels. Renderer failure is the explicit fail-closed exception defined below.

```text
需求文档：<绝对路径> | 未确定
需求主题：<稳定主题> | 未确定 | 未知
需求范围：产品 | 阶段 | 功能 | 未确定 | 未知
需求理解置信度：<0 到 100 的整数> | 未知
需求理解确认：待确认 | 已确认 | 未知
需求文档用户批准：待批准 | 已批准 | 未知
需求文档独立评审：待评审 | 已通过 | 未知
技术规格门禁：未开放 | 已开放
技术规格：<绝对路径> | 未确定
技术规格用户批准：待批准 | 已批准
技术规格独立评审：待评审 | 已通过
实施计划：<绝对路径> | 尚未创建
计划评审状态：未开始 | 未通过 | 已通过 | 未知
实施门禁：未开放 | 已开放
```

This second block is a schema reference, not a literal reply. In an actual response, emit one allowed value per field, never copy the `|` alternatives, and render the authoritative Chinese view as plain text, not a Markdown code fence.

For `ordinary-clarification`, successful renderer stdout is exactly three consecutive plain-text lines with no blank line, list marker, leading whitespace, full handoff field, or trailing content:

```text
当前阶段：<技术规格澄清 | 实施计划澄清>
主题：<stable-topic | 未确定 | 未知>
下一步：<one verified action>
```

Apply mappings by field context rather than by globally replacing English tokens:

- `requirements_path: null` → `需求文档：未确定`; otherwise preserve the absolute path exactly.
- Preserve a non-null `requirements_topic` exactly. For `requirements_topic`, `null` → `未确定` and `unknown` → `未知`.
- For `requirements_scope`, `product` → `产品`, `phase` → `阶段`, `feature` → `功能`, `null` → `未确定`, and `unknown` → `未知`.
- Preserve an integer `requirements_understanding_confidence` exactly; for `requirements_understanding_confidence`, `unknown` → `未知`.
- For `requirements_understanding_confirmation`, `pending` → `待确认`, `approved` → `已确认`, and `unknown` → `未知`.
- For `requirements_user_approval`, `pending` → `待批准`, `approved` → `已批准`, and `unknown` → `未知`.
- For `requirements_independent_review`, `pending` → `待评审`, `approved` → `已通过`, and `unknown` → `未知`.
- For both gates, `blocked` → `未开放` and `open` → `已开放`.
- `spec_path: null` → `技术规格：未确定`; otherwise preserve the absolute path exactly.
- `spec_user_approval` and `spec_independent_review` accept only `pending | approved`. For `spec_user_approval`, `pending` → `待批准` and `approved` → `已批准`. For `spec_independent_review`, `pending` → `待评审` and `approved` → `已通过`.
- `plan_path: null` → `实施计划：尚未创建`; otherwise preserve the absolute path exactly.
- `plan_path: null` + `plan_review_status: not-approved` → `计划评审状态：未开始`.
- existing `plan_path` + `plan_review_status: not-approved` → `计划评审状态：未通过`.
- existing `plan_path` + `plan_review_status: approved` → `计划评审状态：已通过`.
- existing `plan_path` + `plan_review_status: unknown` → `计划评审状态：未知`.

Do not repeat any fixed handoff field label with a colon outside the one authoritative Chinese handoff block. In explanatory prose, describe gates and review states without reproducing a fixed label.

Render the actual fourteen-field handoff as plain text, not a Markdown code fence. Its `实施门禁` value must be the last non-empty line of the response.

Open `specification_gate` only for the current reliably approved PRD. Open `implementation_gate` only when that requirements gate still remains open, the current written spec has reliable independent review and explicit user approval, and the current plan has real independent approval.

The state mapping is `plan_path: null maps to not-approved` because no plan exists. Use `unknown` only for an existing plan whose review metadata is missing, malformed, duplicate, conflicting, or unreadable. Open the gate only when spec independent review is approved, the user approved that reviewed spec, and plan independent review is approved.

Preserve a reliably selected path even if its document state is unknown. Use `null` only when no single path is reliably selected. For PRD metadata, do not replace missing or invalid content with pending. If a material PRD change invalidates the requirements gate, `implementation_gate` is blocked regardless of older spec or plan metadata.

When no spec exists, report both spec approval fields as `pending`. Their allowed values are only `pending` and `approved`; do not emit `unknown` for these two fields.

## Chinese View Validation

After freezing the canonical English snapshot, pre-render the complete Chinese view before selecting any routing capability and before session routing. Validate its field count is exactly fourteen, its field order and labels exactly match the schema above, every value comes from the matching canonical field, and each contextual mapping is complete and unique.

If validation fails, keep the preserved canonical snapshot as the authority and emit a deterministic Chinese blocker. The blocker must identify the unmapped field or failed integrity condition. This exceptional reply does not append a status view. Do not emit a partial Chinese view, do not emit a mixed-language view, do not fall back to the English user-visible handoff, do not select the routing capability, and stop the current automatic handoff. Never invent a translated state or silently upgrade a gate. Only after the mapping is corrected, retry from the preserved canonical snapshot or rebuild it from the current canonical source if that source changed.

## Approved Routing Transition

When every gate is satisfied, revalidate the PRD, spec, plan, and validate the complete fourteen-field handoff. Freeze one snapshot before routing, pre-render and validate its Chinese view, and only then select the runtime-exposed skill capability named `generating-development-prompts` in the same session when the canonical snapshot has `implementation_gate: open`.

Do not read sibling skill source, do not inspect sibling skill installation directories, and do not infer a fixed local path. If the named capability is unavailable, report the capability gap and end with the same fourteen-field snapshot rendered as the authoritative Chinese view. When routing succeeds, place the routing result and any generated prompt before the handoff, then end with that same Chinese view. The routing workflow must not change document approval state.

## Runtime Boundary

- Do not implement target code.
- Select session routing only through the runtime-exposed skill capability after the approved routing transition gate opens.
- Do not read sibling skill source or inspect sibling skill installation directories.
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
