# 11.10 模块化与包设计

> 通过高内聚、低耦合和明确导出，让大型代码库的职责与依赖保持可理解。

## 🎯 学习目标

完成本文档后，你将能够：

- 解释高内聚、低耦合与信息隐藏
- 根据变化原因划分 Python 模块与包
- 设计稳定、最小且显式的包公开接口
- 理解 controllers、services、core、models、tasks、extensions 的职责
- 沿 dify 的 controller → service → core/domain 边界分析依赖方向

## 📚 前置知识

- Python 模块、包、导入与 `__init__.py`
- 基本的分层架构和依赖注入知识
- 已阅读 `08-solid.md`
- 已阅读 `09-dry-kiss-yagni.md`

## 📦 核心概念

### 模块化的目标

模块化（Modular Design）把系统分成具有明确职责和接口的单元。
目标不是创建更多目录，而是让开发者能够：

- 在局部理解和修改代码
- 预测一个改动会影响哪些区域
- 独立测试核心规则
- 替换外部实现而不改业务策略
- 控制公开 API 和依赖方向

Python 中，一个 `.py` 文件是模块，一个包含模块的目录通常构成包。
架构层则可能由多个包共同组成。文件边界、包边界和架构边界不是同一个概念，
但都应服务于业务能力与变化隔离。

### 高内聚：相关内容放在一起

Cohesion（内聚）描述模块内部元素相关程度。
高内聚模块中的函数、类和常量共同服务于一个明确目的。

判断高内聚可以问：

- 能否用一句话描述模块职责，而且不需要“以及”？
- 模块中的函数是否使用相同核心数据和规则？
- 一项业务变化是否主要落在一个模块内？
- 模块名是否准确表达内容？

按技术动作堆积的 `utils.py` 往往低内聚，因为日期、权限、网络和字符串规则
没有共同变化原因。更好的选择是放回领域模块，或按稳定能力建立专门包。

### 低耦合：通过窄接口协作

Coupling（耦合）描述模块之间的依赖程度。
低耦合不是没有依赖，而是依赖明确、稳定且尽量小。

降低耦合的常见方法：

- 依赖 Protocol 或领域接口（详见 [Protocol 与 Generic](../01-fundamentals/09-protocol-generic.md)），而不是具体客户端
- 只传递所需数据，不暴露巨大上下文对象
- 避免跨层读取内部字段
- 将外部 I/O 封装在 adapter 或 extension 边界
- 使用领域异常跨越内部边界，在 controller 转成 HTTP 响应
- 避免循环导入和隐式全局状态

耦合也可能出现在数据格式上。两个包共享一个包含几十个可变字段的模型，
即使没有直接导入具体类，也会因数据契约变化而共同修改。

### 信息隐藏与公开接口

Information Hiding 要求模块隐藏容易变化的内部决策，只公开稳定能力。
Python 没有强制私有边界，但可以通过以下方式表达：

- 下划线命名内部符号，例如 `_normalize_input`
- 在 `__init__.py` 中显式重导出公共符号
- 使用 `__all__` 声明支持的导出集合
- 让调用者从包入口导入，而不是深入内部文件
- 不把数据库 session 或第三方响应对象泄漏到领域接口

`__all__` 主要约束 `from package import *` 并提供接口意图，
不是安全边界。真正的模块化还依赖团队遵守导入规则和测试契约。

### 包的粒度

包太大时职责模糊，包太小时导航和装配成本上升。
可以按以下信号调整：

**需要拆分**：

- 文件持续增长且包含多个变化原因
- 包内模块形成互不关联的子群
- 测试必须加载大量无关依赖
- 公开接口无法用一个领域概念描述

**不必拆分**：

- 代码虽多但围绕同一稳定能力
- 拆分后产生大量双向导入
- 新包只有转发，没有隐藏任何决策
- 唯一理由是追求目录形式整齐

应先画依赖关系和变化关系，再移动文件。仅按行数切割可能降低内聚。

### dify 后端主要包职责

结合项目规则，可以这样理解 `api/` 下的关键包：

