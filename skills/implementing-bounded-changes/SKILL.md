---
name: implementing-bounded-changes
description: Use when the user has explicitly approved implementation or a bug fix for a bounded change in an existing or in-development project and wants scoped execution with proportional TDD and validation, optional Sub Agent delegation, independent review, and relevant documentation updates.
---

# Implementing Bounded Changes

## Overview

Execute an approved change directly in the current repository without requiring a PRD, spec, plan, or generated handoff prompt. Treat the approved scope as a hard boundary while preserving repository rules, user changes, validation evidence, independent review, and affected documentation.

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
5. Re-run the focused test, then repeat only for another approved behavior slice.

Do not edit the test and production behavior in one unobserved step. Test public behavior rather than private implementation details, and keep expected values independent of the implementation.

When a documentation, formatting, or mechanical change has no meaningful executable seam, do not manufacture a test. Use the narrowest relevant static, parsing, rendering, or diff check instead. Refactor only after GREEN, only when necessary for the approved change, and only inside the frozen scope.

### 5. Use Bounded Delegation

Use a Sub Agent when a bounded subtask can reduce risk or latency, including read-only discovery, an isolated implementation slice, or independent review. Give each delegate explicit inputs, allowed files or decisions, non-goals, and expected evidence.

The main Agent retains scope control, shared-contract decisions, integration, validation, and the completion claim. Do not delegate the entire task without boundaries. If no matching Agent capability is available, proceed locally when safe or report the capability gap; do not claim that delegation occurred.

### 6. Validate and Update Documentation

Run the smallest sufficient validation for the affected behavior and files. Do not default to the full test suite. Expand validation only when repository rules require it, the change touches shared or high-risk behavior, a focused check cannot establish correctness, or unexpected impact appears.

Keep unrelated pre-existing failures unchanged and attribute them with evidence. Never fix them merely to obtain a green full-suite result.

Update only existing documentation affected by the behavior or operating change, such as README, API, configuration, operational, status, or changelog documents. Create a new document only when the user or an applicable repository rule requires it. Documentation is part of completion: validate it where a relevant check exists and include it in the final diff and review.

### 7. Obtain Independent Review

Final review is a completion gate. After implementation, documentation updates, and focused validation, ask one implementation-independent reviewer to inspect the latest complete diff. Require the reviewer to check correctness, regression risk, scope adherence, validation sufficiency, and documentation consistency.

Do not require per-slice or per-task review for a bounded change. Fix only in-scope findings, re-run affected validation, and have the same reviewer re-check the updated diff until the reviewer returns APPROVED. A changed diff invalidates the prior approval.

Once approved, stop reviewing. Do not add another reviewer, seek consensus, or repeat the same review without a new diff or new material evidence. Independent review must not expand the approved scope or validation boundary.

Do not self-approve. Do not claim independent review, Sub Agent use, or approval unless the runtime actually produced that evidence. When the reviewer is unavailable, inconclusive, or does not approve after in-scope fixes, report the task as BLOCKED and do not claim completion.

### 8. Complete Truthfully

Inspect the final diff and working tree before reporting. Report:

- changed files and resulting behavior;
- documentation updates;
- validation commands and results;
- independent review result and actual reviewer identity or capability gap;
- unrelated pre-existing failures;
- unresolved limitations and any scope decision still awaiting approval.

Do not commit, push, merge, release, deploy, or change external state unless the user has explicitly authorized that operation and current repository and platform rules allow it.

## Hard Boundaries

- User approval opens only the frozen scope, not adjacent work.
- TDD is proportional but a behavior change must show RED before GREEN.
- Sub Agent use is allowed, never fabricated, and never a substitute for main-Agent integration.
- Focused validation is the default; broader validation needs evidence.
- Relevant documentation and the latest complete diff belong in the completion review.
- One final reviewer is sufficient; APPROVED ends the review loop.
- Missing evidence remains missing; never upgrade it to success.
