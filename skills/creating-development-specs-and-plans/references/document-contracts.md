# Document Contracts

## Specification

Use `assets/spec-template.md` as the required shape. Replace every angle-bracket slot with current evidence and delete instructional slot text from the finished document.

Write user-facing titles, section headings, explanatory prose, labels, and template-derived content in Chinese by default. New specifications and plans use the `chinese-current` frontmatter schemas below. Paths, commands, API names, protocols, filenames, stable topics, ISO dates, reviewer roles, Task identifiers, and canonical handoff identifiers retain their technical form.

Create or materially modify the spec only from approved product requirements whose explicit path, expected topic, expected scope, confidence, summary confirmation, independent review, and user approval all passed `inspect_product_requirements.py`. Copy the requirements source into spec frontmatter using a repository-relative path and preserve its validated topic, scope, confidence, confirmation, and approval states.

The technical spec must state goals, non-goals, current evidence, behavior and boundaries, component responsibilities or control flow, errors and uncertainty, testing, documentation impact, and observable acceptance criteria. When relevant, it owns API definitions and other technical interfaces, the data model and entity relationships, migration boundaries, state transitions, transaction or concurrency behavior, and consistency guarantees. It must not rewrite product scope or treat implementation choices as new product requirements. Cover security, permissions, or sensitive data only when the requested feature actually touches those boundaries. Use positive requirements. Record a prohibition only when a real misuse or high-risk boundary makes it necessary.

For every interface that changes durable state or drives asynchronous work, include a command outcome and failure matrix. Normalize the matrix by outcome, not by command: give every distinct outcome a unique Outcome ID and its own row, then repeat the command or asynchronous stage across rows as needed. Cover every state-changing command and every asynchronous completion or commit path. Name each outcome's preconditions, result type, client-visible status and error fields, durable side effects, rollback behavior, caller action, retry ownership, and linked Guarantee IDs. Success, no-op, validation or state failure, conflict or contention, local persistence failure, relevant remote dependency, cancellation, timeout, and unknown results are distinct outcomes when they can occur. Reconciliation success, confirmed non-application, and unknown commit state must be separate rows. Never merge outcomes that require different caller action or produce different consistency effects.

When a database, transaction, lock, or durable queue affects correctness, name the actual database engine, configured mode and relevant version, driver or transaction layer, and authoritative evidence. Specify transaction start and end, the first read and first write, lock acquisition order, read-to-write upgrade semantics or the rule that prevents an upgrade, lock hold duration and release point, isolation or snapshot boundary, busy, deadlock, and timeout behavior, retries, rollback, and public failure classification. If the engine or mode remains undecided and changes these guarantees, ask before writing the spec. Framework-generic transaction language is not sufficient when engine-specific behavior affects correctness.

Assign a unique Guarantee ID to every material invariant, consistency promise, rollback guarantee, and client-reachable failure guarantee. Link every outcome row to at least one Guarantee ID, then add one traceability row per Guarantee ID that names the exact Outcome IDs, exact test file and test name, exact test command, and observable assertion. Map every material matrix outcome, transaction or lock guarantee, and asynchronous publish or completion guarantee to at least one automated test, and map each required test back to its Guarantee ID. When no automated seam exists, state the evidence-backed reason and the required manual check; high-risk transaction, concurrency, persistence, and client-visible failure guarantees cannot rely only on manual validation.

## Acceptance Evidence

Classify every observable acceptance item by the evidence that can actually establish it. Use the minimum critical E2E set only for a repeatable cross-layer technical closure whose production-like entry point, component boundaries, and durable or externally visible result cannot be established by lower-level tests alone. Keep unit, component, API, integration, and other focused tests as the main technical regression layers; do not promote every guarantee or failure branch into E2E.

Use target-user manual acceptance for usability, content quality, and visual experience. Name the target-user role, acceptance owner, release-candidate environment, concrete task, observable judgment or threshold, and retained evidence. Assign subjective product judgment only to people acting as the named target-user cohort. A developer or reviewer may participate only if they independently satisfy that target-user profile; their implementation or review role alone is not acceptance evidence. Automated assertions cannot establish subjective product judgment. When one product outcome contains both a technical closure and an experience judgment, split it into separate acceptance rows instead of forcing one evidence type to cover both.

The specification must record the selected acceptance type and evidence boundary. The implementation plan must preserve that classification and turn it into exact scope: enumerate every E2E scenario by name with its command, environment, observable assertions, and evidence, then enumerate every manual acceptance scenario with its target users, owner, steps, pass condition, and evidence. Do not leave either list for implementers to decide. Manual acceptance cannot replace critical technical regression. E2E cannot claim product-experience validation.

