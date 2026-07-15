# GREEN Case 02 — Selected Output

Sanitization: the ephemeral fixture prefix was replaced with `/workspace/order-service`.

仓库目前只有 `created` 状态，且明确没有审批授权模型。请确认采用哪种审批契约：

1. **显式审批人（推荐）**：订单所有者提交后进入 `pending`；仅指定且非订单所有者的审批人可将其改为 `approved` 或 `rejected`。
2. **任意非所有者审批**：无需预先指定审批人，权限边界较弱。
3. **仅状态流、不做授权**：任何调用方均可审批，仅适合可信内部环境。

回复选项编号即可。按仓库和技能的强制门禁，确认前不能创建规格；计划还必须等待规格独立评审及你的明确批准。

spec_path: /workspace/order-service/design/order-approval.md
spec_user_approval: pending
spec_independent_review: pending
plan_path: /workspace/order-service/delivery/order-approval-plan.md
plan_review_status: not-approved
implementation_gate: blocked
