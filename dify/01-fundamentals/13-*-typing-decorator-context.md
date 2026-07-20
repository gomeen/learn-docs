# 小验证：类型系统 · 装饰器 · 上下文管理器

> 覆盖：
> - [07-python-typing-basics](./08-python-typing-basics.md)
> - [08-typeddict](./09-typeddict.md)
> - [09-protocol-generic](./10-protocol-generic.md)
> - [10-decorator](./11-decorator.md)
> - [11-context-manager](./12-context-manager.md)
>
> 预计：30～60 分钟 · 在 dify 仓库练习

## 背景

类型标注、TypedDict/Protocol、`@wraps` 装饰器与 `with`/contextmanager 是读 Flask 控制器与执行上下文的日常工具。dify 里这些不是教材示例，而是生产代码：`repositories/`、`context/`、`controllers/*/wraps.py`、`libs/flask_utils.py`。

仓库根：`/Users/xu/code/github/dify`（路径相对 `api/`）。

## 需求（主任务：仓库内）

### 1. 只读对照表（必做）

按表打开文件，用 8～12 行 NOTES 记录「符号 → 一句话作用」：

| 知识点 | 打开 | 找什么 |
|--------|------|--------|
| TypedDict | `repositories/types.py` | `DailyRunsStats` 等：字段名与值类型 |
| TypedDict + NotRequired / total=False | `libs/oauth.py` | `OAuthState`、`GitHubRawUserInfo` |
| Protocol | `context/execution_context.py` | `AppContext`、`IExecutionContext`（含 `@runtime_checkable`） |
| Protocol（仓库接口） | `repositories/api_workflow_run_repository.py` | `APIWorkflowRunRepository(Protocol)` 方法签名即可 |
| 装饰器 + wraps | `controllers/console/wraps.py` | `once_true`、`account_initialization_required` 里的 `@wraps` |
| 装饰器簇 | 同文件 | `only_edition_cloud` / `only_edition_self_hosted`：如何根据配置短路 |
| @contextmanager | `libs/flask_utils.py` | `preserve_flask_contexts`：`yield` 前后做了什么 |
| 类上下文管理器 | `context/execution_context.py` | `ExecutionContext.__enter__` / `__exit__` 与内部 `@contextmanager enter` |

### 2. 动手（二选一）

**选项 A · 对照改写（推荐，改完务必还原）**

1. 打开 `controllers/console/wraps.py` 中**某一个**简单装饰器（优先 `only_edition_self_hosted` 或 `only_edition_cloud`）。
2. 做**等价改写**之一（只改这一处）：
   - 把内层 `decorated` 改成显式 `functools.wraps(view)(decorated)` 形式；或
   - 给装饰器增加一行更清晰的 docstring / 注释，说明「不满足 edition 时 `abort(404)`」。
3. 用笔记说明：`@wraps(view)` 保留了被装饰函数的哪些元数据（`__name__` / `__doc__` 等）。
4. **不要**改变分支条件与 `abort` 行为。验证：至少能 `python -c` 导入模块，或跑与 console wraps 相关的已有测试（若环境具备）。
5. 还原改动。

**选项 B · 找错 / 修错（安全演练）**

1. 在本地练习分支上，**故意**从某个 `@wraps(view)` 装饰器里删掉 `@wraps(...)` 一行。
2. 观察：内层函数的 `__name__` 是否变成 `decorated` / `wrapper`（在 REPL 里对装饰前后打印即可）。
3. 恢复 `@wraps`，再确认 `__name__` 回到原函数名。
4. NOTES 写清：为什么路由/调试栈依赖 wraps。

### 3. 类型阅读小题（必做，只读）

打开 `context/execution_context.py` 的 `IExecutionContext` 与 `ExecutionContext`：

- 说明：Protocol 只约定「长什么样」，`ExecutionContext` 是不是「显式声明实现了 Protocol」？
- 指出一处 `@contextmanager` 与一处 `__enter__`/`__exit__` 如何协作（`enter()` 与 `__enter__` 的关系写 2～3 句）。

## 提示（路径 / rg，不给完整答案）

```bash
cd /Users/xu/code/github/dify/api
rg -n "class .*\(TypedDict|TypedDict\)" repositories/ libs/oauth.py services/oauth_device_flow.py | head -30
rg -n "class .*\(Protocol\)|@runtime_checkable" context/ repositories/ | head -30
rg -n "@wraps|functools\.wraps" controllers/console/wraps.py libs/login.py
rg -n "@contextmanager|def __enter__|def __exit__" context/ libs/flask_utils.py services/file_service.py | head -40
```

- 更多 wraps：`controllers/service_api/wraps.py`、`libs/login.py`、`libs/rate_limit.py`
- 临时文件上下文：`services/file_service.py` 中带 `yield tmp_path` 的 `@contextmanager`（资源清理范例）

## 验收标准

- [ ] NOTES 覆盖表中至少 6 行「符号 → 作用」
- [ ] 完成选项 A 或 B，并记录 wraps 对 `__name__`（或文档）的影响
- [ ] 用自己的话解释 `IExecutionContext`（Protocol）与 `ExecutionContext`（实现）的关系
- [ ] 指出至少 1 个 `@contextmanager` 与 1 个类式 `__enter__`/`__exit__` 的真实位置
- [ ] 仓库改动已还原

## 延伸（选做）

本地单文件 `typed_cache.py`：`TypedDict` + `Protocol Clock` + 泛型 `TtlCache` + `counted` 装饰器 + `cache_span` 上下文管理器。仅作巩固，**不能替代**仓库主任务。