For a new `chinese-current` specification, write exactly these semantic fields and representations at creation:

| Canonical semantic key | Chinese key | Initial Chinese value or format |
| --- | --- | --- |
| `document_type` | `文档类型` | `技术规格` |
| `topic` | `主题` | stable topic unchanged |
| `requirements_path` | `需求文档` | repository-relative PRD path |
| `requirements_topic` | `需求主题` | stable topic unchanged |
| `requirements_scope` | `需求范围` | `产品`、`阶段`、or `功能` |
| `requirements_understanding_confidence` | `需求理解置信度` | integer from 95 through 100 |
| `requirements_understanding_confirmation` | `需求理解确认` | `已确认` |
| `requirements_user_approval` | `需求文档用户批准` | `已批准` |
| `requirements_independent_review` | `需求文档独立评审` | `已通过` |
| `specification_gate` | `技术规格门禁` | `已开放` |
| `user_approval` | `技术规格用户批准` | `待批准` |
| `independent_review` | `技术规格独立评审` | `待评审` |

After a fresh specification review, change only the same Chinese schema to `技术规格独立评审: 已通过` and add `技术规格独立评审角色` plus `技术规格独立评审日期`. After the user explicitly approves that reviewed version, change only `技术规格用户批准` to `已批准` and add `技术规格批准日期`. Keep every path, topic, confidence integer, ISO date, and reviewer role value unchanged.

The reviewer remains read-only; after it explicitly approves the latest file, the main agent writes the matching current-schema review fields. User approval is recorded only after the user has been directed to that independently approved written file and explicitly approves the same version. The initial request to write both documents, silence, old approval, or reviewer approval is not user approval.

## Implementation Plan

Resolve the route before plan creation. A reliable `standard` route is present only when the separately supplied route handoff and the approved PRD's unique `## 工作流分流` section both say `workflow_route: standard` and their risk facts do not establish a full-route boundary. A `full` value, any mismatch, or a missing or unreliable route selects the full route.

On the standard route, create the plan before spec user approval as part of one technical package. The current spec must be complete and reliable, but its `技术规格用户批准` remains `待批准`. Create a new `chinese-current` plan with exactly `文档类型: 实施计划`, `主题`, `技术规格`, `技术规格用户批准: 待批准`, `评审模式: 技术包`, and `计划评审状态: 待评审`. One package reviewer examines both complete files, and one verdict covers the current spec and plan. After approval, record the real reviewer and date in both files' current schemas: the spec independent review and plan review become approved while technical specification user approval remains pending. The implementation gate remains blocked.

When the user later approves that same reviewed spec without a material content change, update the spec approval metadata and synchronize the plan metadata to `技术规格用户批准: 已批准`. This metadata-only synchronization does not invalidate the package review. Revalidate both files before opening the implementation gate.

On the full route, preserve the sequential lifecycle: the user approves that reviewed spec before creating the plan. Create the plan with `技术规格用户批准: 已批准`, `评审模式: 逐级`, and `计划评审状态: 待评审`, then use a separate plan reviewer. After a real package or plan review approval, keep the same schema, change only `计划评审状态` to `已通过`, and add `计划评审角色` plus `计划评审日期`. Do not add English aliases.

Each task is one independently testable execution slice. Task decomposition creates implementation and validation boundaries, not automatic independent-review gates. Include:

- exact repository-relative create/modify/test files;
- interfaces consumed and produced;
- the testing approach required by the approved spec and repository rules; when they require TDD, include RED, Verify RED, GREEN, Verify GREEN, and REFACTOR steps;
- executable commands, named tests, and observable expected results;
- the approved spec Guarantee IDs covered by the task, with exact tests, commands, and observable assertions and no orphan guarantee or required test;
- documentation synchronization.

Preserve the approved spec's acceptance classification. List the exact minimum critical E2E scenarios and the exact target-user manual acceptance scenarios in a dedicated plan section before task decomposition. Carry each scenario into the responsible task and final validation without adding broader E2E coverage or converting subjective product experience into automated assertions.

