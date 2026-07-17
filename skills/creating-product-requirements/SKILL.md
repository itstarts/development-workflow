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
6. After independent approval, direct the user to the current file and ask them to explicitly approve it. Open `specification_gate` only when the current PRD retains all understanding and document approvals. Write and validate the current approval metadata before building the complete canonical English eight-field handoff.
7. Pre-render and validate the one authoritative Chinese user-visible view defined in the review reference before selecting any downstream capability. Continue only when its field count, field order, labels, and contextual value mapping are complete and unique.
8. When `specification_gate` is open and the Chinese view is valid, use the frozen canonical English handoff to select the runtime-exposed `creating-development-specs-and-plans` skill capability in the same session. Pass the explicit `requirements_path`, `requirements_topic`, `requirements_scope`, and complete canonical handoff. If the capability is unavailable, report the capability gap without searching installation paths or changing the approved PRD.
9. Follow the response ownership rules in the review reference: replies that do not transition end with the one authoritative Chinese eight-field view; after a successful downstream transition, the downstream Chinese fourteen-field view owns the final response while the canonical English eight fields remain its machine input prefix.

## Hard Gates

- Do not combine independent product topics into one PRD. Keep topic and path unresolved until the user chooses.
- Treat missing, unreadable, duplicate, conflicting, or unsupported metadata as unknown; never upgrade it to pending or approved.
- A material change resets affected approval states. Reassess confidence truthfully; a score at or above 95 still does not replace confirmation of the updated summary.
- Never use the Chinese view to open a gate or reconstruct machine state. On mapping failure, preserve the canonical snapshot, emit no partial or fallback handoff, and stop before downstream selection.
- This skill does not create the design spec or implementation plan and does not implement target code. It may select the runtime-exposed skill capability only after the approved handoff is validated.
- Do not read sibling skill source, inspect sibling skill installation directories, infer fixed local paths, or change external state.
