# 小验证：Python 入门基础

> 覆盖：
> - [01-python-variables-and-types](./01-python-variables-and-types.md)
> - [02-python-functions](./02-python-functions.md)
> - [03-python-classes-basics](./03-python-classes-basics.md)
> - [04-python-modules-and-imports](./04-python-modules-and-imports.md)
> - [05-python-control-flow](./05-python-control-flow.md)
> - [06-python-exceptions](./06-python-exceptions.md)
>
> 预计：30～60 分钟 · 在 dify 仓库练习

## 背景

本组覆盖变量、函数、类、模块、控制流与异常。dify 后端大量简单校验与工具函数就在 `api/libs/`：纯函数、`raise ValueError`、模块级常量、可调用类。本练习在**真实代码**里读懂它们，并做一处无害小改，而不是从零造 `mini_config`。

仓库根：`/Users/xu/code/github/dify`（以下路径均相对 `api/`）。

## 需求（主任务：仓库内）

### 1. 只读定位（必做）

在编辑器中打开并阅读下列入口（不必整文件啃完，跟到函数体即可）：

| 主题 | 打开 | 找什么 |
|------|------|--------|
| 模块常量 + 函数 + 异常 | `libs/password.py` | 模块级 `password_pattern`、`valid_password` 如何 `raise ValueError` |
| 控制流 + 返回值 | `libs/time_parser.py` | `parse_time_duration`：空串 / 正则不匹配 / `d|h|m|s` 分支 |
| 纯函数 + 类型标注 | `libs/url_utils.py` | `normalize_api_base_url` 的链式字符串处理 |
| 集合推导 | `libs/collection_utils.py` | `convert_to_lower_and_upper_set` 的推导式与空输入 |
| 类当校验器 | `libs/helper.py` | `StrLen` / `DatetimeString`：`__init__` + `__call__` |
| 包导入 | 随便跟一条 `from libs.password import valid_password` | 例如 `tests/unit_tests/libs/test_password.py` 或 `rg "valid_password" --type py` |

写一份 **NOTES（5～10 行）** 到本地笔记（勿提交到 dify），至少回答：

1. `valid_password` 成功时返回什么？失败抛什么类型、信息长什么样？
2. `parse_time_duration("7days")` 与 `"7d"` 结果为何不同（结合 `re.match` 模式）？
3. `StrLen` 是「类」还是「函数」在用？调用方大概怎么用它？

### 2. 动手（三选一，做完后请还原或另开练习分支）

**选项 A · 更清晰错误信息（推荐）**

1. 打开 `libs/password.py` 的 `valid_password`。
2. 把失败时的 `ValueError` 文案改得更具体（例如点出「至少 8 位」「需同时含字母与数字」），**不要**改校验规则本身。
3. 验证：跑已有单测  
   `cd /Users/xu/code/github/dify/api && uv run pytest tests/unit_tests/libs/test_password.py -q`  
   （若环境未装依赖，可改用下方「最小本地断言」：在 Python REPL 里 `from libs.password import valid_password` 测合法/非法各 2 例。）
4. 练习结束后用 git 还原该文件（**不要 commit**）。

**选项 B · 命名常量**

1. 打开 `libs/validators.py` 的 `validate_description_length`。
2. 将魔数 `400` 提成模块级常量（如 `DESCRIPTION_MAX_LENGTH = 400`），函数体引用常量。
3. 验证：  
   `uv run pytest tests/integration_tests/controllers/console/app/test_description_validation.py -q`  
   或手工调用：`None` / 400 字通过、401 字抛 `ValueError`。
4. 还原改动。

**选项 C · 人为改坏再恢复**

1. 打开 `libs/time_parser.py`，**故意**把 `unit == "d"` 分支改成错误逻辑（例如当小时处理）。
2. 跑 `uv run pytest tests/unit_tests/libs/test_time_parser.py -q`，确认失败信息指向你的改动。
3. 改回正确逻辑，再跑测试至通过。
4. 在 NOTES 记一行：哪条用例最先暴露问题。

### 3. 导入关系小实验（必做，只读即可）

在 `api/` 下执行（或等价 IDE 跳转）：

```bash
rg -n "from libs\.(password|time_parser|validators|url_utils|collection_utils) import|import libs\.(password|time_parser)" --type py -g '!migrations/**' | head -40
```

在 NOTES 中列 2 个**真实调用方**（文件路径 + 函数/测试名即可）。

## 提示（路径 / rg，不给完整答案）

```bash
cd /Users/xu/code/github/dify/api
rg -n "def valid_password|password_pattern" libs/password.py
rg -n "def parse_time_duration|def get_time_threshold" libs/time_parser.py
rg -n "class StrLen|class DatetimeString|def email\(" libs/helper.py
rg -n "def normalize_api_base_url" libs/
rg -n "validate_description_length" --type py
ls tests/unit_tests/libs/test_password.py tests/unit_tests/libs/test_time_parser.py
```

- 比较 `None` 用 `is`；异常链式可用 `raise ... from exc`（`libs/helper.py` 的 UUID 校验附近可见）。
- 若 pytest / `uv` 不可用：用 `PYTHONPATH=. python -c "from libs.password import valid_password; ..."` 做最小断言即可。

## 验收标准

- [ ] NOTES 覆盖：`valid_password` 返回/异常、`parse_time_duration` 模式差异、`StrLen` 用法直觉
- [ ] 完成选项 A/B/C 之一，并有可复现的验证记录（pytest 输出或 REPL 断言）
- [ ] 列出至少 2 个真实 import 调用方路径
- [ ] 对 dify 的改动已还原或明确只在本地练习分支、未 push/commit 到学习任务要求之外

## 延伸（选做）

本地实现 `mini_config/`（不必进 monorepo）：`parse_bool`、`load_env_map`、包导入 + `cli` 入口。这是从零造轮子，**不能替代**上面的仓库主任务。
