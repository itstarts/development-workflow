# Migration Baseline Case 05 — Selected Output

Sanitization: the ephemeral fixture prefix was replaced with `/workspace/order-service`.

- Spec：[docs/specs/2026-07-12-order-approval-design.md](/workspace/order-service/docs/specs/2026-07-12-order-approval-design.md)，用户批准和独立评审均为 `approved`。
- Plan：[docs/plans/2026-07-12-order-approval.md](/workspace/order-service/docs/plans/2026-07-12-order-approval.md)，评审状态同时记录为 `approved` 和 `changes-requested`。

现在不能开始实现，因为 plan 尚无有效的独立评审批准状态。
