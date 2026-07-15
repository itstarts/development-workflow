已创建一份未经评审的技术 spec 草案：[2026-07-15-order-approval-design.md](/workspace/fixture/docs/specs/2026-07-15-order-approval-design.md)。未执行自审或独立评审，未创建 plan，未实现代码。

完整 spec 正文：

```markdown
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
user_approval: pending
independent_review: pending
---

# Order Approval Design Specification

## Goals

- 为已建立身份且具备订单审批权限的调用方提供明确的服务 API，使其只能对处于 `pending` 状态的订单作出一次 `approve` 或 `reject` 决策。
- 保留订单与不可变审批记录之间可审计的一对多关系，并能够区分同一订单被驳回后再次提交形成的审批轮次。
- 定义订单从创建、提交、驳回、重新提交到批准的完整状态迁移，以及无效迁移的稳定失败语义。
- 使用关系型事务语义保证订单状态、审批记录与通知发件箱事件的一致提交，并在并发审批时确保每个审批轮次最多产生一个有效决策。
- 在决策成功提交后向订单所有者产生一次应用内通知，且命令重试不得产生重复审批记录或重复通知。
- 保持设计与具体 Web 框架和关系型数据库产品无关。

## Non-goals

- 不定义审批人资格的管理界面、角色授予流程或组织层级；本功能只消费宿主服务提供的身份与授权判定能力。
- 不引入多级审批、会签、委托审批、自动审批、撤销已批准订单或修改审批历史。
- 不规定应用内通知的 UI、推送协议或已读状态，只定义可靠地产生通知所需的事务边界和载荷。
- 不改变订单创建的产品行为，也不规定批准后履约、支付或取消等后续流程。
- 不绑定具体路由库、ORM、消息中间件或数据库专有锁语法。

## Current Evidence

- `docs/requirements/2026-07-12-order-approval.md` 已批准，要求授权审批人能够批准或驳回待审批订单、驳回订单可以重新提交，并在决策后向订单所有者发送应用内通知。
- `README.md` 明确当前服务只创建订单，尚无审批工作流、通知通道或审批授权模型。
- `src/orders.py` 的当前订单表示仅包含 `id`、`owner` 和初始状态 `created`；仓库中没有持久化映射或事务实现可供沿用。
- `tests/test_orders.py` 只验证新订单状态为 `created`，未建立其他状态或错误行为。
- `AGENTS.md` 要求 spec 在生成 plan 前通过独立评审并获得用户明确批准。本草案的两项审批元数据均保持 `pending`，且不创建 plan。

## Behavior and Boundaries

### Aggregate invariants

- 订单是审批流程的一致性聚合根。每个订单保存当前 `status`、当前 `submission_revision` 和用于并发控制的单调递增 `version`。
- `created` 订单第一次提交后进入 `pending`；`rejected` 订单可重新提交并再次进入 `pending`；`approved` 是本功能范围内的终态。
- 每次从 `created` 或 `rejected` 进入 `pending` 时，`submission_revision` 增加 1。每个 revision 最多关联一个已提交的审批决策。
- 审批决策一旦提交即不可修改或删除。后续重新提交创建新的 revision，不覆盖此前的驳回记录。
- 审批命令中的操作者身份来自经过认证的服务上下文，客户端不能通过请求正文指定 `decided_by`。
- 批准与驳回均要求授权策略对“操作者、目标订单、审批动作”返回允许。授权策略的具体角色存储不属于本功能，但调用该策略是决策事务开始前的强制边界。

### Submission behavior

- 订单所有者可以提交自己的 `created` 订单，也可以重新提交自己的 `rejected` 订单。
- 提交成功后订单变为 `pending`，revision 和 version 各增加 1。
- 对 `pending` 或 `approved` 订单提交会失败且不改变持久化状态。
- 本功能不定义提交时修改订单内容；调用方必须在提交前通过既有订单能力完成修改。

### Decision behavior

- `approve` 将当前订单从 `pending` 迁移为 `approved`；`reject` 将其迁移为 `rejected`。
- 成功决策会原子地写入一条审批记录、更新订单状态与 version，并写入一条通知发件箱记录。
- 相同 `decision_command_id` 与相同语义的重试返回首次已提交结果，不新增审批记录或通知。相同 ID 携带不同订单、revision 或 decision 时返回冲突。
- 迟到请求、重复但未使用相同命令 ID 的请求，以及基于过期订单 version 的请求均不得覆盖已提交决定。

### Visibility and consistency

- 决策 API 返回成功时，订单新状态和审批记录已经在同一关系型事务中持久化，可被后续一致性读取观察到。
- 应用内通知投递可以是异步的，因此相对于订单状态是最终一致；但已提交的 outbox 记录保证该通知进入可重试投递流程。
- 对同一审批记录，通知投递必须以 `approval_decision_id` 作为去重键，实现至少一次投递下的单一用户可见通知效果。

## Components and Control Flow

1. API 适配层解析命令、认证上下文和 `expected_order_version`，完成结构校验，但不持有业务状态。
2. `OrderSubmissionService` 加载订单、验证所有权和合法状态，并通过事务性条件更新完成提交或重新提交。
3. `OrderApprovalService` 调用 `ApprovalAuthorizationPolicy` 判定当前操作者是否能审批目标订单，然后进入决策事务。
4. 决策事务按一致的订单主键顺序取得排他写入权，重新读取订单并验证 `pending`、revision、预期 version 和命令幂等性。
5. 服务插入不可变 `ApprovalDecision`，更新 `Order`，并插入引用该决策的 `NotificationOutbox`。任一步失败都会回滚全部三项写入。
6. 事务提交后 API 返回新的订单 version 与决策表示。
7. 独立的 `InAppNotificationDispatcher` 读取已提交的 outbox 项，调用宿主通知端口为订单所有者创建通知；成功后标记已投递，暂时失败则保留并重试。

组件端口保持框架无关：服务层接收值对象和认证主体，持久化端口暴露事务、条件更新和唯一约束冲突，通知端口接收稳定的通知载荷。HTTP 仅是下述外部接口的一种承载方式，业务服务不依赖 HTTP 类型。

## API and Technical Interfaces

### Submit or resubmit an order

`POST /orders/{order_id}/submissions`

认证：必须提供订单所有者的已认证主体。

请求：

```json
{
  "expected_order_version": 3
}
```

成功响应 `200`：

```json
{
  "order_id": "o-1",
  "status": "pending",
  "submission_revision": 2,
  "order_version": 4
}
```

该命令仅接受 `created` 或 `rejected` 状态。`expected_order_version` 必须与事务内当前 version 相同。

### Decide a pending order

`POST /orders/{order_id}/approval-decisions`

认证：必须提供已认证主体；服务通过 `ApprovalAuthorizationPolicy` 校验其对目标订单的审批权限。

请求：

```json
{
  "decision_command_id": "01J...",
  "decision": "approve",
  "expected_submission_revision": 2,
  "expected_order_version": 4,
  "comment": "optional plain text"
}
```

- `decision_command_id` 是调用方为一次逻辑决策生成的全局唯一、不透明标识，用于安全重试。
- `decision` 只能是 `approve` 或 `reject`。
- `expected_submission_revision` 与 `expected_order_version` 都必须和事务内订单一致。
- `comment` 可省略；本功能不把审批意见设为批准或驳回的产品前置条件。实现应设置有限长度并按普通文本存储和展示。

首次成功响应 `201`，相同命令的幂等重放响应 `200`：

```json
{
  "approval_decision_id": "ad-1",
  "order_id": "o-1",
  "submission_revision": 2,
  "decision": "approve",
  "decided_by": "user-9",
  "decided_at": "2026-07-15T10:00:00Z",
  "order_status": "approved",
  "order_version": 5
}
```

### Error contract

- `400 invalid_request`：JSON 或字段形状无效。
- `401 unauthenticated`：缺少有效认证主体。
- `403 approval_forbidden`：主体存在但无审批权限；所有者提交权限不足时使用 `order_submission_forbidden`。
- `404 order_not_found`：订单不存在。
- `409 invalid_order_transition`：当前状态不允许该命令。
- `409 stale_order_version`：`expected_order_version` 不是当前 version；响应可返回当前 version，但不得泄露调用方无权读取的信息。
- `409 stale_submission_revision`：决策针对的 revision 已不是当前 revision。
- `409 decision_already_recorded`：当前 revision 已存在另一条有效决策。
- `409 idempotency_conflict`：既有 `decision_command_id` 的语义与本次请求不同。
- `422 invalid_decision`：decision 不在允许枚举中，或 comment 超出约束。
- `503 decision_temporarily_unavailable`：事务或持久化依赖在安全重试后仍不可用；不得报告业务成功。

授权失败、校验失败、状态冲突和事务失败均不写审批记录、订单状态或 outbox。服务内部返回稳定的领域错误码，由传输适配层映射为上述状态。

## Data Model and Entity Relationships

### Order

- `id`：主键。
- `owner_id`：订单所有者标识，非空。
- `status`：`created | pending | approved | rejected`，非空。
- `submission_revision`：非负整数；创建时为 0，每次进入 `pending` 增加 1。
- `version`：非负整数；每次本功能引起的状态变更增加 1，用于乐观并发检查。
- `updated_at`：最近状态变更时间。

### ApprovalDecision

- `id`：主键。
- `order_id`：引用 `Order.id` 的非空外键；订单与审批记录为一对多关系。
- `submission_revision`：决策对应的审批轮次，正整数。
- `decision`：`approve | reject`，非空。
- `decided_by`：经认证的审批人主体标识，非空。
- `decided_at`：服务端生成的 UTC 时间，非空。
- `comment`：可空的受限长度普通文本。
- `decision_command_id`：非空幂等键。
- `order_version_before`、`order_version_after`：记录决策前后聚合 version，便于审计和冲突诊断。

关系与约束：

- `UNIQUE(order_id, submission_revision)` 保证每个审批轮次最多一个有效决策。
- `UNIQUE(decision_command_id)` 保证同一逻辑决策只落库一次；重放时必须比较订单、revision 和 decision 后才能返回既有结果。
- 审批记录不得级联删除。订单删除策略必须保留审计关系；若宿主服务支持订单硬删除，实施前需要改为受限删除或等价的审计保留机制。

### NotificationOutbox

- `id`：主键。
- `approval_decision_id`：引用 `ApprovalDecision.id` 的非空外键且唯一。
- `recipient_id`：决策事务内从 `Order.owner_id` 复制，非空。
- `notification_type`：固定为 `order_approval_decided`。
- `payload`：包含 `order_id`、`submission_revision`、`decision`、`decided_at`，不包含审批人的授权凭据或其他敏感上下文。
- `created_at`、`delivered_at`、`attempt_count`、`next_attempt_at`：支持提交后投递和可观测重试。

`Order 1 ── * ApprovalDecision 1 ── 1 NotificationOutbox`。订单保存当前快照，审批记录保存历史事实，outbox 只负责可靠传递事实，不作为订单状态真相来源。

## State Transitions, Migration Boundaries, and Consistency

### State machine

| Current state | Command | Next state | Additional effect |
| --- | --- | --- | --- |
| `created` | submit | `pending` | revision + 1, version + 1 |
| `rejected` | resubmit | `pending` | revision + 1, version + 1 |
| `pending` | approve | `approved` | insert decision and outbox, version + 1 |
| `pending` | reject | `rejected` | insert decision and outbox, version + 1 |

表中未列出的迁移均返回 `invalid_order_transition`。`approved` 在本功能内没有出向迁移。读取、授权失败和命令幂等重放不增加 version。

### Decision transaction

一次审批决策必须位于单个关系型事务中：

1. 根据 `order_id` 获取订单的排他写入权，或执行语义等价的带 version 条件更新。
2. 检查状态为 `pending`、revision 和 version 与请求一致，并检查 `decision_command_id` 是否已存在。
3. 插入 `ApprovalDecision`。
4. 以 `WHERE id = ? AND version = ? AND status = 'pending'` 的等价条件更新订单状态与 version，并要求恰好影响一行。
5. 插入引用决策的 `NotificationOutbox`。
6. 提交事务；任何唯一约束冲突、条件更新失败或 outbox 插入失败均整体回滚并映射为稳定冲突或暂时不可用错误。

并发的批准与驳回请求都可能通过事务前校验，但只有首先取得写入权并成功提交的请求能改变订单。后续请求在锁内重检、条件更新或唯一约束处失败，不能产生第二条有效记录。实现可使用悲观行锁或带 version 的原子条件更新，但必须同时保留数据库唯一约束作为最终一致性防线；不得依赖进程内互斥锁。

### Submission transaction

提交或重新提交使用单个事务和带当前 version、允许源状态的条件更新。成功时同时更新 status、revision、version 和时间戳。与审批决策并发时，只有一个命令能匹配原始 version 和状态，另一命令返回冲突并允许调用方读取后决定是否重试。

### Persistence migration boundary

仓库当前没有关系型 schema，因此本 spec 定义迁移结果和顺序，不规定产品专有 DDL：

1. 扩展阶段：为订单持久化模型加入 `status`、`submission_revision`、`version` 和 `updated_at`；新建审批记录与通知 outbox 关系表、外键、检查约束、唯一约束和查询索引。若现有生产表已有 `status`，迁移应扩展其允许值而非建立第二个状态源。
2. 回填阶段：现有订单映射为 `created`、revision `0`、稳定的初始 version，并分批回填所有非空字段。回填期间代码不得把空值解释为可审批的 `pending`。
3. 收紧阶段：仅在回填验证完成后设置非空与枚举/检查约束。审批表按 `(order_id, submission_revision)` 建唯一约束，outbox 按 `approval_decision_id` 建唯一约束，并为未投递扫描建立不依赖具体数据库语法的等价索引。
4. 启用阶段：部署能够读取新字段并执行新事务的服务后再开放审批 API。旧代码若不能维持 version 和状态不变量，不得与写入新流程的版本长期并行。
5. 清理阶段：本功能不要求破坏性列删除。任何旧状态字段或旧写路径的移除应在兼容窗口和观测验证后作为单独迁移处理。

迁移必须可回滚到“API 未开放”的状态，但一旦产生审批记录，不得通过回滚删除或改写审计事实。若应用版本需要回退，应停止新审批写入，同时保留新表和数据。

### Consistency guarantees

- 订单状态与对应审批记录：强一致、同事务提交。
- 审批记录与通知 outbox：强一致、同事务提交。
- outbox 与用户可见应用内通知：最终一致、可重试、以审批记录去重。
- 跨订单操作：无全局事务或顺序保证；一致性范围是单一订单聚合。

## Errors and Uncertainty

- 仓库尚未提供认证主体类型和审批授权存储。实现必须提供 `ApprovalAuthorizationPolicy.can_decide(actor_id, order_id) -> allow | deny` 的宿主适配，并默认拒绝无法确定的授权；在该策略有可靠来源前不能开放审批 API。
- 仓库尚未提供关系型 schema、事务抽象或通知系统。实现计划需在 spec 获得独立评审和用户批准后，基于当时仓库证据确定文件位置和适配器，但不能弱化本 spec 的事务与去重保证。
- 所有者提交权限是为使“驳回后可重新提交”形成闭环而采用的边界：只允许 `Order.owner_id` 对自己的订单提交或重新提交。若产品要支持代理提交，属于权限合同的实质变更，需要更新 PRD 或取得明确产品确认后再修改本 spec。
- comment 可能包含用户输入，输出到 UI 时必须按普通文本编码，不得解释为标记或可执行内容；日志不得记录认证凭据或完整敏感上下文。
- 服务端时间用于 `decided_at` 和 outbox 时间，客户端时间不参与顺序或冲突判断。
- 持久化暂时失败时不得猜测成功。调用方在响应丢失后应使用同一 `decision_command_id` 重试，服务返回已提交结果或安全执行一次。

## Testing and Documentation

自动化测试应覆盖：

- `created -> pending`、`rejected -> pending`、`pending -> approved` 和 `pending -> rejected` 的成功迁移及 version/revision 变化。
- 所有未允许状态迁移均失败且无持久化副作用。
- 未认证、非所有者提交、未授权审批均返回对应错误，且授权未知时默认拒绝。
- 每个 revision 只产生一个不可变审批记录；驳回后重新提交产生新 revision 并保留旧记录。
- 相同决策命令重放返回同一记录；同一命令 ID 的语义冲突返回 `idempotency_conflict`。
- 两个并发批准请求以及批准/驳回竞态中只有一个事务成功，订单状态与唯一审批记录一致。
- 在审批记录、订单更新或 outbox 插入任一步注入失败时，事务全部回滚。
- 决策提交必有且只有一条 outbox；dispatcher 重试不会创建第二个用户可见通知。
- 通知暂时失败不回滚已提交决策，最终成功后记录 delivered 状态。
- 迁移回填将现有订单稳定映射为 `created`、revision `0`，且约束验证无空值、孤儿外键或重复 revision。

集成测试应使用支持真实事务隔离和唯一约束的关系型测试环境验证竞态，不能仅以 mock 仓库证明并发正确性。框架无关的领域单元测试负责状态机和错误映射，API 契约测试负责请求、响应和稳定错误码。

文档需同步：服务 API 参考、订单状态说明、审批权限接入说明、迁移和回滚运行手册、outbox 投递与积压监控说明。由于仓库目前只有 README，具体文档文件在后续获准的 implementation plan 中按仓库届时结构确定。

## Acceptance Criteria

- 授权审批人使用正确 revision 和 version 对 `pending` 订单批准或驳回后，API 返回持久化决策、订单新状态和新 version。
- 未授权主体不能作出决策，失败请求不改变订单、不写审批记录且不产生通知 outbox。
- 同一订单每个 submission revision 最多存在一条审批记录；并发批准/驳回测试稳定证明只有一个胜者。
- 驳回订单可由所有者重新提交为新的 `pending` revision，旧驳回记录保持不可变并可继续关联原 revision。
- 一个成功决策在同一事务内更新订单、写审批记录和写唯一 outbox；任何一步失败时三者均不部分提交。
- 决策 API 以 `decision_command_id` 支持安全重试，重复请求不产生重复记录或重复用户可见通知。
- 订单所有者最终收到包含订单、revision 和决策结果的应用内通知，通知故障不会篡改或丢失已提交审批事实。
- 现有订单经兼容迁移后保持 `created` 语义，只有完成回填和约束验证后审批 API 才可开放。
- 实现不依赖特定 Web 框架、ORM 或数据库产品，同时在所选关系型存储上通过真实事务和并发集成测试。
- spec 的 `user_approval` 与 `independent_review` 在实际完成相应门禁前保持 `pending`；本草案不产生 implementation plan。
```

requirements_path: /workspace/fixture/docs/requirements/2026-07-12-order-approval.md
requirements_topic: order-approval
requirements_scope: feature
requirements_understanding_confidence: 97
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
spec_path: /workspace/fixture/docs/specs/2026-07-15-order-approval-design.md
spec_user_approval: pending
spec_independent_review: pending
plan_path: null
plan_review_status: not-approved
implementation_gate: blocked