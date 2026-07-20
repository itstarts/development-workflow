---
name: creating-product-requirements
description: Use when and only when the requested deliverable is a product requirements document or PRD, or the user explicitly wants product scope, user scenarios, business rules, success measures, and acceptance criteria formalized before technical design. Do not use for content-only deliverables such as narration, scripts, copy, outlines, or articles merely because their structure, duration, or scope changes.
---

# Creating Product Requirements

## Applicability Gate

Before establishing any PRD workflow state, reading workflow references, selecting a topic or document path, or rendering status, identify the final requested deliverable.

This skill applies only when the final deliverable is a PRD, or when the user explicitly asks to formalize product behavior or development scope as product requirements before technical design. If the final deliverable is only narration, a script, copy, an outline, an article, or another content document, and the user has not explicitly requested a PRD or downstream product behavior or development scope, this skill does not apply. Changes to content structure, duration, or scope do not by themselves turn a content task into product-requirements work.

When this skill does not apply:

- Do not create a PRD.
- Do not emit the eight-field status in compact or full form.
- Do not transition to a spec or plan.
- Return to the original task and produce the requested content directly.

Only after this gate passes may the workflow below begin.

## Overview

Turn product intent into one approved PRD before technical design. Preserve uncertainty and keep the specification gate blocked until understanding, review, and approval evidence are all current.

## Workflow

1. First read only [references/discovery-and-confidence.md](references/discovery-and-confidence.md), then inspect applicable repository rules and product evidence without searching above the repository root. Before the first PRD write, read [references/document-contract.md](references/document-contract.md) completely. Before summary confirmation, review, approval, a blocked or full-status reply, or downstream transition, read [references/review-and-handoff.md](references/review-and-handoff.md) completely. Read each required reference once per current workflow unless it changes or the earlier read was unreliable; a missing, unreadable, or conflicting required reference stops that stage.
2. Establish one `product`, `phase`, or `feature` scope and one non-reserved lowercase ASCII kebab-case stable topic. Use that same topic in the confirmed summary, PRD frontmatter, default path, and handoff. When selected by `routing-development-workflows`, accept its route handoff separately from the canonical requirements state and preserve `workflow_route` plus the observed risk facts. Only `standard | full` are valid PRD routes; a missing or unreliable route defaults to `full`. Ask one to three independent questions in one turn only when no answer changes another question's applicability, options, meaning, priority, or necessity. Ask only one decisive question when its answer selects the next branch; preserve partial answers and reassess the remaining dependencies.
3. Do not create the PRD until understanding confidence is at least 95 and the user explicitly confirms the current requirements-understanding summary. Confidence does not replace confirmation.
4. After both understanding gates pass, create or update the PRD with [assets/prd-template.md](assets/prd-template.md). Persist the reliable route and risk facts in `## 工作流分流` without adding them to frontmatter or the canonical eight-field handoff. Keep architecture, API, database design, code files, and implementation tasks out of the PRD.
5. Self-review the current PRD, dispatch a fresh read-only reviewer, fix every finding, and re-review the latest file. Independent review does not equal user approval.
6. After independent approval, direct the user to the current file and ask them to explicitly approve it. Open `specification_gate` only when the current PRD retains all understanding and document approvals. Write and validate the current approval metadata before building the complete canonical English eight-field handoff.
7. Classify the reply before rendering. An `ordinary-clarification` uses the local [scripts/render_handoff.py](scripts/render_handoff.py) `compact` view and exactly three consecutive lines. A `checkpoint`, `blocked`, approval, document-stage completion, or downstream transition uses its `full` view. A progress-only update is not ordinary clarification and conservatively uses full; when classification is uncertain, conservatively use full. Requirements-understanding summary confirmation and PRD approval are checkpoints. Preserve canonical state and stop the transition if the renderer fails; never emit partial stdout.
8. When `specification_gate` is open and the Chinese view is valid, use the frozen canonical English handoff to select the runtime-exposed `creating-development-specs-and-plans` skill capability in the same session. Pass the explicit `requirements_path`, `requirements_topic`, `requirements_scope`, complete canonical eight-field handoff, and the route handoff separately. If the capability is unavailable, report the capability gap without searching installation paths or changing the approved PRD.
9. Follow the response ownership rules in the review reference: full replies that do not transition end with the one authoritative Chinese eight-field view; ordinary clarification ends with only the compact three-line view. After a successful downstream transition, the downstream Chinese fourteen-field view owns the final response while the canonical English eight fields remain its machine input prefix.

## Hard Gates

- Do not combine independent product topics into one PRD. Keep topic and path unresolved until the user chooses.
- Treat missing, unreadable, duplicate, conflicting, or unsupported metadata as unknown; never upgrade it to pending or approved.
- A material change resets affected approval states. Reassess confidence truthfully; a score at or above 95 still does not replace confirmation of the updated summary.
- A material route change or material change to its risk facts resets independent review and user approval. Do not silently downgrade `full` to `standard`.
- Never use the Chinese view to open a gate or reconstruct machine state. On mapping failure, preserve the canonical snapshot, emit no partial or fallback handoff, and stop before downstream selection.
- This skill does not create the design spec or implementation plan and does not implement target code. It may select the runtime-exposed skill capability only after the approved handoff is validated.
- Do not read sibling skill source, inspect sibling skill installation directories, infer fixed local paths, or change external state.
