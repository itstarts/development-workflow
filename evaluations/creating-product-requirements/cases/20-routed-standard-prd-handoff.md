总路由已经为当前普通功能选择 `standard`，下面是与 requirements 八字段分离的当前 route handoff：

workflow_route: standard
scope_summary: 为订单列表增加按审批状态导出的产品规则
risk_facts: 普通局部功能；未观察到 full 路由边界
implementation_approval: not-applicable
destination_capability: creating-product-requirements
next_action: 创建并评审 PRD

我确认当前 requirements-understanding summary：运营人员需要按当前可见的审批状态导出订单；未选择状态时保持现有导出；不改变审批状态定义、权限或导出格式。稳定主题是 `order-export-filter`，范围是 `feature`，当前理解置信度为 98。

请在 `docs/requirements/2026-07-20-order-export-filter.md` 创建这一个 PRD，完成当前阶段该做的检查和独立评审，然后让我批准当前文件。不要把这次摘要确认当成 PRD 用户批准，不要创建 spec、plan、代码、用户可见 task/thread，也不要搜索兄弟 skill 路径。
