---
document_type: product-requirements
topic: durable-order-archive
scope_type: feature
understanding_confidence: 98
understanding_user_confirmation: approved
user_approval: approved
independent_review: approved
independent_reviewer: fixture-product-reviewer
independent_reviewed_at: 2026-07-18
approved_at: 2026-07-18
---

# Durable Order Archive Product Requirements

An operator can save an editable order and start a background archive. A save conflict preserves the operator's draft. An archive is published only from a current complete order snapshot. Failed or stale archive attempts do not replace the last completed archive. The client can distinguish retryable editing conflicts, failed background work, and successful completion without reading server logs.
