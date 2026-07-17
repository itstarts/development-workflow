路由结果为 `new-session`。显式规格和计划均可读，计划评审已批准，发现无歧义、错误或警告；当前会话存在大量无关上下文，适合隔离执行。仅生成提示词，未创建、打开或发送新会话。

```````text
开发目标：依据已批准的规格 docs/specs/2026-07-17-example-design.md 和计划 docs/plans/2026-07-17-example.md 完成 example feature 的实施。遵守仓库规则，修改行为必须先写失败测试，并完成独立复审。保留压力内容：中文、English、café、naïve、Δ、🚀、全角标点「交接」，长路径 docs/specs/2026-07-17-example-design.md，以及连续六个反引号 ``````。

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
每次委派前检查目标新会话实际加载的个人全局 custom agents：`CODEX_HOME/agents`，未设置 `CODEX_HOME` 时检查 `~/.codex/agents`。按 `name` 和 `description` 匹配当前子任务。存在职责匹配时，使用该全局 agent 的 `name` 启动；多个匹配时选择职责最具体者。仅在没有匹配的全局 agent 时使用内置或通用子代理。存在匹配但当前运行时无法按 name 启动时，停止该次委派并报告能力缺口；不得声称已使用该 agent。记录每次委派实际使用的 agent name，并在最终报告中汇总。

主代理执行合同
按照计划和适用的仓库规则实施，不擅自扩大范围或修改未授权的公共契约。需要委派时遵循上文的全局子代理选择规则。每项任务使用 TDD：先写并运行失败测试，确认失败原因符合预期，再写最小实现并运行与影响范围匹配的验证。验证失败时保留错误证据并定位原因。验证完成后由未参与实现的独立评审者检查当前变更；发现问题时，由同一评审者复审当前版本，重复修复、验证和复审，直到 APPROVED。独立评审未通过不得进入下一项。仅在权限允许且工作区状态安全时创建范围清晰的本地 commit。

完成条件与报告
全部计划任务完成并集成后，先运行完整的相关验证，再由未参与实现的独立评审者执行整体评审。发现问题时，由同一评审者整体复审当前结果，重复修复、验证和整体复审，直到 APPROVED。只有整体复审通过且验证证据完整后才报告完成。报告关键变更、受影响文件、验证命令与结果、任务级独立评审与整体复审结论、风险、未验证项和后续操作。
```````
需求路径：docs/requirements/2026-07-17-example.md
需求主题：example
需求范围：feature
需求理解置信度：98
需求理解确认：已批准
需求用户批准：已批准
需求独立评审：已批准
规格门：开放
规格路径：docs/specs/2026-07-17-example-design.md
规格用户批准：已批准
规格独立评审：已批准
计划路径：docs/plans/2026-07-17-example.md
计划评审状态：已批准
实施门：开放
