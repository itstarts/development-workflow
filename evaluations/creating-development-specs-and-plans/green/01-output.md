# GREEN Case 01 — Selected Output

Sanitization: the ephemeral fixture prefix was replaced with `/workspace/order-service`.

仓库明确没有现成审批授权模型，而“谁能审批”会直接改变权限与安全边界。请先选择 MVP 方案：

1. `order_approver` 固定角色（推荐）：边界清晰、实现最小，但需调用方提供可信身份/角色。
2. 提交时为每个订单指定审批人：更灵活，但需要新增审批人字段及防篡改规则。
3. 订单所有者的直属主管：符合常见流程，但当前仓库没有组织架构数据，会引入外部依赖。

请回复 `1`、`2` 或 `3`。之后我会继续逐项确认通知方式和驳回后能否重提。依照仓库及技能门禁，目前不能生成 spec、plan 或开始编码。

spec_path: /workspace/order-service/docs/specs/2026-07-15-order-approval-design.md
spec_user_approval: pending
spec_independent_review: pending
plan_path: /workspace/order-service/docs/plans/2026-07-15-order-approval.md
plan_review_status: not-approved
implementation_gate: blocked
