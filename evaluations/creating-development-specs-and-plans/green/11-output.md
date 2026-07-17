已创建未评审的技术规格草案：[2026-07-17-order-approval-design.md](/workspace/fixture/docs/specs/2026-07-17-order-approval-design.md)。

未执行自审或独立评审，未创建计划，未实现或提交代码。两项规格审批状态均保持 `pending`。

完整规格正文如下：

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

# 订单审批技术规格

## 目标

- 为单个订单提供可审计的提交审批、批准和拒绝能力；只有授权审批人可以对处于待审批状态的订单作出决定。
- 允许被拒绝的订单重新提交，并以新的审批记录保留每次提交和决定的完整历史。
- 在审批决定持久化后，为订单所有者可靠地产生站内通知。
- 在重复请求和并发决定下，保证一个审批轮次至多产生一个有效决定，且订单状态、审批记录和通知事件保持一致。

## 非目标

- 不选择具体 Web 框架、关系型数据库产品、ORM、消息代理或站内通知 UI 技术。
- 不定义审批人名单的管理、角色配置或订单写权限规则；本规格只定义调用既有或注入式授权策略的边界。
- 不支持批量审批、多级会签、撤回决定、已批准订单重新开启或跨订单事务。
- 不改变已批准产品需求中的用户范围，也不在本功能内设计通知偏好和已读状态。

## 当前证据

- `docs/requirements/2026-07-12-order-approval.md` 已批准并通过独立评审，要求授权审批人批准或拒绝待审批订单、被拒订单可重新提交，并在决定后通知订单所有者。
- `src/orders.py` 仅提供 `create_order(order_id, owner)`，新订单状态为 `created`；当前没有持久化仓储、审批、授权或通知实现。
- `tests/test_orders.py` 只验证新订单状态为 `created`，没有审批或并发行为覆盖。
- `README.md` 明确当前服务尚无审批工作流、通知通道和审批授权模型。
- `AGENTS.md` 要求规格经独立评审且由用户明确批准后才能生成计划；本草案的两项批准状态均保持 `pending`。

## 行为与边界

订单状态集合为 `created`、`pending`、`approved`、`rejected`。合法转换仅为：

- `created -> pending`：首次提交审批；
- `rejected -> pending`：重新提交，创建新的审批轮次；
- `pending -> approved`：授权审批人批准当前轮次；
- `pending -> rejected`：授权审批人拒绝当前轮次。

`approved` 在本功能内为终态。任何未列出的转换都失败且不产生持久化副作用。每次从 `created` 或 `rejected` 进入 `pending` 都创建一条新的 `ApprovalRecord`；历史记录不覆盖、不删除。订单在任意时刻至多有一个当前待审批记录。

决定成功后立即向调用方返回已提交的订单和审批快照。站内通知采用最终一致投递：决定事务提交即代表业务决定成功，通知通道暂时不可用不会回滚决定；持久化待投递事件会持续重试，直到通知子系统确认接收。通知消费者以事件标识去重，因此允许传输层至少一次投递但用户侧只生成一条决定通知。

所有写入命令都要求已认证的 `actor_id`、非空幂等键和调用方读取到的 `expected_order_version`。同一操作与幂等键使用相同请求参数重试时返回原结果；复用该键但参数不同则失败。时间戳使用 UTC，服务端生成的标识在其实体范围内唯一。

## 组件与控制流

1. 服务 API 校验命令结构、幂等键和预期版本，并读取既有幂等结果；命中同参数结果时直接返回。
2. 提交审批时，`OrderWriteAuthorization` 判断操作者是否具有订单写权限；作出决定时，`ApprovalAuthorization` 判断操作者是否是该订单的授权审批人。授权策略是注入式端口，具体角色或名单存储不属于本规格。
3. 应用服务开启关系型事务，锁定或以条件更新保护目标订单，重新检查版本、当前状态和当前审批记录。
4. 提交命令创建新的 `ApprovalRecord` 并把订单切换为 `pending`；决定命令原子更新当前记录、订单状态和版本，同时写入通知发件箱事件。
5. 同一事务记录幂等回执并提交。任何事务内步骤失败都整体回滚。
6. 独立的发件箱投递器读取已提交事件，调用站内通知端口；成功后记录投递完成，失败则按可观测的退避策略重试。该投递器不修改订单或审批决定。

