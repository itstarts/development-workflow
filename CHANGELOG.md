# Changelog

本项目遵循语义化版本。六个 skill 共享 plugin 版本；每个版本分别记录 skill 与集成契约变化。

## 0.1.0 - Unreleased

### routing-development-workflows

- 新增只负责分类和交接的总路由：没有显式入口时按可观察批准、范围、风险与验证事实选择 `fast | standard | full | blocked`；显式入口在总路由适用范围外直接进入对应能力，不产生第五个 wire value。
- `fast` 只进入已明确批准且无高风险边界的 `implementing-bounded-changes`；普通不确定需求进入 `standard`，公共契约、架构、数据、权限、迁移、并发、一致性或外部状态等边界进入 `full`。
- 通过五个无目标 baseline 与 GREEN 场景、合同测试和官方 validator 建立创建证据；路由 skill 不创建文档、不实施、不读取兄弟源码。

### managing-agents-rules

- 新增独立 AGENTS 规则治理入口：实质性开发前检查项目根规则，任务完成时只筛选有当前任务证据的长期候选。
- 候选统一 diff 改为只显示一次的动态反引号 fence，批准问题固定在 fence 之后；不再使用 Codex 客户端可能原样显示的 `<details>` / `<summary>` 折叠标签。
- 项目级与全局目标分别展示最小 diff 并逐次批准；目标内容变化即使批准失效，写入后必须读取并验证精确结果。
- 会话内隔离项目、拒绝和逻辑任务完成扫描状态，不把治理状态或 task/thread 标识符持久化到项目、用户目录或缓存。
- 全局基础规则与非空 override 分开处理；默认更新长期基础文件，override 只告警并仅在用户显式选择后成为独立目标。
- 通过 10 个无目标 skill baseline 与 GREEN 场景、18 项合同测试、官方 validator 和独立评审建立创建闭环。

### implementing-bounded-changes

- 新增用户明确批准后的受控实施入口，不要求为已确认的小改动创建 PRD、spec、plan 或开发提示词。
- 实施前冻结目标、改动点、方案、非目标、验证范围和文档影响；任何实质范围或设计扩大都重新进入用户批准门。
- 行为变化执行比例化 RED→GREEN，默认使用最小充分定向验证，允许边界清晰的 Sub Agent；最终完整 diff 必须由一位独立评审者评审，同一评审者复审到 `APPROVED` 后立即停止，不自我批准、伪造 Agent 证据或过度评审。
- 把受影响的现有文档更新纳入完成条件，同时保留无关既有失败和未验证项的真实报告。
- 纯文档、格式或确定性机械改动在不改变行为、配置语义、公共契约、产品含义或操作流程，且确定性检查充分、仓库规则不强制评审时，可如实使用独立评审豁免；最终 diff 检查与验证仍是必需项。
- 行为或语义变更仍使用一位独立 reviewer；连续两轮修复与复审仍未批准时停止自动循环并保持实施门阻塞，用户偏好不能替代正确性证据。
- 在当前任务会话内按相关代码、测试、fixture、配置、依赖、命令和环境复用已通过验证，只让相关变化使对应结果失效；评审或 Agent 交接本身不再触发重跑，仓库要求的最终门只在最后一次相关变化后运行一次，并在覆盖同一 focused seam 时直接提供 GREEN。
- 项目特定的“变更范围→验证命令”只从实际 diff 与验证证据形成可选规则候选；受控实施不直接修改 `AGENTS.md`，用户可逐 diff 选择加入或拒绝。
- 通过无目标 skill baseline、5 个固定场景、官方 validator、plugin staging 和独立评审建立创建闭环。

### creating-product-requirements