Define one implementation review strategy for the complete plan. By default, after all tasks are integrated and the relevant validation passes, one implementation-independent reviewer inspects the latest complete diff; in-scope findings are fixed, affected validation is rerun, and the same reviewer re-checks the updated diff. Stop after `APPROVED`. If two consecutive repair-and-review cycles end without approval, stop automatic repair, report the remaining findings, and the implementation gate remains blocked. User direction may resolve a scope choice, but it cannot replace missing correctness or review evidence. Add an intermediate milestone review only when a task independently crosses a material public-contract, data, migration, permission, security, money, concurrency, transaction, or consistency boundary, or when later tasks depend on an otherwise unverified critical foundation. State each milestone's trigger, reason, and review scope. Never create per-task review gates merely because of task count.

Include commit steps only when the user and repository rules authorize commits. Do not embed large final implementations; provide exact signatures, assertions, data shapes, boundaries, and locations needed to avoid design guesses.

## Metadata and Status

Both document types start at byte zero with flat YAML frontmatter. Determine the current document schema before reading or writing lifecycle metadata.

An existing spec with the complete established English keys and values is `english-legacy`; an existing plan with `document_type`, `topic`, `spec_path`, `spec_user_approval`, and `review_status` is also `english-legacy`. Maintain, invalidate, approve, and re-review each existing spec or existing plan in the same schema. There is no implicit migration. Do not convert an existing English document merely because new documents are localized, and do not append Chinese aliases. Existing reliable plans without `评审模式` retain their established sequential meaning; do not infer technical-package authority from absence.

For an `english-legacy` spec, continue to use `user_approval`, `approved_at`, `independent_review`, `independent_reviewer`, and `independent_reviewed_at` with their established English values. For an `english-legacy` plan, continue to use `review_status`, `reviewer`, and `reviewed_at`. Never record an agent run identifier in either schema.

Before plan creation, require a complete `chinese-current` spec or a reliable `english-legacy` spec. A complete Chinese spec contains every creation field listed above. When its technical-spec approval or review is approved, the matching Chinese date and reviewer fields must also be present and unique; pending states must not retain stale approval, reviewer, or review-date fields. The standard route may create the plan while the reliable spec review and user approval are still pending because the reviewer receives both complete drafts together; the full route may not. Classify a mixed schema, semantic duplicate, missing field, malformed flat metadata, or unsupported localized value as unreliable. Do not create the plan from such a spec, do not choose a favorable status, and keep `implementation_gate` blocked.

For plan review derivation, Chinese `计划评审状态: 待评审` and English `review_status: pending` both map to canonical `not-approved`; Chinese `已通过` and English `approved` map to canonical `approved`. `评审模式` accepts only `技术包 | 逐级` for new Chinese plans. `技术包` permits reliable plan review while spec user approval is pending, but the implementation gate stays blocked. `逐级` requires spec user approval before plan creation. A missing mode remains compatible only for an existing plan whose spec approval is already reliable and approved. A missing, malformed, duplicate, conflicting, nested, multiline, quoted, unreadable, or unsupported state maps to `unknown`. Reviewer identity or date never substitutes for a reliable review status.

A material spec change invalidates its independent review and user approval and invalidates the plan review because the reviewed package or sequential plan no longer describes the current spec. A material plan-only change invalidates plan review without invalidating the unchanged spec review or user approval. Updating only the approval metadata of the unchanged package-reviewed spec and synchronizing its copied state in the plan does not invalidate the package review.

## Write Outcomes and Readback Reconciliation

- If the target path already exists and the user has not identified it as the current spec or plan, stop without writing or overwriting it.
- If a PRD, spec approval, review, or other creation precondition is not satisfied, report the actual pending or unknown state and make no write.
- If a local write fails and the tool confirms it was not applied, report the persistence failure and retain the prior state; this is confirmed not applied, not partial success.
- If the completion result is uncertain because the write tool was interrupted, timed out, or otherwise cannot say whether it applied, do not repeat the write. Read the target back before taking any review, approval, plan-creation, or routing action.
- If readback is byte-for-byte the exact expected content, treat the write as applied and continue from the verified document state without another write.
- If readback is byte-for-byte the original content, treat the write as confirmed not applied; after fixing the cause, retry the same authorized write at most once from that original state.
- If readback is unreadable, partially changed, or differs from both expected and original content, keep the write result and every dependent gate unknown. Do not overwrite or roll back automatically, do not repeat the write, and do not use partial approval. Stop for manual inspection of the current file.

Internal requirements, spec, and plan paths stay repository-relative. Final handoff paths are absolute. If the PRD changes materially or no longer validates, close both downstream gates; do not preserve implementation authority from stale spec or plan approvals.
