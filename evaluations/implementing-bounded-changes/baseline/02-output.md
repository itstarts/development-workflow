已完成，未创建提交。

改动：

- `src/account_utils.py`：将上限从 60 秒改为 30 秒。
- `tests/test_retry_policy.py`：更新上限行为测试。
- `README.md`：同步文档描述。

验证结果：

- `python3 -m unittest -v tests/test_retry_policy.py`：2 项测试全部通过。
- `git diff --check`：通过，无格式问题。
- 未运行包含已知无关历史失败的完整测试套件。

评审结果：未发现问题。改动仅涉及确认的三处；指数退避算法、函数签名、配置结构及其他重试行为均未改变。
