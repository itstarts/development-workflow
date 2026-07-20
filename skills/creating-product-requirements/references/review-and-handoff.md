# Review and Handoff

## Review Sequence

Self-review the PRD, then dispatch a fresh read-only reviewer that did not write it. Give the reviewer the request, confirmed requirements-understanding summary, applicable rules, current PRD, and necessary repository evidence without an expected verdict or author defense. For an incremental PRD, also give the reviewer the approved baseline PRD and require checks that the new document identifies the baseline, does not repeat the complete baseline, and contains no product behavior outside the confirmed summary.

Require findings ordered by severity, open questions, verification gaps, and one final verdict. Accept only `APPROVED`, `CHANGES_REQUESTED`, or `BLOCKED`. Fix every finding and re-review the latest file. After `APPROVED`, the main agent records a generic reviewer role and date. Independent approval does not equal user approval; the user explicitly approves the current PRD only after being directed to that reviewed file.

## State Mapping and Invalidation

Use `pending` when a confirmation or approval has not happened. Use `unknown` for an existing file whose relevant metadata is missing, unreadable, unsupported, duplicate, conflicting, or cannot be tied to the current version. Preserve a reliably selected path even when content state is unknown.

A material change to PRD meaning must reset independent review and user approval to pending, remove stale reviewer identity, and remove all related approval and review dates. A material route change, including a change between `standard` and `full` or a risk-fact change that crosses that boundary, must also reset independent review and user approval. If it also changes the confirmed summary, reset understanding confirmation, reassess confidence truthfully from 0 through 100, and repeat summary confirmation. A confidence score at or above 95 does not replace a pending confirmation.

An approved baseline and its incremental PRD retain separate lifecycle states. Creating, reviewing, approving, invalidating, or handing off the increment does not rewrite the baseline's metadata. The canonical handoff always describes the current increment when that is the document under review.

For a read-only handoff check, do not re-litigate the content quality of a PRD whose current metadata is complete, reliable, and approved. Report specification_gate open when every recorded gate is satisfied. If new evidence requires a content change, report that separately; change the file and reset approvals only through the material change workflow rather than silently overturning valid approval metadata.

## Canonical Handoff

Build and validate this canonical English snapshot first. It remains the machine-authoritative requirements handoff:

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

The alternatives are reference-only; select exactly one value per field. Open the gate only when the PRD exists and confidence is at least 95, summary confirmation is approved, metadata is reliable, and both document approvals are approved. Keep this canonical English snapshot internal; do not print it as a second user-visible status block. The route is not a ninth requirements field: pass the route handoff separately, while its `workflow_route` and risk facts remain recoverable from `## 工作流分流` in the approved PRD.

Do not reverse-parse the Chinese view into canonical state. A legacy English handoff remains valid input and follows the same validation rules.

Whenever a topic is known, report the same non-reserved lowercase ASCII kebab-case topic used by the confirmed summary and PRD frontmatter. `null`, `unknown`, and `pending` are reserved and cannot be topic values.

## Reply Classification and User-Visible View

Classify each reply before rendering:

- `ordinary-clarification`: an expected nonblocking discovery or choice question with no formal confirmation or approval. Invoke `scripts/render_handoff.py` with `handoff_schema: requirements`, `view: compact`, the complete canonical object, a verified `stage`, and a verified `next_step`.
- `checkpoint`: a pause or recovery point, requirements-understanding summary confirmation, PRD approval request, completed document stage, or downstream capability selection. Invoke the same local script with `view: full`, `stage: null`, and `next_step: null`.
- `blocked`: a deterministic file, metadata, permission, reviewer, tool, reference, renderer, or capability problem that prevents progress. Use `full` when canonical state can be rendered; renderer failure itself uses its deterministic error and no partial status.

A progress-only update is not an ordinary clarification. Conservatively use full when the reply cannot be classified reliably. The local renderer validates canonical field shape, gates, mappings, strict UTF-8 JSON, and the selected view; invoke it through a structured argument/process API, use only successful stdout, and never import a sibling skill copy.

When no downstream transition occurs and the reply is a checkpoint, blocked result, approval request, document-stage completion, progress-only update, or conservative fallback, it ends with one authoritative Chinese eight-field view in this exact order:

