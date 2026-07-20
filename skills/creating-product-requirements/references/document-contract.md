# Product Requirements Document Contract

Use `assets/prd-template.md` for a full PRD and `assets/incremental-prd-template.md` for an incremental PRD. Replace every angle-bracket slot with current evidence and remove instructional slot text from the finished document.

Write the user-facing document title, section headings, explanatory prose, labels, and template-derived content in Chinese by default. New PRDs use the `chinese-current` frontmatter schema below. Paths, commands, API names, protocols, filenames, stable topics, ISO dates, confidence integers, reviewer roles, and canonical handoff identifiers retain their technical form.

The `topic` value is the same non-reserved lowercase ASCII kebab-case topic confirmed in the current requirements-understanding summary and emitted in the handoff. Do not translate, localize, title-case, or independently rename it when writing the PRD.

## Full and Incremental Documents

When no relevant approved baseline PRD exists, create a full PRD. When a relevant approved baseline PRD is verified, default to a separate incremental PRD. A user may explicitly request a consolidated replacement, but the current confirmed summary must cover that full replacement scope before the baseline can be changed.

An incremental PRD must:

- identify the repository-relative approved baseline path and state that unchanged baseline behavior remains in force;
- contain only the delta, affected context, non-goals, acceptance criteria, dependencies, risks, and handoff constraints present in the confirmed requirements-understanding summary;
- do not overwrite the baseline and do not repeat the complete baseline;
- retain the ordinary `chinese-current` frontmatter schema and canonical eight-field handoff, with the incremental document's own path, topic, scope, confidence, review, and approval state;
- start its own independent review and user approval as pending; baseline approval never carries forward to the increment.

Reference the baseline to establish document identity and inheritance. Within the confirmed delta, restate affected context when it materially improves clarity and use a reference when that is sufficient. There is no blanket preference for citation over restatement, but neither choice authorizes copying the complete baseline or adding behavior outside the confirmed summary.

There is no length, complexity, or review-cost ceiling. Do not switch an approved-baseline change to a full restatement, split one stable topic, or omit confirmed product behavior solely to reduce page count, authoring complexity, or review cost. Independent product topics still follow the ordinary one-topic rule.

## Required Product Content

For a full PRD, state the product problem, goals, non-goals, success measures, target users, user scenarios, scope, observable product requirements, business rules, product-visible error behavior, acceptance criteria, dependencies, risks, and assumptions. For an incremental PRD, state only the confirmed delta and the affected context required to interpret and verify it. Add performance, compatibility, privacy, accessibility, or other non-functional requirements only when they appear in the confirmed summary and affect product behavior.

When `routing-development-workflows` supplied a reliable route handoff, preserve it in the body section `## 工作流分流` using exactly one `workflow_route: standard | full` line and one `风险事实: <observed facts or none>` line. The alternatives are reference-only: a finished PRD contains one route. If the route is missing, duplicated, unsupported, conflicts with the separately supplied handoff, or its risk facts are unreliable, record `workflow_route: full` and the known uncertainty rather than inferring `standard`. This body section is recoverable workflow evidence; it is not product scope and does not add fields to frontmatter or the canonical eight-field handoff.

Record product-visible constraints without choosing a technical solution. Keep architecture, component design, API definitions, database schemas, migration design, code files, and implementation tasks out of the PRD. Move those concerns to the downstream technical specification.

## Frontmatter and Approval States

Write flat YAML frontmatter from byte zero. A new PRD can exist only after confidence is at least 95 and the current requirements-understanding summary is confirmed, so it begins with that confirmation approved while document approvals remain pending.

For a new `chinese-current` PRD, use exactly these semantic fields and representations:

| Canonical semantic key | Chinese key | Chinese value or format |
| --- | --- | --- |
| `document_type` | `文档类型` | `产品需求` |
| `topic` | `主题` | stable topic unchanged |
| `scope_type` | `范围类型` | `产品`、`阶段`、or `功能` |
| `understanding_confidence` | `理解置信度` | integer from 95 through 100 |
| `understanding_user_confirmation` | `需求理解确认` | `已确认` |
| `user_approval` | `用户批准` | `待批准` or `已批准` |
| `approved_at` | `批准日期` | ISO date, present only after user approval |
| `independent_review` | `独立评审` | `待评审` or `已通过` |
| `independent_reviewer` | `独立评审角色` | reviewer role unchanged, present only after review approval |
| `independent_reviewed_at` | `独立评审日期` | ISO date, present only after review approval |

`需求理解确认` records confirmation of the pre-document summary; it is not PRD approval. `独立评审` records a fresh reviewer verdict. `用户批准` records the user's explicit approval of the independently reviewed current file. Initial creation has `用户批准: 待批准` and `独立评审: 待评审` without approval, reviewer, or review dates. A real review approval changes only the same Chinese schema to `独立评审: 已通过` and adds `独立评审角色` plus `独立评审日期`. Explicit user approval changes only the same Chinese schema to `用户批准: 已批准` and adds `批准日期`.

An existing PRD that already uses the complete English keys and English values is `english-legacy`. Read, maintain, invalidate, approve, and re-review an existing `english-legacy` document using that same schema: keep `understanding_user_confirmation`, `user_approval`, `approved_at`, `independent_review`, `independent_reviewer`, and `independent_reviewed_at` in English with their established English values. There is no implicit migration. Do not convert an existing English document merely because new documents are localized, and never add Chinese aliases to it.

Determine the document schema before any metadata write. A document containing known English and known Chinese keys, duplicate semantic fields, malformed flat metadata, or unsupported lifecycle values is unreliable. Do not select the more favorable value, repair it automatically, or write partial approval state. Approval and review writeback always preserve the current reliable schema. The canonical English eight-field handoff and its gate truth table remain unchanged; normalize the reliable document meaning into that canonical state without reverse-parsing the Chinese display view.

## Write Outcomes and Readback Reconciliation

- If the target path already exists and the user has not identified it as the current PRD, stop without writing or overwriting it.
- If a creation or approval precondition is not satisfied, report the actual pending or unknown state and make no write.
- If a local write fails and the tool confirms it was not applied, report the persistence failure and retain the prior state; this is confirmed not applied, not partial success.
- If the completion result is uncertain because the write tool was interrupted, timed out, or otherwise cannot say whether it applied, do not repeat the write. Read the target back before taking any review, approval, or downstream action.
- If readback is byte-for-byte the exact expected content, treat the write as applied and continue from the verified document state without another write.
- If readback is byte-for-byte the original content, treat the write as confirmed not applied; after fixing the cause, retry the same authorized write at most once from that original state.
- If readback is unreadable, partially changed, or differs from both expected and original content, keep the write result and every dependent gate unknown. Do not overwrite or roll back automatically, do not repeat the write, and do not use partial approval. Stop for manual inspection of the current file.

Use repository-relative paths inside the PRD and an absolute path in the handoff.