| 包 | 主要职责 | 不应承担 |
|---|---|---|
| `controllers/` | 解析 HTTP 输入、调用 service、序列化响应 | 领域业务规则 |
| `services/` | 协调用例、repository、provider 和后台任务 | HTTP 框架细节 |
| `core/` | 核心能力与领域逻辑 | controller 响应拼装 |
| `models/` | SQLAlchemy 模型、持久化映射与基础类型 | endpoint 流程协调 |
| `tasks/` | Celery 后台任务入口、队列执行 | 同步 HTTP 响应逻辑 |
| `extensions/` | Flask 扩展和基础设施初始化 | 业务策略判断 |

这些职责不是绝对的文件分类口诀。判断新代码位置时，应沿调用链看它属于协议、
用例、领域、持久化还是基础设施，并遵守现有协作者和项目约定。

### Controller → Service → Core/Domain

典型调用方向是：

```text
HTTP Request
    ↓
Controller：校验与协议转换
    ↓
Service：协调一个应用用例
    ↓
Core/Domain：执行核心规则
    ↓
Repository / Provider / Extension：外部细节
```

返回路径将领域结果转换为 DTO 和 HTTP response。
依赖方向应尽量指向更稳定的策略边界，外围细节通过注入或 adapter 接入。

如果 core 导入 controller，就产生反向依赖；如果 controller 直接操作模型并实现规则，
则绕过 service 边界。两种情况都会扩大修改影响面。

### models、tasks 与 extensions 的边界

`models/` 表达持久化结构，但数据库模型不应自动成为所有层的公共 DTO。
将 ORM 对象直接泄漏给 API，会让表结构变化牵动公开协议。

`tasks/` 是异步执行入口。task 应保持可重试和幂等所需的明确输入，
调用 service 或 core 完成工作，而不是复制同步路径中的业务规则。

`extensions/` 负责数据库、缓存等框架扩展初始化。
业务代码通过稳定入口使用基础设施，而不是在任意模块重复创建 engine 或 client。

### 避免循环依赖

循环导入常表示职责或依赖方向不清：

```text
services.account → services.notification → services.account
```

处理方法不是把 import 移到函数内部掩盖问题，而是检查：

- 是否存在可下沉到 core/domain 的共同概念
- 是否应提取只含契约的窄模块
- 两个 service 是否其实属于同一高内聚能力
- 是否可由更高层 orchestrator 协调双方

局部导入有合法用途，但不应成为架构环路的默认补丁。

## 💻 代码示例

### 用包入口隐藏通知实现

**示例结构**：

```text
notifications/
├── __init__.py
├── contract.py
├── memory.py
└── service.py
```

**示例文件**：`examples/modular_notifications.py`  
**示例代码**（行 1-45，独立示例；注释分隔逻辑文件）：

```python
# notifications/contract.py
from typing import Protocol


class Sender(Protocol):
    def send(self, recipient: str, message: str) -> None: ...


# notifications/memory.py
class MemorySender:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.messages.append((recipient, message))


# notifications/service.py
class NotificationService:
    def __init__(self, sender: Sender) -> None:
        self._sender = sender

    def welcome(self, email: str) -> None:
        if "@" not in email:
            raise ValueError("invalid email")
        self._sender.send(email, "Welcome")


# notifications/__init__.py
__all__ = ["MemorySender", "NotificationService", "Sender"]


# app.py：调用者只依赖包公开接口。
sender = MemorySender()
service = NotificationService(sender)
service.welcome("user@example.com")

assert sender.messages == [
    ("user@example.com", "Welcome")
]
```

真实项目中，每段应位于注释标出的文件，并在 `__init__.py` 中从子模块显式导入。
示例把它们放在一个代码块中，是为了在 10-50 行内完整展示依赖关系。

`NotificationService` 与 `MemorySender` 高内聚地承担各自职责；
服务只依赖 `Sender` 的窄接口，具体实现可以替换。调用者从包入口获得公共符号，
无需知道 `memory.py` 的内部组织。

## 🔍 dify 仓库源码解读

### 分层边界和复用方向

**文件位置**：`/Users/xu/code/github/dify/api/AGENTS.md`  
**核心代码**（行 105-116）：

```markdown
### Architecture & Boundaries

- Mirror the layered architecture: controller → service → core/domain.
- Reuse existing helpers in `core/`, `services/`, and `libs/` before creating new abstractions.
- Optimise for observability: deterministic control flow, clear logging, actionable errors.

### Logging & Errors

- Never use `print`; use a module-level logger:
  - `logger = logging.getLogger(__name__)`
- Include tenant/app/workflow identifiers in log context when relevant.
- Raise domain-specific exceptions (`services/errors`, `core/errors`) and translate them into HTTP responses in controllers.
```

