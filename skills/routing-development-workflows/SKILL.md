---
name: routing-development-workflows
description: Use when a development request enters dw without an explicit workflow entry and Codex must route it to fast bounded implementation, standard product and technical planning, full gated development, or a blocked result.
---

# Routing Development Workflows

## Overview

Choose one efficient, risk-matched entry into the development workflow. Own only classification and handoff. Do not create downstream artifacts or execute the selected workflow.

## Applicability

This router is not applicable when the current request contains an explicit workflow entry. Preserve an explicit request for product requirements, an approved PRD's specification or plan, a development prompt, an explicitly approved bounded implementation, or AGENTS rule governance by selecting the matching runtime-exposed capability directly, outside this router's applicability. Do not invoke this router or emit its canonical handoff for that request.

Direct entries remain `creating-product-requirements`, `creating-development-specs-and-plans`, `generating-development-prompts`, `implementing-bounded-changes`, or `managing-agents-rules`; this list names existing capabilities and does not extend the route enum.

Otherwise classify the request as exactly one of `fast | standard | full | blocked` using [references/routing-policy.md](references/routing-policy.md).

## Workflow

1. Read the routing policy completely, then inspect applicable repository rules and only the repository evidence needed to establish route facts. Do not search above the repository root.
2. Preserve the user's requested outcome and explicit values. Record confirmed implementation approval separately from agreement with analysis, investigation, or design.
3. Establish the scope summary, observable result, open product or technical choices, repository validation seam, and every observed or unknown risk fact. Never convert an unknown into a favorable absence.
4. Choose exactly one route. Do not start the downstream capability while facts needed for a safe choice are missing.
5. Emit exactly one canonical handoff in this order:

   ```text
   workflow_route: fast | standard | full | blocked
   scope_summary: <confirmed concise scope>
   risk_facts: <observed risks and material unknowns, or none>
   implementation_approval: approved | pending | not-applicable | unknown
   destination_capability: <runtime capability name or null>
   next_action: <one action>
   ```

6. Select only a runtime-exposed capability. If the selected capability is unavailable, change the result to `blocked`, retain the classification evidence, and report the capability gap without searching installation paths.

## Handoff Boundaries

- `fast` selects `implementing-bounded-changes` only while every fast condition and explicit implementation approval remain current.
- `standard` selects `creating-product-requirements` with the route handoff so its approved PRD can enter standard technical-package planning.
- `full` selects `creating-product-requirements` with the observed high-risk facts and preserves the existing sequential gates.
- `blocked` selects no downstream capability and names the missing authority, evidence, rule access, or runtime capability.
- Explicit workflow entries select their named capability outside this router and produce no `workflow_route` value.

## Hard Boundaries

- Do not create a PRD.
- Do not create a technical specification.
- Do not create an implementation plan.
- Do not modify production files, tests, configuration, documentation, rules, or external state.
- Do not infer implementation approval from a route decision.
- Do not emit a router handoff for an explicit workflow entry.
- Do not read sibling skill source, inspect sibling installation directories, depend on plugin-cache paths, or call another skill through a fixed path.
- Do not turn task size alone into a risk fact. Route from observable boundaries and unknowns.
