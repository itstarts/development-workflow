PRD 门状态为 `unknown`：`independent_review` 元数据重复且冲突，并包含无效状态 `changes-requested`。因此 spec 门被阻塞，未创建或修改 spec；仓库无变更。

```text
requirements_path: /workspace/fixture/docs/requirements/2026-07-12-order-approval.md
requirements_topic: order-approval
requirements_scope: feature
requirements_understanding_confidence: 97
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: unknown
specification_gate: blocked
spec_path: /workspace/fixture/docs/specs/2026-07-15-order-approval-design.md
spec_user_approval: pending
spec_independent_review: pending
plan_path: null
plan_review_status: not-approved
implementation_gate: blocked
```