---
document_type: implementation-plan
topic: <stable-topic>
spec_path: <repository-relative-spec-path>
spec_user_approval: approved
review_status: pending
---

# <Feature Name> Implementation Plan

**Goal:** <One observable outcome.>

**Architecture:** <Implementation approach and stable boundaries.>

**Tech Stack:** <Existing languages, frameworks, and tools.>

## Global Constraints

<Copy exact project-wide constraints from the approved spec and applicable rules.>

### Task <number>: <Independently Testable Deliverable>

**Exact files:**

- Create: `<repository-relative-path>`
- Modify: `<repository-relative-path>`
- Test: `<repository-relative-path>`

**Interfaces:**

- Consumes: <Existing signatures, inputs, or artifacts.>
- Produces: <Exact signatures, outputs, or artifacts used later.>

**Testing approach:** <Use the approach required by the approved spec and repository rules. When the approved spec or repository rules require TDD, include RED, Verify RED, GREEN, Verify GREEN, and REFACTOR steps; otherwise list the minimum relevant implementation and verification steps.>

- [ ] Implement: <Make the smallest production change required by the task.>
- [ ] Verify: Run `<exact command>`; expect <observable result>.
- [ ] Documentation synchronization: <Update the exact affected document or state why none changes.>
- [ ] Task-level independent review: <Review the current diff and verification evidence; fix findings and re-review.>

## Final Verification

<List complete commands, expected results, integration review, and any explicitly unverified release gate.>