**解读**：

- 第 107 行明确 controller → service → core/domain 的分层调用方向。
- 第 108 行要求先在既有层寻找 helper，避免同一能力被散落到多个新包。
- 第 109 行的确定性控制流、清晰日志和可操作错误，让跨模块协作可观察。
- 第 116 行把领域异常定义与 HTTP 翻译分开，避免 core 耦合 Web 协议。
- 这段规则既约束模块放置，也约束依赖穿越边界时使用的契约。

实际顶层目录与职责对应如下：

```text
/Users/xu/code/github/dify/api/controllers/
/Users/xu/code/github/dify/api/services/
/Users/xu/code/github/dify/api/core/
/Users/xu/code/github/dify/api/models/
/Users/xu/code/github/dify/api/tasks/
/Users/xu/code/github/dify/api/extensions/
```

目录结构本身不是架构证明；评审时还要检查实际 import、对象创建位置和副作用。

### services.errors 的显式模块导出

**文件位置**：`/Users/xu/code/github/dify/api/services/errors/__init__.py`  
**核心代码**（行 1-30；源码工具以 0 起始显示为 0-29）：

```python
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

__all__ = [
    "account",
    "app",
    "app_model_config",
    "audio",
    "base",
    "conversation",
    "dataset",
    "document",
    "enterprise",
    "file",
    "index",
    "message",
]
```

**解读**：

- 第 1-14 行使用显式相对导入汇总错误子模块，包入口清楚展示可发现模块。
- `account`、`app`、`dataset` 等按领域拆分，错误定义与所属能力保持内聚。
- 第 16-30 行通过 `__all__` 声明包希望公开的模块集合，避免通配导入暴露临时名称。
- 新领域错误模块需要有意识地加入入口，公共表面变化可在评审中清楚看到。
- 这里导出的是子模块而不是所有异常类，避免包根命名空间膨胀与类名冲突。

## ✅ 关键要点总结

- 高内聚让模块围绕一个变化原因组织，低耦合让模块通过窄契约协作。
- 包边界应隐藏易变细节，只公开稳定能力。
- `__init__.py` 与 `__all__` 可以表达公共接口意图，但不能替代架构纪律。
- controllers 负责 HTTP，services 协调用例，core/domain 承载核心能力。
- models 管理持久化映射，tasks 承载后台入口，extensions 初始化基础设施。
- 循环依赖通常应通过重新划分职责或下沉契约解决，而不是隐藏 import。
- 目录结构只是起点，必须检查真实依赖方向、对象装配和副作用。

## 🧪 练习题

### 练习：为代码选择模块（基础）

把以下能力放入最合适的 dify 后端包，并解释原因：

- 解析 GET 查询参数
- 计算工作流领域状态
- 初始化 Redis 扩展
- 定义 SQLAlchemy 映射
- 投递可重试的后台清理任务
- 协调 repository 与 provider 完成应用用例

同时说明每项能力不应放在哪一层。

### 练习：设计包公开接口（进阶）

把独立示例拆成真实的四个 Python 文件：

- 在 `__init__.py` 中显式重导出公共符号
- 让调用者不导入 `memory.py`
- 增加一个不公开的 `_normalize_email()`
- 编写测试证明替换 `MemorySender` 不影响 service
- 运行静态检查确认不存在循环导入

### 练习：绘制 dify 包依赖图（挑战）

选择一个 `/Users/xu/code/github/dify/api/controllers/console/` 入口，
向下追踪到 service、core、model 或 task，记录：

- 每次跨包调用的输入和输出
- 哪一层创建具体依赖
- 领域异常在哪里定义、在哪里翻译
- 是否绕过了规定层级
- 是否有模型或第三方对象泄漏到不该知道它的层

最后提出一个提高内聚或降低耦合的小步重构，并列出安全测试。

## 📖 参考资料

- `/Users/xu/code/github/dify/api/AGENTS.md`
- `/Users/xu/code/github/dify/api/services/errors/__init__.py`
- `/Users/xu/code/github/dify/api/controllers/`
- `/Users/xu/code/github/dify/api/services/`
- `/Users/xu/code/github/dify/api/core/`
- Python 模块文档：https://docs.python.org/3/tutorial/modules.html
- Robert C. Martin, *Clean Architecture*

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