```text
需求文档：<absolute-path | 未确定>
需求主题：<stable-kebab-topic | 未确定 | 未知>
需求范围：<产品 | 阶段 | 功能 | 未确定 | 未知>
需求理解置信度：<integer-0-through-100 | 未知>
需求理解确认：<待确认 | 已确认 | 未知>
需求文档用户批准：<待批准 | 已批准 | 未知>
需求文档独立评审：<待评审 | 已通过 | 未知>
技术规格门禁：<未开放 | 已开放>
```

Render the actual view as plain text, never as a Markdown code fence. Use the full-width colon shown above, no list marker or leading whitespace, and no content after the final line. Do not print the canonical English block or another Chinese status block. Explanatory prose must not repeat a Chinese field label followed by `：`.

For `ordinary-clarification`, successful renderer stdout is exactly three consecutive plain-text lines with no blank line, list marker, leading whitespace, full handoff field, or trailing content:

```text
当前阶段：<需求澄清>
主题：<stable-kebab-topic | 未确定 | 未知>
下一步：<one verified action>
```

Map values by field context:

- `requirements_scope`: `product` → `产品`; `phase` → `阶段`; `feature` → `功能`; `null` → `未确定`; `unknown` → `未知`.
- `understanding_user_confirmation`: `pending` → `待确认`; `approved` → `已确认`; `unknown` → `未知`.
- `requirements_user_approval`: `pending` → `待批准`; `approved` → `已批准`; `unknown` → `未知`.
- `requirements_independent_review`: `pending` → `待评审`; `approved` → `已通过`; `unknown` → `未知`.
- `specification_gate`: `blocked` → `未开放`; `open` → `已开放`.
- `requirements_topic` with `unknown` → `未知`; `requirements_scope` with `unknown` → `未知`; `understanding_confidence` with `unknown` → `未知`; `understanding_user_confirmation` with `unknown` → `未知`; `requirements_user_approval` with `unknown` → `未知`; `requirements_independent_review` with `unknown` → `未知`.
- `requirements_path: null` → `需求文档：未确定`; `requirements_topic: null` → `需求主题：未确定`.
- Preserve a non-null path, stable topic, and integer confidence exactly; do not translate or normalize them.

Pre-render the full Chinese view from the frozen canonical English snapshot before selecting a downstream capability. Validate the field count, field order, exact labels, and that every mapping is complete and unique. The view is presentation only and never changes approval or gate state.

If pre-rendering fails because a valid canonical value has no mapping, mappings conflict, or the view is incomplete, preserve the canonical snapshot and report a concise deterministic blocker. Do not emit a partial Chinese view, do not fall back to the English user-visible handoff, and do not select the downstream capability. After the mapping defect is fixed, retry from the preserved canonical snapshot rather than chat memory.

## Approved Transition

After writing and validating user approval, freeze the complete canonical English eight-field handoff and pre-render its Chinese view. Only when `specification_gate` is `open` and that view passes validation, select the runtime-exposed skill capability named `creating-development-specs-and-plans` in the same session. Pass the absolute `requirements_path`, exact `requirements_topic`, exact `requirements_scope`, the complete canonical English handoff, and the separate route handoff as explicit input. Do not ask the user to repeat those values.

The PRD workflow does not create the design spec. Do not read sibling skill source, do not inspect sibling skill installation directories, and do not infer an installation path. If the named capability is unavailable, report the capability gap and end with the pre-rendered truthful Chinese eight-field view.

On a successful downstream transition, do not append a separate competing eight-field block. The downstream canonical fourteen-field handoff preserves the validated canonical eight fields as its prefix, while the final response ends with that workflow's single Chinese fourteen-field view. If canonical validation fails before the downstream workflow is selected, remain in the PRD workflow and render the truthful Chinese view when its mapping is valid. After the downstream workflow has been selected, its response contract owns later validation failures.

## Runtime Boundary

- Do not create a design spec.
- Do not create an implementation plan.
- Do not implement target code.
- Select a downstream workflow only through the runtime-exposed skill capability and only after the approved transition gate opens.
- Do not read sibling skill source or inspect sibling skill installation directories.
- Do not create or manage a user-visible task/thread.
- Do not install into a real skill home.
- Do not commit.
- Do not push, merge, rebase, tag, or release.
- Do not change external state.
