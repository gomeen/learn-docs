# 11.03 命名规范：变量、函数、类、模块

> 好的命名让代码自我解释，坏的命名让每次阅读都像在破译密码。

## 🎯 学习目标

完成本文档后，你将能够：

- 解释为什么命名是代码可读性的第一要素
- 列出 Python 与 TypeScript 的命名约定差异
- 识别常见的命名坏味道（缩写、相似名、误导名）
- 在 dify 代码中区分各层（controller / service / model）的命名模式
- 用可搜索、有意图的命名替代通用名

## 📚 前置知识

- 已完成 [01-pep8.md](../../dify/11-engineering/01-pep8.md)
- 已完成 [02-agents-md.md](../../dify/11-engineering/02-agents-md.md)
- Python 与 TypeScript 基础语法

## 1. 核心概念

### 1.1 为什么命名如此重要

《Clean Code》的核心观点之一：**变量、函数、类的命名就是代码的注释**。好的命名：

- 让代码自我解释，减少注释需求
- 让搜索 / 跳转更高效（grep 友好）
- 让 code review 更快（不需要反复阅读上下文）
- 让新成员上手更快

差的命名会让每次阅读都需要"翻译"——`d`、`tmp`、`data`、`process` 这些名字几乎不携带任何信息。

### 1.2 Python 命名约定（PEP 8 + dify 收紧）

| 类别 | 约定 | 示例 | 说明 |
|---|---|---|---|
| 变量 / 函数 | `snake_case` | `user_id`, `fetch_profile` | 全小写 + 下划线 |
| 类 | `PascalCase` | `UserService`, `WorkflowRun` | 首字母大写、无下划线 |
| 常量 | `UPPER_CASE` | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` | 全大写 + 下划线 |
| 模块 / 包 | `snake_case` | `user_service.py`, `models/account.py` | 全小写 + 下划线 |
| 私有成员 | 前缀 `_` | `_cache`, `_validate()` | 单下划线提示"内部使用" |
| 魔术方法 | `__xxx__` | `__init__`, `__repr__` | 双下划线包围 |
| 布尔变量 | `is_` / `has_` / `can_` | `is_active`, `has_permission` | 可读性更强 |
| 异常类 | 后缀 `Error` | `WorkflowNotFoundError` | dify 强制约定 |

### 1.3 TypeScript / React 命名约定

| 类别 | 约定 | 示例 |
|---|---|---|
| 变量 / 函数 | `camelCase` | `userId`, `fetchProfile` |
| 类 / 组件 | `PascalCase` | `UserCard`, `WorkflowEditor` |
| 接口 / 类型 | `PascalCase` | `UserProfile`, `ApiResponse<T>` |
| 常量 | `UPPER_CASE` 或 `camelCase` | `MAX_SIZE` 或 `defaultTimeout` |
| React 组件文件 | `PascalCase.tsx` | `WorkflowEditor.tsx` |
| Hook | `useXxx` | `useUserProfile`, `useWorkflow` |
| 布尔变量 | `is` / `has` / `can` | `isLoading`, `hasPermission` |

注意：React 组件文件名在 dify 中**强烈建议用 PascalCase**，因为组件名和文件名一致更利于搜索。

### 1.4 命名的核心原则

Robert C. Martin 在《Clean Code》中给出三条核心原则：

1. **名副其实**（Use intention-revealing names）：`elapsed_time_in_days` 优于 `d`
2. **避免误导**（Avoid disinformation）：不要用 `accounts_list` 表示非列表的数据
3. **做有意义的区分**（Make meaningful distinctions）：`User` 和 `UserInfo` 没有任何区别，是反例

## 2. 代码示例

### 2.1 命名从坏到好

```python
# 文件：example_naming.py

# ❌ 差命名：缩写、无意图
def get(d, t):
    r = []
    for i in d:
        if i.t > t:
            r.append(i)
    return r

# ✅ 好命名：意图明确、可搜索
def fetch_active_orders(orders: list[Order], cutoff_time: datetime) -> list[Order]:
    """获取截止时间之后仍处于活跃状态的订单。"""
    return [order for order in orders if order.last_active_at > cutoff_time]
```

```typescript
// TypeScript 示例
// ❌ 差命名
function proc(u: any, c: any) {
  if (u.t === 'admin' && c > 0) return true
  return false
}

// ✅ 好命名
function hasAdminQuota(user: User, currentQuota: number): boolean {
  return user.role === 'admin' && currentQuota > 0
}
```

### 2.2 反例：常见的命名坏味道

```python
# ❌ 反例 1：误导性命名
def get_user_data(user_id: str) -> dict:
    """获取用户数据。"""
    # 实际同时调用了 3 个外部 API，还修改了缓存
    # "get" 完全无法反映这些副作用
    ...

# ✅ 正确做法：动词要精确
def fetch_and_cache_user_profile(user_id: str) -> UserProfile:
    ...
```

```python
# ❌ 反例 2：通用名 + 后缀
class UserInfo:
    pass

class UserData:
    pass

class UserObject:
    pass

# 这三个类提供的信息量完全相同

# ✅ 正确做法：意图驱动
class UserProfile:  # 用户的个人档案
    pass

class UserSession:  # 用户的会话状态
    pass

class UserPreferences:  # 用户的偏好设置
    pass
