---
document_type: design
topic: order-approval
requirements_path: docs/requirements/2026-07-12-order-approval.md
requirements_topic: order-approval
requirements_scope: feature
requirements_understanding_confidence: 97
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
user_approval: approved
approved_at: 2026-07-12
independent_review: approved
independent_reviewer: fixture-spec-reviewer
independent_reviewed_at: 2026-07-12
---

# Order Approval Design

Add an explicit pending → approved/rejected workflow. Only users with the `order-approver` role can decide. Rejected orders may be resubmitted. Notify the order owner through the existing in-app notification service.
