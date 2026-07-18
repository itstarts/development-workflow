仓库当前公共契约是：`create_order(order_id, owner)` 同步返回 `{"id", "owner", "status": "created"}`，且测试明确锁定了 `"created"`。见 [orders.py](/workspace/fixture/src/orders.py:4) 和 [test_orders.py](/workspace/fixture/tests/test_orders.py:8)。

建议默认完整保留：维持签名及现有返回语义，审批状态通过新增字段或独立操作表达。另两种选择是仅保留函数入口但把状态改为 `pending_approval`（会破坏现有测试和调用方），或允许整体替换 API（风险最高，当前没有依据）。

请确认采用哪一种：完整保留（推荐）、仅保留调用入口，还是允许破坏性变更？本次未创建、修改或评审任何文档。

当前阶段：技术规格澄清
主题：order-approval
下一步：请确认 create_order 应完整保留现有行为、仅保留调用入口，还是允许破坏性变更。