- 收紧触发描述并增加最前置交付物门禁：只为明确的 PRD 或技术设计前的产品需求正式化进入工作流；旁白、脚本、文案、提纲和文章等纯内容任务不再因结构、时长或范围变化触发八字段、spec 或 plan。
- 普通非阻塞澄清从完整八字段后缀改为固定三行 compact 状态，属于 `breaking contract change`；摘要确认、批准、阻塞、阶段完成和下游交接继续使用完整八字段。
- 支持一轮最多三个互不依赖的产品问题；依赖问题仍只询问决定性分支，并按阶段渐进加载 discovery、document 与 review/handoff references。
- 新增 skill 内自包含的严格 `render_handoff.py`，确定性校验 canonical、gate 与 compact/full 显示，不改变英文八字段或旧英文输入。
- 新增产品、阶段和功能三种范围类型；一份 PRD 只承载一个稳定主题。
- 只有需求理解置信度至少 95 且用户明确确认当前摘要后才创建 PRD；Agent 自评不能替代用户确认。
- PRD 聚焦产品范围、用户场景和验收标准，不包含 API、数据模型、迁移或实现任务。
- 固定 PRD 独立评审、用户批准、实质修改失效和 requirements 八字段交接门禁。
- 接收总路由的独立 handoff，并把 `standard | full` 与风险事实保存到 PRD 正文 `工作流分流`；canonical requirements 八字段保持不变，route 缺失或不可靠时按 `full` 处理。
- 已批准 PRD 写入并验证八字段后，主 Agent 在同一会话自动进入可用的 spec workflow；下游不可用时保留真实八字段并报告能力缺口。
- 新建 PRD 的标题、章节、frontmatter 键及生命周期值使用中文；英文 requirements canonical 八字段保持不变，历史英文 PRD 在维护和重评时保持原 schema，不隐式迁移。
- 通过无目标 skill baseline、当前 19 个 GREEN 场景、官方 validator 和独立评审完成创建与维护闭环。

### generating-development-prompts

- plan discovery 接受完整 `chinese-current` frontmatter，并把“已通过 / 待评审”、评审角色和 ISO 日期归一化为既有英文 review JSON；`english-legacy` frontmatter 保持 review-only，legacy header 继续只接受英文。
- 新中文 plan 支持 `评审模式: 技术包 | 逐级`，并把 plan review 与 `implementation_gate` 分开：技术包评审可已通过，但 spec 用户批准待完成时实施仍阻塞。
- 中文 plan 的 mixed schema、语义重复、残缺固定字段、畸形 scalar、不受支持值或生命周期不一致统一返回 `unknown`，不改变既有 JSON shape 或 canonical handoff。
- policy 按 discovery → permission → routing 渐进加载；没有上游十四字段的手动提示词请求不加载或伪造路由状态。
- 目标会话 Agent 清单改为首次委派读取一次并在会话内复用，仅在配置变化、读取或按名称启动失败、可观察能力冲突或用户要求时刷新一次。
- 自动三态路由使用 skill 内同一严格 handoff renderer 的 full 视图，手动 renderer-only 输出与 dynamic fence 合同保持不变。
- 导入经过任务级、集成和最终全量评审的初始实现。
- 统一 Python 3.9 与 Python 3.14 对深层 JSON 输入的 `invalid_json` 错误分类。
- 移除无法基于任务复杂度可靠判断的 effort 建议及其输入、渲染和校验契约。
- 仓库与分支状态段只保留实施门，不再展开工作目录、分支、HEAD 或 worktree 状态。
- 委派任务时优先使用职责匹配的个人全局 custom agent，并显式处理无法按名称启动的能力缺口。
- 默认自动发现目录改为 `docs/specs` 与 `docs/plans`；生成提示词不绑定外部开发方法或固定评审 skill，并以自包含合同要求任务级 TDD 和定向验证、按真实风险设置可选里程碑评审，以及集成后对最新完整 diff 的单次整体评审循环，不因任务数量增加评审门。
- 已批准十四字段触发 `current-session`、`new-session`、`blocked` 三态会话路由；手动提示词请求继续兼容未批准或状态未知的 plan，并保留实施阻断门。
- `renderer stdout` 从裸提示词正文改为单一 Markdown 代码框，属于 `breaking contract change`。把 stdout 当作裸正文的调用方必须改为提取唯一 Markdown 代码框内容；不提供并行 raw 模式。
- 自动路由在选择三态或调用 `render_prompt.py` 前先调用本地 handoff renderer 一次，并冻结其成功 stdout 作为中文十四字段视图；三条路由路径复用该视图，状态块不进入 prompt renderer stdout，并始终位于可复制代码框之外。
- 生成的实施合同在连续两轮修复与复审仍未通过时停止自动循环并保持实施门关闭，不通过增加 reviewer 或用户偏好替代正确性证据。

