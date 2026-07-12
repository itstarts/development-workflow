$goal_line

开发目标与来源文档
规格：$spec_path（来源：$spec_source）
计划：$plan_path（来源：$plan_source；评审：$plan_review）

仓库与分支状态
工作目录：$workdir
仓库根目录：$repository_root
目标分支：$target_branch
当前分支：$current_branch
HEAD：$head
worktree：$worktree_kind
工作区状态：$worktree_status
$repository_gate
$branch_gate

规则与文档优先级
$rules
先完整读取规格、计划和所有适用的 AGENTS.md，再做任何修改。会话显式规则优先于文件系统规则，更深层目录规则优先；显式文档路径优先于自动选择值。实施前核对路径、分支、HEAD、工作区状态与计划评审状态。
$plan_gate

模型与 reasoning effort
$model_evidence
主代理：$main_effort
实现子代理：$implementation_effort
任务评审与集成评审：$review_effort
最终全量评审：$final_effort
$model_gate

权限边界
允许：$allowed
禁止：$forbidden
平台安全与审批规则始终优先；外部状态、敏感信息或破坏性操作必须遵循当前会话审批机制，用户权限覆盖不能绕过平台约束。

主代理执行合同
根据计划按顺序拆分边界清晰、可独立验证的开发子任务。每项任务由独立实现子代理执行，实现者不得担任该任务的评审者。生产行为遵循测试驱动开发：先写并运行失败测试，确认按预期失败，再写最小实现并验证。异常、测试失败或非预期行为使用系统化调试，先定位根因。每项任务依次完成实现、验证、独立评审、修复所有发现、重新验证和复审；评审未收敛或验证证据不完整时不得进入下一项。每项任务完成后创建范围清晰的本地 commit。集成后执行任务间一致性评审，最终全量评审前完成所需 effort 确认或切换。

完成条件与报告
最终全量评审必须由独立评审者执行。仅当模型配置段给出暂停或继承门时，才按其中条件和顺序启动指定评审角色；否则按已确认的子代理配置执行最终评审。修复全部发现后重新运行相关验证，并通过同一渠道复审到 APPROVED。只有最终全量评审通过且验证证据完整后，才报告完成。报告关键变更、受影响文件、验证命令与结果、评审结论、风险、未验证项和后续操作。
