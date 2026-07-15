---
name: creating-product-requirements
description: Use when users need to define product requirements or a PRD, clarify product scope, capture user scenarios and acceptance criteria, or review product requirements before technical design.
---

# Creating Product Requirements

## Overview

Turn product intent into one approved PRD before technical design. Preserve uncertainty and keep the specification gate blocked until understanding, review, and approval evidence are all current.

## Workflow

1. Read [references/discovery-and-confidence.md](references/discovery-and-confidence.md), [references/document-contract.md](references/document-contract.md), and [references/review-and-handoff.md](references/review-and-handoff.md) completely before the first reply. Inspect applicable repository rules and product evidence without searching above the repository root.
2. Establish one `product`, `phase`, or `feature` scope and one non-reserved lowercase ASCII kebab-case stable topic. Use that same topic in the confirmed summary, PRD frontmatter, default path, and handoff. Ask one material product question at a time while any answer could change users, goals, scope, business rules, priority, success measures, or acceptance criteria.
3. Do not create the PRD until understanding confidence is at least 95 and the user explicitly confirms the current requirements-understanding summary. Confidence does not replace confirmation.
4. After both understanding gates pass, create or update the PRD with [assets/prd-template.md](assets/prd-template.md). Keep architecture, API, database design, code files, and implementation tasks out of the PRD.
5. Self-review the current PRD, dispatch a fresh read-only reviewer, fix every finding, and re-review the latest file. Independent review does not equal user approval.
6. After independent approval, direct the user to the current file and ask them to explicitly approve it. Open `specification_gate` only when the current PRD retains all understanding and document approvals.
7. End every reply with the fixed eight-field handoff from the review reference.

## Hard Gates

- Do not combine independent product topics into one PRD. Keep topic and path unresolved until the user chooses.
- Treat missing, unreadable, duplicate, conflicting, or unsupported metadata as unknown; never upgrade it to pending or approved.
- A material change resets affected approval states. Reassess confidence truthfully; a score at or above 95 still does not replace confirmation of the updated summary.
- Do not create a design spec or implementation plan, implement target code, call sibling skills, or change external state. The terminal deliverable is the approved PRD handoff.
