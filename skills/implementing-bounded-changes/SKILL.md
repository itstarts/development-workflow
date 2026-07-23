---
name: implementing-bounded-changes
description: Use when the user has explicitly approved implementation or a bug fix for a bounded change in an existing or in-development project and wants scoped execution with proportional TDD, validation, risk-matched final review, and relevant documentation updates.
---

# Implementing Bounded Changes

## Overview

Execute an approved change directly in the current repository without requiring a PRD, spec, plan, or generated handoff prompt. Treat the approved scope as a hard boundary while preserving repository rules, user changes, validation evidence, risk-matched review, and affected documentation.

This skill does not bypass a repository's mandatory product, design, migration, safety, or release gates.

## Approval Gate

Modify files only after the user has explicitly approved implementation or repair. Agreement with an analysis, diagnosis, proposal, or request to inspect is not implementation approval.

When approval is absent, inspect only as authorized and return the proposed scope. When approval is ambiguous, ask one concise blocking question before writing. Do not infer approval from urgency, a previous approval of a different version, or permission to investigate.

## Workflow

### 1. Inspect the Current State

Before writing, read every applicable repository rule, current status or recovery document, relevant code, tests, configuration, and existing documentation. Check `git status` and relevant diffs. Preserve unrelated user changes and existing failures.

Use repository evidence to confirm the actual change surface. Do not turn a bounded request into broad product discovery or architecture work.

### 2. Freeze the Execution Scope

Record a concise scope card in the conversation before the first write:

- approved goal and observable acceptance result;
- change points expected to be touched;
- implementation approach already agreed or supported by repository evidence;
- non-goals and adjacent behavior that must remain unchanged;
- validation boundary, including the public test seam when behavior changes;
- documentation impact and the existing documents expected to change.

If these facts are already explicit and consistent, restate them and continue without asking the user to approve the same scope again. Ask only when a missing answer could materially alter behavior, design, contracts, validation, or documentation.

Do not create a PRD, technical spec, implementation plan, progress document, or other planning artifact solely for this bounded task. Follow an existing repository requirement when it explicitly mandates one.

### 3. Enforce the Scope-Change Gate

Stop before making that change and request explicit user approval when implementation evidence requires any material addition or change to:

- approved behavior, acceptance results, or non-goals;
- a public contract, API, schema, protocol, or compatibility promise;
- a dependency, architecture, shared abstraction, or cross-module design;
- a data model, migration, permission, security boundary, money flow, concurrency, transaction, or consistency rule;
- the agreed validation boundary or external-state permissions.

Do not disguise expansion as cleanup, consistency, future-proofing, reuse, hardening, or an implementation detail. Local, reversible details may follow an established repository pattern only when they preserve the approved behavior and boundary.

Apply the same gate to reviewer suggestions. Record out-of-scope reviewer suggestions separately; do not implement them without approval.

### 4. Implement the Smallest Vertical Change

For an observable behavior change or bug fix:

1. Confirm the public seam named by the scope card.
2. Add one behavior-level test for the approved result.
3. Run it and observe the test fail for the expected reason before changing production behavior.
4. Write the smallest implementation that makes that slice pass.
5. Re-run the focused test, or let an immediately required parent gate supply the GREEN result when it covers the same seam; then repeat only for another approved behavior slice.

Do not edit the test and production behavior in one unobserved step. Test public behavior rather than private implementation details, and keep expected values independent of the implementation.

When a documentation, formatting, or mechanical change has no meaningful executable seam, do not manufacture a test. Use the narrowest relevant static, parsing, rendering, or diff check instead. Refactor only after GREEN, only when necessary for the approved change, and only inside the frozen scope.

### 5. Use Bounded Delegation

Use a Sub Agent when a bounded subtask can reduce risk or latency, including read-only discovery, an isolated implementation slice, or independent review. Give each delegate explicit inputs, allowed files or decisions, non-goals, and expected evidence.

The main Agent retains scope control, shared-contract decisions, integration, validation, and the completion claim. Do not delegate the entire task without boundaries. If no matching Agent capability is available, proceed locally when safe or report the capability gap; do not claim that delegation occurred.

### 6. Validate and Update Documentation

Run the smallest sufficient validation for the affected behavior and files. Do not default to the full test suite. Expand validation only when repository rules require it, the change touches shared or high-risk behavior, a focused check cannot establish correctness, or unexpected impact appears.

Maintain an in-memory validation ledger for the logical task. Record each command, the behavior or files it covers, the relevant task state and environment, and its conclusive result. Do not persist this ledger to the repository or user directories.

Reuse a passing result while its relevant production code, test, fixture, configuration, dependency, validation command, and environment remain unchanged. Do not rerun a passing check merely because review or Agent handoff starts, progress is reported, or another workflow stage consumes the same evidence. Invalidate only the affected validation when a relevant input changes; preserve unrelated passing results. After the last relevant change, re-run the invalidated checks and run any required parent or final gate once. When that gate covers an invalidated focused seam, let the gate supply its GREEN result instead of adding a separate focused run immediately before it.

A timeout, cancellation, missing exit status, truncated evidence, or otherwise inconclusive result is not a pass. Diagnose the cause before retrying, and retry only when a concrete cause or changed condition makes another run informative.

