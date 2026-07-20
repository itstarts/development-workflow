# Release notes 规范

本规范适用于本仓库的 GitHub Release 正文。`CHANGELOG.md` 保存完整版本变化，Release notes 只提炼使用者需要知道的结果、安装方式、迁移影响、验证证据和已确认限制。

## 固定规则

- 正文第一节必须是 `## 本版内容`，不在正文前重复 Release 标题或版本号。
- `本版内容` 使用 3～7 条面向用户的中文结果说明；技术标识符保持英文，只在有助于理解时提及内部实现。
- Release 标题、Git tag、plugin manifest 版本、Marketplace `source.ref`、安装命令和版本链接必须指向同一版本。
- 只记录当前候选实际完成的验证、兼容性影响和已确认限制；不得把计划、授权或未运行的检查写成完成证据。
- 不直接复制 commit 列表，不堆叠实现过程，不保留空章节、占位说明或容易过期的测试数量。
- 有 breaking change 时必须说明受影响调用方和迁移方法；没有适用内容时省略对应可选章节。

## 章节顺序

1. `## 本版内容`：必需，概括用户可感知的主要结果。
2. `## 安装与升级`：发布可安装 plugin 或安装方式变化时使用，给出固定 tag 的命令。
3. `## 兼容性与迁移`：存在 breaking change、旧开发版迁移或特殊升级动作时使用。
4. `## 验证`：列出本次真实完成的发布门和 tag 安装证据，不展开全部测试日志。
5. `## 已知限制`：仅列当前已确认且会影响使用者的限制。

可选章节必须按上述顺序出现；没有内容就整节删除。

## 版本链接

- 首个 release 没有前一版本，末行使用 `https://github.com/itstarts/development-workflow/tree/vCURRENT`。
- 后续 release 末行使用 `https://github.com/itstarts/development-workflow/compare/vPREVIOUS...vCURRENT`。
- 链接中的版本必须与 Release 标题、tag、manifest、Marketplace 和安装命令一致。

## 模板

```markdown
## 本版内容

- <用一句话说明用户获得的结果>

## 安装与升级

<只保留本版实际适用的固定 tag 安装或升级命令>

## 兼容性与迁移

- <说明受影响对象与迁移动作；不适用时删除整节>

## 验证

- <记录实际通过的发布门与 tag 安装验证；不适用时删除整节>

## 已知限制

- <只写已确认限制；没有时删除整节>

[查看完整变更](https://github.com/itstarts/development-workflow/compare/vPREVIOUS...vCURRENT)
```

首个 release 将模板末行替换为 `/tree/vCURRENT` 链接。发布前删除所有模板说明和不适用章节，再用实际版本与证据替换示例值。
