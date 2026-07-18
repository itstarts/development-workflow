```text
开发目标：实现 example 功能

开发目标与来源文档
规格：/workspace/fixture/docs/specs/2026-07-17-example-design.md（来源：explicit）
计划：/workspace/fixture/docs/plans/2026-07-17-example.md（来源：explicit；评审：approved）

仓库与分支状态
仓库状态已识别为 Git 仓库。
目标分支未指定：修改前根据计划与仓库规则派生开发分支名；不得直接使用 main 或 master，仓库状态不允许建分支时停止。

规则与文档优先级
- /workspace/fixture/AGENTS.md（来源：filesystem；优先级：0）
先完整读取规格、计划和所有适用的 AGENTS.md，再做任何修改。会话显式规则优先于文件系统规则，更深层目录规则优先；显式文档路径优先于自动选择值。实施前核对文档路径、适用规则与计划评审状态。
计划评审已明确批准。

权限边界
允许：create-development-branch-or-worktree、create-local-commit、query-official-documentation、install-plan-listed-dependencies、download-plan-required-playwright-browsers、start-local-development-service、run-tests-build-lint-local-validation
禁止：push、merge、rebase、tag、release、production-deployment、cloudflare-or-dns-change、unauthorized-secrets-tokens-credentials-or-production-data
平台安全与审批规则始终优先；外部状态、敏感信息或破坏性操作必须遵循当前会话审批机制，用户权限覆盖不能绕过平台约束。

全局子代理选择
目标会话首次需要委派时，读取实际加载且可按名称启动的个人全局 custom agents，建立仅存于当前对话上下文的会话内清单；记录每项的 `name`、`description` 和本次读取是否可靠，不写入项目、缓存、用户目录或 task/thread 标识符。按该清单匹配当前子任务，职责匹配时使用最具体的 agent name；只有没有匹配项时才使用内置或通用子代理。后续委派不重复扫描。

仅在确认配置变化、首次读取失败、匹配 Agent 按名称启动失败、会话内清单与可观察能力冲突，或用户显式要求刷新时刷新一次并重新判断。刷新后仍无法启动匹配 Agent 时，停止该次委派并报告能力缺口，不得静默降级或声称已使用。记录每次委派实际使用的 agent name，并在最终报告中汇总。

主代理执行合同
按照计划和适用的仓库规则实施，不擅自扩大范围或修改未授权的公共契约。需要委派时遵循上文的全局子代理选择规则。每项任务使用 TDD：先写并运行失败测试，确认失败原因符合预期，再写最小实现；每项任务完成与影响范围匹配的验证，失败时保留错误证据并定位原因。任务拆分本身不产生独立评审门，不得仅因任务数量增加评审次数。只有计划明确标记单项任务跨越重大公共契约、数据、迁移、权限、安全、资金、并发、事务或一致性边界，或后续任务依赖尚未验证的关键基础时，才在该边界后执行中间里程碑评审。仅在权限允许且工作区状态安全时创建范围清晰的本地 commit。

完成条件与报告
全部计划任务完成并集成后，先运行完整的相关验证，再由一名未参与实现的独立评审者对最新完整 diff 执行整体评审。发现范围内问题时，由同一评审者整体复审当前结果，重复修复、验证和整体复审，直到 APPROVED；通过后停止，不增加重复评审。只有整体复审通过且验证证据完整后才报告完成。报告关键变更、受影响文件、验证命令与结果、中间里程碑评审（若有）和整体复审结论、风险、未验证项和后续操作。
```
