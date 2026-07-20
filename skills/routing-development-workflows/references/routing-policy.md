# Routing Policy

## Explicit Workflow Entry

An explicit workflow entry is outside this router's applicability. Preserve the user's named entry by selecting the matching runtime-exposed capability directly. Do not invoke this router, do not reclassify the request, and do not emit a canonical router handoff or any `workflow_route` value. Merely mentioning dw or using ordinary development language is not an explicit entry.

## Fast

Choose `fast` only when every fast condition is confirmed:

1. The user gave explicit implementation approval for the current scope.
2. The goal, non-goals, and observable result are stable with no unresolved product or technical choice.
3. The change is local and ordinarily reversible and does not alter a shared abstraction or cross-module core rule.
4. No public contract, dependency, architecture, data model, migration, permission, security, money, concurrency, transaction, consistency, production configuration, or external state boundary is present.
5. One focused validation seam or deterministic static check can sufficiently prove the result.
6. Applicable repository rules do not require a stronger workflow or independent review.

If any fast condition is false, do not choose `fast`. If approval alone is missing while every other fast fact is established, use `blocked` and request that authority without creating documents or starting implementation.

## Standard

Choose `standard` for an ordinary feature or product behavior that needs requirements or technical clarification but has no confirmed full-route risk. Route to `standard` when any material routing fact is unknown; unknown never means safe enough for `fast`. Ask only the decisive missing question when its answer can change whether the request remains standard or becomes full.

The standard path retains PRD independent review and user approval. After the approved PRD, it may create a spec and plan as one technical package under the downstream package-review contract. A route decision does not approve any document or implementation.

## Full

Choose `full` when evidence confirms any of these material boundaries:

- a public contract, API, schema, protocol, or compatibility promise;
- architecture, dependency, shared abstraction, or cross-module core rule;
- data model, migration, irreversible or recovery-sensitive data behavior;
- permission, security, trust boundary, sensitive data, or money flow;
- concurrency, transaction, consistency, locking, or shared-state synchronization;
- production configuration, external state, deployment, release, or long-running service behavior;
- major unresolved product meaning whose choices would materially change the system boundary.

Preserve the current PRD, specification, plan, approval, validation, and review gates. The router names observed risks but does not design their solution.

## Blocked

Choose `blocked` only when a missing authority, unreadable applicable rule, unresolved repository root, unavailable required runtime capability, or other deterministic condition prevents a safe handoff. Product or technical uncertainty with a readable repository normally routes to `standard`, not `blocked`.

## Reclassification

Every downstream workflow must preserve the routed scope and risk facts. When implementation or repository evidence crosses a route boundary, stop the current route, reclassify from current facts, and do not reuse the earlier approval for the expanded scope. Never downgrade `full` or `standard` merely to avoid documentation, review, or validation time.
