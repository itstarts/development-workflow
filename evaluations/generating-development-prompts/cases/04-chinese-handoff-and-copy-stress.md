以下十四字段英文 canonical 快照已经重新验证，implementation gate 已开放：

requirements_path: docs/requirements/2026-07-17-example.md
requirements_topic: example
requirements_scope: feature
requirements_understanding_confidence: 98
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
spec_path: docs/specs/2026-07-17-example-design.md
spec_user_approval: approved
spec_independent_review: approved
plan_path: docs/plans/2026-07-17-example.md
plan_review_status: approved
implementation_gate: open

当前会话已有大量无关上下文，批准任务适合隔离到新会话执行。请按 `new-session` 路由并生成完整可复制提示词，但不要创建、打开或发送新会话。自动路由回复末尾只显示同一快照的中文十四字段视图，状态块必须在 renderer 代码框之外。

提示词正文需保留以下压力内容：中文、English、café、naïve、Δ、🚀、全角标点「交接」，长路径 docs/specs/2026-07-17-example-design.md，以及连续六个反引号 ``````。这些反引号来自动态外部字段，必须遵循 renderer 既有 inert-text 合同，可逆编码为六个连续的 `\u0060` 字面序列；不得绕过 `render(payload)` 或修改 renderer/template 来强行保留原始反引号。复制出的动态 fence 内完整正文必须与 renderer stdout 的 fence 内正文逐字一致，且不得增加外层 fence、语言标记、前导空格、中文状态块或末尾解释。