核心职责边界如下：

- `OrderApprovalService`：编排授权、状态机、事务、幂等和返回结果；
- `OrderRepository` 与 `ApprovalRecordRepository`：在同一关系型事务上下文内读写实体；
- `OrderWriteAuthorization` 与 `ApprovalAuthorization`：返回明确的允许或拒绝结果，依赖不可用时采取拒绝写入的失败关闭策略；
- `NotificationOutbox`：与决定原子写入待投递事件；
- `InAppNotificationPort`：接收稳定事件标识和通知载荷，负责用户可见通知及消费去重。

## API 与技术接口

以下是与传输协议和框架无关的服务契约；适配层可映射为 HTTP、RPC 或进程内调用，但不得改变字段语义和错误码。

### 提交或重新提交审批

`submit_for_approval(command) -> ApprovalSubmissionResult`

输入：

- `order_id: string`：目标订单；
- `actor_id: string`：已认证操作者；
- `expected_order_version: integer`：调用方读取到的订单版本；
- `idempotency_key: string`：调用方生成的非空稳定键。

输出：

- `order_id`、`order_status: pending`、`order_version`；
- `approval_id`、`attempt_number`、`approval_status: pending`、`submitted_by`、`submitted_at`。

该操作仅接受 `created` 或 `rejected` 订单。首次提交和拒绝后重新提交使用同一契约；服务通过递增的 `attempt_number` 区分轮次。

### 作出审批决定

`decide_approval(command) -> ApprovalDecisionResult`

输入：

- `order_id: string` 与 `approval_id: string`：必须共同指向该订单的当前待审批记录；
- `actor_id: string`：已认证且经授权策略允许的审批人；
- `decision: approved | rejected`；
- `reason: string | null`：可选说明，适配层应执行长度上限等基础校验；
- `expected_order_version: integer`；
- `idempotency_key: string`。

输出：

- `order_id`、`order_status`、`order_version`；
- `approval_id`、`attempt_number`、`approval_status`、`decided_by`、`decided_at`、`reason`；
- `notification_event_id`，用于关联决定后的可靠通知。

### 查询审批历史

`get_approval_history(order_id, actor_id, page_token, page_size) -> ApprovalHistoryPage`

结果按 `attempt_number` 降序返回审批记录及稳定的下一页游标。读取权限沿用订单读取授权端口；查询不改变状态，也不等待通知投递。页面大小必须有服务端上限。

### 稳定错误契约

- `NOT_FOUND`：订单或指定审批记录不存在；
- `FORBIDDEN`：操作者未获相应写入、审批或读取授权；
- `INVALID_TRANSITION`：订单状态不允许提交、重新提交或决定；
- `VERSION_CONFLICT`：当前订单版本与预期版本不同；
- `APPROVAL_CONFLICT`：审批记录不是当前轮次、已被决定，或并发请求已先完成转换；
- `IDEMPOTENCY_KEY_REUSED`：同一操作的幂等键对应不同请求指纹；
- `VALIDATION_ERROR`：字段缺失、枚举非法或超出稳定限制；
- `DEPENDENCY_UNAVAILABLE`：授权等同步依赖无法给出可靠结果。

失败响应不得包含部分成功结果。适配层可将这些错误映射到协议状态，但领域错误码保持不变。

## 数据模型与实体关系

### `Order`