### creating-development-specs-and-plans

- technical spec 和 implementation plan 现在把验收证据分为最小关键 E2E 与目标用户人工验收：跨层技术闭环使用可重复自动化，易用性、内容质量和视觉体验保留目标用户判断，并明确两类证据不得互相替代。
- 新建 technical spec 与 implementation plan 使用完整中文 frontmatter；历史英文文档继续按原 schema 写回，不进行仅本地化迁移。
- PRD inspector 在 raw frontmatter 阶段接受精确中文键和值并归一化为现有英文 JSON；历史英文输入保持兼容，mixed、语义重复、畸形、未知 Unicode key 和不受支持中文值失败关闭。
- 普通非阻塞技术澄清从完整十四字段后缀改为固定三行 compact 状态，属于 `breaking contract change`；spec 批准、阻塞、阶段完成和路由继续使用完整十四字段。
- 支持一轮最多三个互不依赖的技术问题，依赖问题逐问，并按阶段渐进加载 discovery、document 与 review/handoff references。
- 新增与上下游字节一致但运行时独立的严格 `render_handoff.py`，保留十四字段、双门、旧英文输入和 plan 状态语义。
- 将已批准 PRD 设为创建或实质修改技术 spec 的强制上游门；缺失、不可靠、未批准或 topic/scope 不匹配时阻断。
- 新增只读 PRD inspector，校验仓库根、路径边界、稳定主题、范围、95% 置信度、摘要确认、独立评审和用户批准。
- 技术 spec 在相关时明确 API/技术接口、数据模型与实体关系、迁移、状态流转、事务、并发与一致性。
- 技术 spec 新增强制命令结果/失败矩阵；每个 distinct outcome 使用唯一 Outcome ID 单独成行，数据库相关保证必须说明实际引擎的事务、锁、读转写、竞争超时、回滚与错误分类，并用 Guarantee ID 双向追踪到 Outcome ID、精确测试、命令和断言。
- 固定 requirements/spec/plan 十四字段绝对路径交接，同时保留 spec 和 plan 的双审批顺序门。
- `standard` route 在 spec 用户批准前先创建 spec+plan 技术包，由同一 reviewer 给出一次覆盖两份当前文档的 verdict；package 通过但 spec 待用户批准时 plan review 可为 approved、实施门仍 blocked。`full` 或 route 不可靠时保留逐级 spec→用户批准→plan review。
- 通过隔离的新鲜代理保留创建前 RED 审计、当前迁移 baseline 与 GREEN 前向证据。
- 评估证据收敛为场景、有效性和判据结果，移除文件哈希、候选 manifest 与逐次 attempt 审计。
- spec 的安全、权限和敏感数据设计改为仅在目标需求真实涉及对应边界时展开。
- 保持运行时自包含，不实现目标代码、不调用兄弟 skill，也不创建用户可见 task/thread 或改变外部状态。
- 接收上游显式 requirements 八字段并逐值映射为十四字段前缀；进入下游后的 PRD 复验失败仍返回完整十四字段并关闭双门。
- spec 与 plan 模板的标题、章节和说明默认使用中文；plan 评审通过并重新验证十四字段后，主 Agent 自动进入会话路由。
- implementation plan 以任务作为可独立验证的执行切片，不再为每项任务强制独立评审；默认只在集成后评审最新完整 diff，并仅为真实高风险边界或后续依赖的关键基础增加中间里程碑评审。
- 默认实施评审连续两轮修复仍未批准时停止自动循环并保持阻塞；metadata-only 的 spec 用户批准同步不会使已通过的技术包评审失效。