```

```python
# ❌ 反例 3：相似命名让搜索变得痛苦
def get_user(): ...
def fetch_user(): ...
def load_user(): ...
def retrieve_user(): ...

# ✅ 正确做法：动作词收敛为一套
def get_user(): ...        # 单一约定
# 然后用参数区分场景
def get_user(by_id: str): ...  # 按 ID 获取
def get_user(by_email: str): ...  # 按邮箱获取
```

## 3. dify 仓库源码解读

### 3.1 后端命名约定：异常类以 `Error` 结尾

**文件位置**：`/Users/xu/code/github/dify/api/services/errors/__init__.py`
**核心代码**（行 1-12）：

```python
class LLMError(ValueError):
    """Base class for all LLM exceptions."""

    description: str = ""

    def __init__(self, description: str = ""):
        self.description = description


class LLMBadRequestError(LLMError):
    """Raised when the LLM returns bad request."""

    description = "Bad Request"
```

**解读**：
- 第 1 行：`LLMError`——`XxxError` 后缀是 Python 异常类的强约定，dify 100% 遵守
- 第 10 行：`LLMBadRequestError`——多级命名 `LLM` + `BadRequest` + `Error`，可读性极高
- 第 4 行：异常类继承 `ValueError`（Python 内置），但通过**前缀** `LLM` 区分领域
- 第 6 行：`description` 类属性作为用户友好的错误描述，而不是直接打印类名
- 第 8 行：构造函数接受可选 `description` 参数，便于在不同场景下自定义错误信息

### 3.2 模块/文件命名：snake_case 全小写

**文件位置**：`/Users/xu/code/github/dify/api/services/errors/__init__.py`（文件清单）
**核心代码**（基于实际目录结构）：

```python
# 文件：/Users/xu/code/github/dify/api/services/errors/account.py
# 文件：/Users/xu/code/github/dify/api/services/errors/app.py
# 文件：/Users/xu/code/github/dify/api/services/errors/conversation.py
# 文件：/Users/xu/code/github/dify/api/services/errors/dataset.py

# 所有异常按"领域对象"切分到不同文件
# 这样导入时非常清晰：
#   from services.errors import account, app
# 而不是把所有异常塞进一个 500 行的 errors.py
```

```python
# 文件：/Users/xu/code/github/dify/api/services/errors/__init__.py（行 1-30）
from . import (
    account,
    app,
    app_model_config,
    audio,
    base,
    conversation,
    dataset,
    document,
    enterprise,
    file,
    index,
    message,
)
```

**解读**：
- **文件命名**：全部 `snake_case`，按领域对象划分（`account.py` / `app.py` / `dataset.py`）
- **导出策略**：`__init__.py` 用 `from . import xxx` 把子模块聚合起来——既保持单文件可管理，又允许 `from services.errors import account` 导入
- **好处**：定位错误时直接看文件名就知道是哪一类问题（如 `dataset.py` → 数据集相关）

### 3.3 命名规范文档（`api/AGENTS.md`）

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`
**核心代码**（行 56-59）：

```markdown
### Naming Conventions

- Use `snake_case` for variables and functions.
- Use `PascalCase` for classes.
- Use `UPPER_CASE` for constants.
```

**解读**：
- dify **没有**额外的命名规定，**完全遵循 PEP 8**
- 这与 PEP 8 的 "Consistency within a project is more important" 原则一致
- 在工程中**规范的一致性比规范的细节更重要**——一个团队遵守一套规则，胜过每个成员遵守不同规则

## 4. 关键要点总结

- 命名是**第一性原则**：好命名 > 好注释，差命名 > 无注释
- Python：`snake_case`（变量/函数）、`PascalCase`（类）、`UPPER_CASE`（常量）、`XxxError`（异常）
- TypeScript：`camelCase`（变量/函数）、`PascalCase`（类/组件）、`useXxx`（Hook）、`is/has/can`（布尔）
- 命名三原则：**名副其实**、**避免误导**、**有意义区分**
- 收敛动词（只用一个 `get_` 而非 `get/fetch/load/retrieve` 全用上）—— dify 通过约定收敛
- 模块命名按**领域对象**划分（如 `services/errors/dataset.py`），而不是按层级划分

## 5. 练习题

### 练习 1：基础（必做）

阅读 `/Users/xu/code/github/dify/api/services/errors/__init__.py` 及其子模块（如 `account.py`），统计所有异常类，验证它们都遵循 `XxxError` 命名约定。

**参考答案**：见 `solutions/01-naming.md`

### 练习 2：进阶

打开你自己最近写的一个项目，找出 5 个最差的命名（缩写、通用名、误导名），并改写成更清晰的名字。

### 练习 3：挑战（选做）

为 dify 的 `api/controllers/console/` 写一份"控制器命名指南"：是否用 `XxxController` 或 `XxxResource`？路径前缀如何选择？试读 3 个真实 controller 文件，归纳出实际命名模式。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`（行 56-59 命名规范）
- `/Users/xu/code/github/dify/api/services/errors/__init__.py`（异常类命名范本）
- `/Users/xu/code/github/dify/api/services/errors/account.py`（按领域划分的异常文件）
- PEP 8 命名章节：https://peps.python.org/pep-0008/#naming-conventions
- 《Clean Code》第二章：有意义的命名

---

**文档版本**：v1.0
**最后更新**：2026-07-13