- 既有字段：`id`、`owner_id`、`status`；
- 新增持久化字段：`version`（每次状态写入递增）、`current_approval_id`（可空，指向当前待审批记录）；
- 不变量：`status = pending` 时 `current_approval_id` 必须指向一条属于该订单且状态为 `pending` 的记录；其他状态下该字段必须为空。

### `ApprovalRecord`

- `id`：主键；
- `order_id`：非空外键，形成 `Order 1:N ApprovalRecord`；订单拥有审批历史，记录不得改挂到另一订单；
- `attempt_number`：同一订单内从 1 单调递增，与 `order_id` 组成唯一业务键；
- `status: pending | approved | rejected`；
- `submitted_by`、`submitted_at`；
- `decided_by`、`decided_at`、`reason`：待审批时为空，完成决定时一次性写入；
- `created_order_version` 与 `decided_order_version`：记录轮次关联的订单版本，便于审计和诊断。

审批记录的提交字段和已完成决定字段不可变。订单删除策略必须保留审批审计历史；若现有系统允许物理删除订单，迁移后应改为受限删除或等效的保留策略，不能级联删除审批记录。

### `CommandReceipt`

- 以 `operation + idempotency_key` 为唯一键；
- 保存请求指纹、处理结果引用及创建时间；
- 与对应业务写入同事务提交。历史保留期必须不短于客户端可能重试的约定窗口；清理不得影响审批记录。

### `NotificationOutboxEvent`

- `event_id`：主键及通知消费去重键；
- `event_type: order_approval_decided`；
- `order_id`、`approval_id`、`owner_id`、`decision`、`decided_at`；
- `delivery_status`、`attempt_count`、`next_attempt_at`、`delivered_at`；
- 每条已完成审批记录至多关联一条该事件类型，通过关系型唯一约束保证。

`ApprovalRecord` 与 `NotificationOutboxEvent` 为 `1:0..1`：待审批记录没有决定事件，完成决定的记录在事务提交时必须有且仅有一个事件。

## 状态转换、迁移边界与一致性

持久化迁移采用向前兼容的分阶段边界：

1. 以可空或带安全默认值的方式增加订单版本和当前审批引用，创建审批记录、幂等回执和通知发件箱结构及必要索引；此阶段不改变现有创建行为。
2. 将既有订单的 `version` 回填为确定的初始值，并校验既有状态；既有 `created` 订单保留 `created`，不自动生成审批记录或通知。
3. 部署能够同时理解旧订单行与新结构的应用写路径，再启用非空、外键、唯一性和状态检查等关系型约束。若某种约束无法跨数据库产品统一表达，必须由事务内条件写入保证，并以迁移校验查询证明无违规数据后再收紧。
4. 最后启用审批 API 和发件箱投递器。回滚应用版本时不得删除新表或审批历史；需要先停止新审批写入，并保持旧版本不会误解新增状态。

每个命令使用单个本地关系型事务，不引入分布式事务。事务通过行级串行化效果实现，可由悲观锁或带 `version` 条件的原子更新提供，但实现必须满足相同行为：

- 状态检查、审批记录变更、订单版本递增、幂等回执以及决定事件写入要么全部提交，要么全部回滚；
- 两个不同幂等键并发决定同一 `approval_id` 时，只有一个事务可从 `pending` 转换成功；失败方返回 `APPROVAL_CONFLICT` 或在版本先失效时返回 `VERSION_CONFLICT`，不得覆盖胜者；
- 相同幂等键的并发重试只产生一份业务结果、一条决定和一条发件箱事件；
- 提交审批与决定、两次重新提交或订单其他版本化写入发生竞争时，版本检查保证陈旧命令不会基于旧状态提交；
- 数据库提交成功后，订单与审批查询必须立即读到同一决定；通知仅保证最终一致，发件箱积压必须可观测和重试。

## 错误与不确定性

