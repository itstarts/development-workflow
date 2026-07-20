已完成，仅修改 `/workspace/fixture/README.md`，将 `"Ada "` 修正为 `"Ada"`。生产代码、测试及其他说明均未修改，也未创建提交。

验证结果：

- `python3 -m unittest tests/test_account_utils.py`：2 项通过
- 精确文本检查：新示例存在，旧示例无匹配
- `git diff --check`：通过
- 最终差异：仅 README 一行变更

未运行含已知无关遗留失败的全量套件。该改动仅同步非规范性陈旧示例，局部可逆且已有确定性验证，因此按技能规则豁免独立评审。
