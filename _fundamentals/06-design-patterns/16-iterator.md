# 3.4 迭代器模式（Iterator）

> 迭代器模式提供一种顺序访问聚合对象元素的方法，而又不暴露其底层表示。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解迭代器模式的核心（统一遍历接口）
- 掌握 Python 迭代器协议（`__iter__` / `__next__`）
- 区分内部迭代器 vs 外部迭代器
- 识别 SQLAlchemy 的查询迭代器

## 📚 前置知识

- Python 基础（for 循环）
- 16-observer.md

## 1. 核心概念

### 1.1 迭代器模式的核心思想

把"遍历逻辑"从聚合对象中抽离，由迭代器对象负责。客户端通过统一接口访问元素。

### 1.2 Python 迭代器协议

```python
class Iterator:
    def __iter__(self): return self  # 返回自身
    def __next__(self): ...          # 返回下一个元素或抛 StopIteration
```

### 1.3 for 循环的本质

```python
for item in iterable:
    body
# 等价于：
it = iter(iterable)
while True:
    try:
        item = next(it)
        body
    except StopIteration:
        break
```

### 1.4 内部迭代器 vs 外部迭代器

| 类型 | 控制权 | Python |
|------|--------|--------|
| 内部迭代器（forEach） | 迭代器控制 | 不直接支持 |
| 外部迭代器 | 客户端控制 | `for ... in` |

## 2. 代码示例

### 2.1 Python 自定义迭代器

```python
class Countdown:
    """自定义可迭代对象——倒计时"""
    def __init__(self, start: int):
        self.start = start

    def __iter__(self):
        return CountdownIterator(self.start)


class CountdownIterator:
    def __init__(self, start: int):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self) -> int:
        if self.current <= 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1


# 使用
for i in Countdown(3):
    print(i)  # 3, 2, 1
```

### 2.2 生成器（最优雅的迭代器）

```python
def fibonacci(limit: int):
    """生成器——自动实现迭代器协议"""
    a, b = 0, 1
    while a < limit:
        yield a
        a, b = b, a + b

# 使用
for n in fibonacci(100):
    print(n)  # 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89
```

### 2.3 反向迭代器

```python
class ReverseList:
    def __init__(self, data: list):
        self.data = data

    def __iter__(self):
        return ReverseIterator(self.data)


class ReverseIterator:
    def __init__(self, data: list):
        self.data = data
        self.index = len(data)

    def __next__(self):
        self.index -= 1
        if self.index < 0:
            raise StopIteration
        return self.data[self.index]


for item in ReverseList([1, 2, 3]):
    print(item)  # 3, 2, 1
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 SQLAlchemy 查询的迭代器

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1-30）：

```python
from sqlalchemy.orm import Session

from extensions.ext_database import db
from models.account import Account

def iter_active_accounts() -> "Iterator[Account]":
    """迭代活跃账户——迭代器模式"""
    with Session(db.engine) as session:
        # scalars() 返回可迭代的 ScalarResult
        result = session.scalars(
            select(Account).where(Account.status == "active")
        )
        # result 是迭代器，自动实现 __iter__
        for account in result:   # 迭代器模式
            yield account
```

**解读**：
- `session.scalars()` 返回迭代器——延迟加载
- `for` 循环逐行读取，不一次性加载全部
- **整体设计**：用迭代器实现大结果集的流式处理

### 3.2 MyBatis 的 RowBounds 游标

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
**核心代码**：

```java
// MyBatis 流式查询——避免 OOM
try (Cursor<UserDO> cursor = userMapper.scanUsers()) {
    cursor.forEach(user -> process(user));
}

@Mapper
public interface UserMapper {
    // 流式查询方法
    @Options(fetchSize = 1000)  // 每次 fetch 1000 行
    @Select("SELECT * FROM users")
    Cursor<UserDO> scanUsers();  // 返回游标（迭代器）
}
```

**解读**：
- `Cursor` 是 MyBatis 的迭代器
- `fetchSize = 1000` 每次只加载 1000 行——避免大结果集 OOM
- **整体设计**：用游标迭代器实现流式查询

### 3.3 dify 的工作流节点迭代器

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/graph_engine/`
**核心代码**：

```python
class GraphIterator:
    """工作流图迭代器——按拓扑顺序遍历节点"""

    def __init__(self, graph: dict):
        self.graph = graph
        self.visited = set()
        self.queue = [entry_node]

    def __iter__(self):
        return self

    def __next__(self):
        if not self.queue:
            raise StopIteration
        node = self.queue.pop(0)
        if node in self.visited:
            return self.__next__()
        self.visited.add(node)
        # 加入子节点
        for child in self.graph.get(node, []):
            if child not in self.visited:
                self.queue.append(child)
        return node
```

**解读**：
- 用迭代器实现工作流图的拓扑遍历
- 每次返回一个节点，避免一次性展开整个图
- **整体设计**：迭代器用于复杂数据结构的流式处理

## 4. 关键要点总结

- 迭代器 = 统一遍历接口 + 流式处理
- Python `__iter__` / `__next__` 协议
- 生成器是最简洁的迭代器实现
- SQLAlchemy `scalars()`、MyBatis `Cursor` 都是迭代器
- 适合大结果集、复杂数据结构的遍历

## 5. 练习题

### 练习 1：基础
为树形结构实现深度优先迭代器（不用递归，用栈）。

### 练习 2：进阶
阅读 dify 的 `graph_engine`，分析工作流图的迭代过程。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
- Python 迭代器：https://docs.python.org/3/tutorial/classes.html#iterators
- 《设计模式》第 5 章：迭代器模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13