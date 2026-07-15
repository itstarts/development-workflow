---
name: creating-development-specs-and-plans
description: Use when users have approved product requirements and need a technical specification, an implementation plan, or a review of those documents before development handoff.
---

# Creating Development Specs and Plans

## Overview

Turn approved product requirements into a repository-grounded technical specification the user explicitly approves, then into an implementation plan a fresh independent reviewer approves. Preserve uncertainty and stop at gates instead of upgrading missing evidence.

## Workflow

1. Read [references/discovery-and-clarification.md](references/discovery-and-clarification.md), [references/document-contracts.md](references/document-contracts.md), and [references/review-and-handoff.md](references/review-and-handoff.md) completely before the first reply. Inspect applicable rules from the repository root to the working directory and relevant repository evidence. Never recursively search above the repository root.
2. Require an explicit product requirements path plus an expected topic and expected scope from the approved upstream handoff or the user. Do not derive expected identity from the PRD itself, its filename, or a guessed default. Run `scripts/inspect_product_requirements.py` with the repository root, requirements path, expected topic, and expected scope.
3. Continue only when the inspector returns parseable JSON with `status: approved` and `specification_gate: open`. A missing input, nonzero exit, unparseable output, mismatch, or unreliable field is `unknown`; a reliable pending gate is `not-approved`. In either case, do not create or materially modify the spec.
4. If a material technical choice remains after reading the approved PRD and repository evidence, ask one material question and stop. Otherwise write the technical spec using [assets/spec-template.md](assets/spec-template.md), preserving its requirements source fields.
5. Self-review the written spec, dispatch a fresh read-only spec reviewer when one is available, fix every finding, and re-review the current file. When the reviewer is known to be unavailable, do not dispatch and do not wait; keep independent review pending. After an explicit approval of the latest file, the main agent updates independent-review metadata. Independent approval does not equal user approval.
6. Stop and ask the user to explicitly approve the current written spec only after spec independent review is approved. Do not create the plan while either approval is absent; a material spec change invalidates both approvals.
7. After spec independent review is approved and the user approves that version, write the plan using [assets/plan-template.md](assets/plan-template.md). Self-review it, dispatch a fresh read-only plan reviewer when one is available, fix every finding, and re-review until the current file is approved. Apply the same known-unavailable reviewer rule without waiting or self-approving.
8. Return the fixed fourteen-field status record from the handoff reference with absolute paths.

## Hard Gates

- Keep an unavailable or inconclusive review blocked. Never replace independent review with author self-review.
- An approved PRD is a hard prerequisite for spec creation or material modification. Re-run its inspection before opening either downstream gate.
- Treat `review_status: pending` as `not-approved`; treat malformed, duplicate, conflicting, or unreadable review metadata as `unknown`.
- Open `implementation_gate` only while `specification_gate` remains open, spec independent review is approved, the user approved that reviewed spec, and the current plan has real independent approval.
- End every reply, including a clarification or blocked reply, with the complete fourteen-field handoff record.
- Do not implement target code, call sibling skills, create or manage a user-visible task/thread, or change external state. The terminal deliverable is the document handoff.