When current evidence establishes a reusable project-specific validation mapping that is absent from the project rules, keep using a temporary in-memory mapping so the current task does not pause. Preserve candidate evidence such as affected paths, exact commands, applicability boundaries, and expected validation-cost reduction for an applicable rule-governance process. Do not edit `AGENTS.md` as part of implementation: implementation approval is not rule approval. Do not invent a generic mapping or require the user to persist it.

Keep unrelated pre-existing failures unchanged and attribute them with evidence. Never fix them merely to obtain a green full-suite result.

Update only existing documentation affected by the behavior or operating change, such as README, API, configuration, operational, status, or changelog documents. Create a new document only when the user or an applicable repository rule requires it. Documentation is part of completion: validate it where a relevant check exists and include it in the final diff and review.

### 7. Classify the Review Requirement

Apply higher-priority user instructions and applicable repository rules before the defaults below. Resolve conflicts using their active precedence. These skill defaults do not create a separate hard gate when a higher-priority source has already decided the review requirement for the current task.

A lightweight behavior change does not require independent review by default when it is local and reversible, deterministic behavior-level tests cover the approved result and direct regression boundary, no high-risk boundary or shared contract is involved, validation is conclusive, and neither the user nor repository rules require review. Pure documentation, formatting, or deterministic mechanical changes may use the same exemption with the narrowest sufficient static, parsing, rendering, or diff check. A stale, non-normative documentation example may qualify when it only synchronizes to behavior already established by current code and focused tests.

For a medium task, decide from actual risk, affected boundaries, reversibility, and validation coverage; task size alone is not a review trigger. Use independent review when evidence shows meaningful shared-logic, compatibility, public-contract, important business-rule, cross-module, or validation-gap risk. A localized medium task with conclusive deterministic coverage may remain review-exempt when the higher-priority sources allow it. Record the concrete decision basis either way.

Under these defaults, require mandatory final review for a data model or migration, permission or security boundary, money flow, irreversible operation, concurrency, transaction, consistency rule, or another boundary that the applicable repository rules classify as high risk. Also review whenever repository rules require review. Resolve uncertain risk with repository evidence before deciding; do not escalate solely from a label when the observable boundaries are known.

When independent review is not required, inspect the latest complete diff after validation and report the concrete exemption reason. Do not report `APPROVED`, a reviewer identity, or review evidence when no independent review occurred.

When review is required, ask one implementation-independent reviewer to inspect the latest complete diff after implementation, documentation updates, and focused validation. Require the reviewer to check correctness, regression risk, scope adherence, validation sufficiency, and documentation consistency. Do not require per-slice or per-task review for a bounded change.

Classify every finding as `BLOCKING_IN_SCOPE`, `SCOPE_CHANGE_REQUIRED`, or `NON_BLOCKING_NOTE`. A `BLOCKING_IN_SCOPE` finding must cite approved acceptance, an existing contract, an applicable rule, a current regression, or a concrete high-risk correctness failure, then give the evidence and minimum in-scope fix. Use `SCOPE_CHANGE_REQUIRED` when resolution would expand the frozen scope, and `NON_BLOCKING_NOTE` for optional improvement. A priority label alone does not make a finding blocking. For an ordinary P2 recommendation without blocking evidence, record it as `NON_BLOCKING_NOTE` or `SCOPE_CHANGE_REQUIRED` and do not enter the automatic repair-and-review loop.

Fix only `BLOCKING_IN_SCOPE` findings, re-run affected validation, and have the same reviewer re-check the updated diff. A changed diff invalidates the prior approval. Non-blocking findings do not prevent `APPROVED`.

Count one repair-and-review cycle only when the reviewer requests changes for a `BLOCKING_IN_SCOPE` finding, the main Agent applies the in-scope fix, affected validation is rerun, and the same reviewer assesses the changed diff. If two consecutive repair-and-review cycles end without `APPROVED`, stop the automatic loop and report the task as `BLOCKED` with the remaining findings and verification evidence. The implementation gate remains blocked. User direction may resolve a scope choice or authorize a changed scope, but it cannot replace missing correctness or review evidence. Resume only from new material evidence or newly approved scope; do not add a second reviewer merely to seek a favorable verdict.

Once approved, stop reviewing. Do not add another reviewer, seek consensus, or repeat the same review without a new diff or new material evidence. Independent review must not expand the approved scope or validation boundary.

Do not self-approve. Do not claim independent review, Sub Agent use, or approval unless the runtime actually produced that evidence. When review is required and the reviewer is unavailable, inconclusive, or does not approve after in-scope fixes, report the task as BLOCKED and do not claim completion.

### 8. Complete Truthfully

Inspect the final diff and working tree before reporting. Report:

- changed files and resulting behavior;
- documentation updates;
- validation commands and results;
- independent review result and actual reviewer identity, or the concrete review-exemption reason;
- unrelated pre-existing failures;
- unresolved limitations and any scope decision still awaiting approval.

Do not commit, push, merge, release, deploy, or change external state unless the user has explicitly authorized that operation and current repository and platform rules allow it.

## Hard Boundaries

- User approval opens only the frozen scope, not adjacent work.
- TDD is proportional but a behavior change must show RED before GREEN.
- Sub Agent use is allowed, never fabricated, and never a substitute for main-Agent integration.
- Focused validation is the default; broader validation needs evidence.
- Relevant documentation and the latest complete diff belong in the final inspection and, when required, the completion review.
- A justified review exemption never removes final diff inspection or validation.
- When review is required, one final reviewer is sufficient; APPROVED ends the review loop.
- Missing evidence remains missing; never upgrade it to success.
