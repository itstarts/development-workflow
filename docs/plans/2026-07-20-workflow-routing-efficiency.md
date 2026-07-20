# 工作流路由与三阶段提效实施记录

**目标：** 在不降低正确性、权限和真实完成门的前提下，减少不必要的文档、评审往返与重复全量测试。

**用户批准范围：** 新增一个只分类和交接的总路由 skill；按 fast、standard、full 三种开发路径优化现有流程；保留 blocked 作为无法安全交接的结果；不发布、不安装到真实 Codex home、不 commit 或 push。

## 阶段一：入口与 bounded change

- [x] 新增 `routing-development-workflows`，冻结 `fast | standard | full | blocked` 和六字段 handoff。
- [x] `fast` 只交给 `implementing-bounded-changes`，路由决定不等于实施批准。
- [x] 纯文档、格式或确定性机械改动满足严格非语义条件时可免独立评审；最终 diff 与确定性验证仍保留。
- [x] 行为或语义变更仍使用一位 reviewer；连续两轮修复与复审未通过后停止自动循环并保持阻塞。
- [x] 当前任务内复用相关输入未变的通过结果；覆盖同一 focused seam 的必跑父门直接提供 GREEN，评审或 Agent 交接本身不触发重跑。
- [x] 项目测试映射只保留有实际 diff 与验证支持的候选证据，不自动修改 `AGENTS.md`，由规则治理入口展示精确 diff 供用户选择。

## 阶段二：standard 技术包

- [x] PRD 正文保存独立 route handoff，canonical requirements 八字段不变；缺失或不可靠 route 按 full 处理。
- [x] standard 在 spec 用户批准前生成 spec+plan 草案，由一位 package reviewer 给出覆盖两份当前文档的 verdict。
- [x] package 已通过但 spec 尚未获用户批准时，plan review 保持 approved，implementation gate 保持 blocked。
- [x] full 保留 spec review→用户批准→plan review 的逐级门。

## 阶段三：验证与证据

- [x] `check.py --skill` 只运行目标 skill tests、stage-aware repository validator 与官方 skill validator；根测试在共享工具直接回归和最终 `--full` 中运行。
- [x] creation-only freshness 支持未提交新 skill 的完整 production/baseline/GREEN 工作区 bundle，不放宽已提交 skill 的 current-RED 要求。
- [x] 全部受影响 skill 的新鲜 GREEN、统一定向门与临时安装验证。
- [x] 最新完整 diff 的独立最终评审与批准写回。
- [x] 评审写回后的统一完整门。

## 已观察证据

- 新 router 的无目标 baseline 在四个路由场景中暴露了路线数量漂移、destination 不稳定和 handoff 不完整；加载 router 后这四个场景得到唯一稳定路线，显式入口场景保持在 router 适用范围外且不输出 route handoff。
- bounded mechanical 场景在旧合同下启动额外 reviewer；严格豁免合同下保留定向检查并不再启动 reviewer。
- 旧 spec/plan 合同明确阻止 spec 用户批准前创建 plan；新合同测试固定 standard package 与 full sequential 两条生命周期。
- 原定向入口会重复运行完整根测试；RED 测试证明无关根失败会阻断单 skill 检查，修改后该场景通过，而 `--full` 仍保留完整根测试。
- 当前工作树实测完整根测试调用耗时约 `22.07s`；优化后的 router 定向门只运行三项直接检查，整体耗时约 `0.29s`。该数字只证明本仓库当前检查编排的重复成本，不外推为所有项目的固定加速比。
- 最终评审批准后的首次完整门仅因 creation-only 测试夹具未排除新增 CPR case20 而失败；补齐夹具自身 case 集后，该单测与完整门均重新通过。
- bounded validation case06 的修复前运行在父门前额外执行一次同覆盖 focused GREEN；新 Skill 只保留 RED 和一次父门，父门同时提供 GREEN 与最终验证，并在评审时复用该结果。

## 完成状态

- 根 `AGENTS.md` 的精确候选 diff 已获用户明确批准并原样写回；reverse-check、对应契约测试和空白检查均通过。
- `workflow-final-reviewer` 已复审并批准包含验证复用边界及 case06 current-RED/GREEN 的最新完整 diff；`implementing-bounded-changes` 已写回 `review-approved`，评审后的统一完整门已通过根测试、六个 Skill 测试、严格 freshness、官方 Skill validators 与 plugin validator。
