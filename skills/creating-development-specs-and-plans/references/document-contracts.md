# Document Contracts

## Specification

Use `assets/spec-template.md` as the required shape. Replace every angle-bracket slot with current evidence and delete instructional slot text from the finished document.

Create or materially modify the spec only from approved product requirements whose explicit path, expected topic, expected scope, confidence, summary confirmation, independent review, and user approval all passed `inspect_product_requirements.py`. Copy the requirements source into spec frontmatter using a repository-relative path and preserve its validated topic, scope, confidence, confirmation, and approval states.

The technical spec must state goals, non-goals, current evidence, behavior and boundaries, component responsibilities or control flow, errors and uncertainty, testing, documentation impact, and observable acceptance criteria. When relevant, it owns API definitions and other technical interfaces, the data model and entity relationships, migration boundaries, state transitions, transaction or concurrency behavior, and consistency guarantees. It must not rewrite product scope or treat implementation choices as new product requirements. Cover security, permissions, or sensitive data only when the requested feature actually touches those boundaries. Use positive requirements. Record a prohibition only when a real misuse or high-risk boundary makes it necessary.

Start with `user_approval: pending` and `independent_review: pending`. The reviewer remains read-only; after it explicitly approves the latest file, the main agent updates `independent_review`, a generic reviewer role, and the review date. Set user approval to `approved` only after the user has been directed to that independently approved written file and explicitly approves the same version. The initial request to write both documents, silence, old approval, or reviewer approval is not user approval.

## Implementation Plan

Create a plan only when the PRD specification gate remains open, spec independent review is approved, and the user has approved that reviewed spec. Use the approved PRD, current spec, repository evidence, applicable rules, and `assets/plan-template.md` as the required shape.

Each task is one independently testable deliverable a reviewer could reject without rejecting an unrelated task. Include:

- exact repository-relative create/modify/test files;
- interfaces consumed and produced;
- the testing approach required by the approved spec and repository rules; when they require TDD, include RED, Verify RED, GREEN, Verify GREEN, and REFACTOR steps;
- executable commands, named tests, and observable expected results;
- documentation synchronization;
- a task-level independent review gate.

Include commit steps only when the user and repository rules authorize commits. Do not embed large final implementations; provide exact signatures, assertions, data shapes, boundaries, and locations needed to avoid design guesses.

## Metadata and Status

The plan starts at byte zero with flat YAML frontmatter. Before review it contains exactly one `review_status: pending`. After a real approval replace that value with `approved` and add a generic reviewer role plus review date. Never record an agent run identifier.

`pending` maps to `not-approved`. A missing, malformed, duplicate, conflicting, nested, multiline, quoted, or unreadable status maps to `unknown`. Only reliable `approved` maps to `approved`.

Internal requirements, spec, and plan paths stay repository-relative. Final handoff paths are absolute. If the PRD changes materially or no longer validates, close both downstream gates; do not preserve implementation authority from stale spec or plan approvals.
