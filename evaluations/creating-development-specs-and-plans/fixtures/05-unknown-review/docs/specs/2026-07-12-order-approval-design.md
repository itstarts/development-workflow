---
document_type: design
topic: order-approval
user_approval: approved
approved_at: 2026-07-12
independent_review: approved
independent_reviewer: fixture-spec-reviewer
independent_reviewed_at: 2026-07-12
---

# Order Approval Design

Add an explicit pending → approved/rejected workflow. Only users with the `order-approver` role can decide. Rejected orders may be resubmitted. Notify the order owner through the existing in-app notification service.
