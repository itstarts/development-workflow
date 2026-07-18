# Unknown-write reconciliation fixture

写入前 frontmatter 为：

```yaml
---
文档类型: 产品需求
主题: localized-metadata
范围类型: 功能
理解置信度: 98
需求理解确认: 已确认
用户批准: 待批准
独立评审: 已通过
独立评审角色: product-analyst
独立评审日期: 2026-07-19
---
```

预期写入后的完整 frontmatter 只把 `用户批准` 改为 `已批准`，并新增 `批准日期: 2026-07-19`。当前目标文件同时出现英文 `approved_at`，因此既不等于写入前内容，也不等于预期完整内容。
