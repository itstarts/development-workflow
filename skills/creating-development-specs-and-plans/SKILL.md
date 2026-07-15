---
name: creating-development-specs-and-plans
description: Use when users need to clarify development requirements, design a feature before coding, write a specification or implementation plan, or review planning documents before a development handoff.
---

# Creating Development Specs and Plans

## Overview

Turn repository-grounded requirements into a written specification the user explicitly approves, then into an implementation plan a fresh independent reviewer approves. Preserve uncertainty and stop at gates instead of upgrading missing evidence.

## Workflow

1. Read [references/discovery-and-clarification.md](references/discovery-and-clarification.md) and [references/review-and-handoff.md](references/review-and-handoff.md) completely before the first reply. Inspect applicable rules from the repository root to the working directory and relevant repository evidence before asking or writing. Never recursively search above the repository root.
2. Read [references/document-contracts.md](references/document-contracts.md) completely. If a material choice remains, ask one material question and stop before document or review work. Otherwise write the spec using [assets/spec-template.md](assets/spec-template.md).
3. Self-review the written spec, dispatch a fresh read-only spec reviewer, fix every finding, and re-review the current file. After an explicit approval of the latest file, the main agent updates independent-review metadata. Independent approval does not equal user approval.
4. Stop and ask the user to explicitly approve the current written spec only after spec independent review is approved. Do not create the plan while either approval is absent; a material spec change invalidates both approvals.
5. After spec independent review is approved and the user approves that version, write the plan using [assets/plan-template.md](assets/plan-template.md). Self-review it, dispatch a fresh read-only plan reviewer, fix every finding, and re-review until the current file is approved.
6. Return the fixed status record from the handoff reference with absolute paths.

## Hard Gates

- Keep an unavailable or inconclusive review blocked. Never replace independent review with author self-review.
- Treat `review_status: pending` as `not-approved`; treat malformed, duplicate, conflicting, or unreadable review metadata as `unknown`.
- Open `implementation_gate` only when spec independent review is approved, the user approved that reviewed spec, and the current plan has real independent approval.
- End every reply, including a clarification or blocked reply, with the complete six-field handoff record.
- Do not implement target code, call sibling skills, create or manage a user-visible task/thread, or change external state. The terminal deliverable is the document handoff.
