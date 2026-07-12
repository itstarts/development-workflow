# AGENTS.md — skills

## 适用范围

适用于 `skills/` 下所有 skill。

## Skill 内容

- 每个可发布 skill 目录必须包含 `SKILL.md`；frontmatter 只包含 `name` 和 `description`。
- 名称使用 64 字符以内的小写 kebab-case，目录名与 frontmatter `name` 完全一致。
- `description` 只描述触发条件，不概述执行步骤；以 `Use when...` 开头并覆盖真实触发语。
- `SKILL.md` 保持精炼；详细策略放入一层深度的 `references/`，确定性逻辑放入 `scripts/`，输出模板放入 `assets/`。
- UI metadata 位于 `agents/openai.yaml`，必须从最终 `SKILL.md` 确定性生成并保持一致。
- skill 目录内不放 README、CHANGELOG、安装说明、评审报告或开发过程记录；这些内容放仓库根目录或 `work/`。

## TDD 与前向测试

- 新 skill：先在 `work/evaluations/<skill>/baseline/` 保存无目标 skill 代理的本地原始输出，并把脱敏后的固定场景、判据和选中证据写入版本化 `evaluations/<skill>/`，再创建 `SKILL.md`。
- 修改 skill：先新增失败测试或失败场景并观察 RED。
- GREEN 场景必须由与 baseline 不同的全新代理运行，且不能看到 expected、失败解释或实现结论。
- 保存原始输出、结构化判据和验证命令；不能只记录总结。
- 失败或不确定时不得放宽判据、吞掉错误或输出部分结果。

## 跨 skill 边界

- skill 之间不使用相对源码 import、不读取兄弟 skill 安装目录，也不依赖 plugin 是否整体安装。
- 共享信息通过稳定文档格式和显式路径传递。
- 每个 skill 必须能够通过 GitHub 多路径安装方式单独安装和验证。
- 修改交接契约时必须同时增加两个 skill 的集成回归测试，并按 semver 判断是否属于 breaking change。

## 发布前检查

- 官方 `quick_validate.py` 通过。
- skill 自带测试和仓库集成测试通过。
- 无 TODO、TBD、PLACEHOLDER、示例残留或本机绝对路径。
- 从 Git tag 安装到临时 `CODEX_HOME` 后，安装内容与已验证 staging 一致。
- plugin manifest 版本、README 安装命令和 CHANGELOG 同步。
