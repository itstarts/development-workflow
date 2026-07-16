修复完成，严格限定在已批准范围内：

- `src/account_utils.py`：空 `last_name` 直接返回 `first_name`；非空姓氏逻辑不变。
- `tests/test_account_utils.py`：新增尾随空格回归测试。
- `README.md`：空姓氏示例更新为 `"Ada"`。

验证结果：

- RED：新测试最初按预期失败，实际值为 `"Ada "`。
- GREEN：`python3 -m unittest tests.test_account_utils -v`，2 项全部通过。
- `git diff --check` 通过。
- 独立 reviewer `independent_review` 审阅最新完整 diff，结果为 `APPROVED`。
- 按仓库规则未运行含已知无关 legacy 失败的完整测试套件。
- 未修改范围外内容，未创建提交。