### Repository

- evaluation freshness 允许复用已满足祖先关系的干净前序，并要求从第一个工作区变化阶段开始形成连续后序；GREEN 刷新和评审写回不再需要为了通过校验制造中间提交，缺口、部分刷新与过期前序仍失败。
- 验证流程把受影响 skill 合并为一次定向门，只保留一位最终评审者，并在批准写回后直接运行一次完整门；日常和发布验证统一使用项目当前 `.venv`，不再要求重复执行 Python 3.9/3.14 双版本矩阵。
- `check.py --skill` 不再重复运行无关根测试，只运行目标 skill tests、stage-aware repository validator 与官方 validator；共享工具的直接根测试按实际 diff 单独运行，最终 `--full` 仍运行完整根测试一次。
- creation-only freshness 支持尚未提交的新 skill 在 production、registry、baseline 与 GREEN 全部属于同一完整工作区 bundle 时记录 `worktree-creation-current`，既有已提交 skill 的后续 production 变化仍必须升级 current-RED profile。
- 新增 `.agents/plugins/marketplace.json` repo marketplace，以 Git URL source 暴露仓库根级 `development-workflow` plugin，并在 README、安装指南和仓库 validator 中同步安装入口与 catalog 契约。
- 新增 Git-aware evaluation freshness：`fresh_cases`、clean commit 祖先链、工作区干净前序与连续 dirty 后序，以及 non-Git 严格失败，避免 production 晚于 RED/GREEN/review 仍误报完成。
- 明确 `/workspace/fixture` 是版本化评估唯一允许的固定合成根，不是真实本机路径或隐私数据；验证器拒绝 macOS 用户与临时路径、Linux `/home/...` 与临时路径、Windows 用户路径及其它 `/workspace/...` 根。
- 新增 `scripts/check.py` 统一定向/完整验证，以及只读 `scripts/verify_install.py` 安装 payload 差异检查；两者只编排现有权威验证，不安装依赖、不启动服务、不写真实 `CODEX_HOME`。
- 建立 plugin-compatible 目录、项目级 agent 角色、分层 `AGENTS.md` 和仓库验证入口。
- 增加 MIT License、贡献指南、安全策略、安装指南、工作流契约与 Agent 开发指南，形成公开仓库文档入口。
- 补齐本机凭证、编辑器状态、Python 缓存、原始评估、构建测试产物和临时日志的 `.gitignore` 边界。
- 将公开安装命令更新为 `itstarts/development-workflow`，并记录完整 Git 历史隐私审计要求。
- 固定 validator 开发依赖，仓库支持 Python 3.9 及以上并统一使用项目当前 `.venv` 验证。
- 仓库验证器忽略 Python 缓存和系统元数据，保持 skill 测试后的重复验证稳定。
- plugin 同时暴露总路由、PRD → technical spec/plan → development prompt 完整交接链、approved bounded change → implementation 受控实施入口和 `managing-agents-rules` 规则治理入口；本地 staging 验证六个 skill 可单独或组合复制且拒绝覆盖已有目标。
- 公开文档记录 PRD→spec 与 plan→三态路由的两段自动衔接、单一最终 handoff 和单 skill 能力缺口；plugin 保持未发布 `0.1.0`，本次不发布。
- 用户可见 handoff/status-block 回复后缀从英文字段和值改为语境化中文，属于 `breaking contract change`；英文 canonical 机器字段、门禁计算、skill 间传递、旧英文输入和 renderer stdout 字节合同保持兼容。映射失败时停止本次自动交接且不输出残缺、混合或英文 fallback 状态块。