- 授权检查必须在写事务提交前完成，并在依赖无响应时拒绝变更；授权拒绝不得创建审批记录、回执或通知事件。
- API 适配层负责认证并传入不可伪造的主体标识；领域服务不得信任客户端自行声明的审批角色。
- `reason` 可能进入审计记录和站内通知，必须按普通用户输入处理：限制长度、保留原始语义并在展示层转义，不记录认证凭据或其他敏感上下文。
- 发件箱投递失败不改变已经提交的审批结果。达到重试告警阈值时进入人工可观测的失败队列或告警状态，但不得静默丢弃事件。
- 仓库尚无持久化、授权和通知抽象；具体实现必须选择能满足上述端口及事务语义的组件，但不得借此改变本规格的公开契约。
- 产品需求未规定谁可以提交或重新提交；本规格明确沿用订单写权限端口，而不在审批功能中发明新的业务角色。若后续产品决定改变该权限，这是需要重新批准的需求变更。

## 测试与文档

自动化测试至少覆盖：

- 状态机单元测试：四条合法转换、所有非法转换、批准终态和每次重新提交生成新轮次；
- 授权测试：授权审批人可决定，未授权或授权依赖不可用时无任何写入；订单写权限同样约束提交和重新提交；
- 仓储集成测试：订单、审批记录、幂等回执和发件箱事件在同一事务中提交或回滚，外键与唯一性不变量有效；
- 幂等测试：同键同参数重试返回原结果，同键异参数失败，重试不重复创建记录或事件；
- 并发测试：用同步屏障同时发出两个相反决定，断言仅一个成功、最终状态匹配胜者且只有一条事件；并发重新提交和陈旧版本写入也必须冲突；
- 通知测试：决定提交后即使通知端口首次失败，发件箱仍保留并可重试；重复投递只生成一条用户通知；
- 迁移测试：从仅含既有 `created` 订单的数据集升级，确认回填、约束校验和旧数据可读，且不会凭空产生审批历史。

文档需同步服务 API 契约、状态图、稳定错误码、数据关系、迁移/回滚顺序、通知最终一致性说明，以及发件箱积压和失败的运维观测方式。不得把某一框架或数据库产品的调用形式写成规范性接口。

## 验收标准

- 对 `created` 订单提交审批后，订单成为 `pending`，出现且仅出现一条当前审批记录，订单版本递增。
- 对 `rejected` 订单重新提交后，旧审批记录保持不变，新记录的轮次号递增并成为唯一当前待审批记录。
- 授权审批人可批准或拒绝当前轮次；订单状态、审批记录、决定审计字段、幂等回执和通知事件在一个关系型事务中原子提交。
- 未授权主体、非法状态、错误审批轮次、陈旧版本和冲突幂等键都返回稳定错误且不产生部分写入。
- 两个并发决定最多一个成功；相同请求的并发重试只产生一个决定结果和一个通知事件。
- 决定提交后，订单所有者最终收到一条包含订单、决定和时间的站内通知；通知通道短暂失败不会丢失事件或回滚决定。
- 审批历史查询按轮次稳定分页，并保留所有拒绝、重新提交和最终决定记录。
- 迁移可从当前只有 `created` 订单的仓库状态安全升级，既有订单不被自动提交或通知，回滚边界不会删除审计数据。
- 自动化测试可独立证明状态迁移、授权、事务原子性、幂等、并发一致性、通知重试和迁移边界。
- 规格不绑定具体 Web 框架或数据库产品，且 `user_approval` 与 `independent_review` 在本次交接中均保持 `pending`。
```

需求文档：/workspace/fixture/docs/requirements/2026-07-12-order-approval.md
需求主题：order-approval
需求范围：功能
需求理解置信度：97
需求理解确认：已确认
需求文档用户批准：已批准
需求文档独立评审：已通过
技术规格门禁：已开放
技术规格：/workspace/fixture/docs/specs/2026-07-17-order-approval-design.md
技术规格用户批准：待批准
技术规格独立评审：待评审
实施计划：尚未创建
计划评审状态：未开始
实施门禁：未开放
