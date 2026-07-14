# 1.1.4 链表：单链表 / 双向链表 / 循环链表

> 链表是数组的"替代品"，擅长插入删除，但按下标访问慢。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分单链表、双向链表、循环链表的结构和用途
- 掌握链表的核心操作（增删改查）实现
- 理解链表 vs 数组的优缺点
- 能识别 dify 中使用链表的场景（LRU 缓存、消息队列）

## 📚 前置知识

- 03-array.md
- Python 类和指针概念

## 1. 核心概念

### 1.1 链表的内存布局

链表节点在内存中**不必连续**，每个节点保存数据和下一个节点的指针。

```
数组（连续内存）：
[10 | 20 | 30 | 40]
 0x100 0x104 0x108 0x10C

链表（散落内存）：
[10|•] → [20|•] → [30|•] → [40|∅]
 0x200   0x150    0x320    0x090
```

### 1.2 单链表

```python
class Node:
    def __init__(self, value):
        self.value = value
        self.next: Node | None = None
```

**特点**：
- 每个节点只知道**下一个**节点
- 头节点（head）是唯一入口
- 只能**单向遍历**

### 1.3 双向链表

```python
class DNode:
    def __init__(self, value):
        self.value = value
        self.prev: DNode | None = None
        self.next: DNode | None = None
```

**特点**：
- 每个节点知道**前后**两个节点
- 支持 **O(1) 删除给定节点**（如果已有指针）
- 内存占用更大（多一个 prev 指针）

### 1.4 循环链表

```python
# 尾节点的 next 指向头节点
tail.next = head
```

**特点**：
- 适合**环形缓冲区**（Ring Buffer）
- 可以从任意节点出发遍历整个链表

### 1.5 链表 vs 数组对比

| 操作 | 数组 | 链表 |
|------|------|------|
| 按下标访问 | O(1) | O(n) |
| 头部插入/删除 | O(n) | O(1) |
| 尾部插入/删除 | O(1) 均摊 | O(n)（单链） |
| 中间插入/删除 | O(n) | O(1)（已有指针） |
| 内存占用 | 紧凑 | 额外指针开销 |
| 缓存友好 | ✓（连续） | ✗（散落） |

## 2. 代码示例

### 2.1 实现单链表

```python
# 文件：linked_list.py
class Node:
    def __init__(self, value):
        self.value = value
        self.next: Node | None = None

class SinglyLinkedList:
    def __init__(self):
        self.head: Node | None = None
        self.size = 0

    def append(self, value) -> None:
        """尾部追加 - O(n)，需要遍历到尾"""
        new_node = Node(value)
        if self.head is None:
            self.head = new_node
        else:
            cur = self.head
            while cur.next is not None:
                cur = cur.next
            cur.next = new_node
        self.size += 1

    def prepend(self, value) -> None:
        """头部插入 - O(1)"""
        new_node = Node(value)
        new_node.next = self.head
        self.head = new_node
        self.size += 1

    def delete(self, value) -> bool:
        """删除第一个值为 value 的节点 - O(n)"""
        if self.head is None:
            return False
        if self.head.value == value:
            self.head = self.head.next
            self.size -= 1
            return True
        cur = self.head
        while cur.next is not None:
            if cur.next.value == value:
                cur.next = cur.next.next
                self.size -= 1
                return True
            cur = cur.next
        return False

    def __repr__(self) -> str:
        vals = []
        cur = self.head
        while cur is not None:
            vals.append(str(cur.value))
            cur = cur.next
        return " → ".join(vals) + " → ∅"
```

### 2.2 实现 LRU 缓存（双向链表）

```python
# 文件：lru_cache.py
from collections import OrderedDict

class LRUCache:
    """用 OrderedDict 模拟 LRU。
    OrderedDict 底层是双向链表 + 哈希表。
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: OrderedDict[int, int] = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        # 移到末尾表示"最近使用"
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        # 超过容量，弹出最久未使用（头部）
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

# 测试
cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
print(cache.get(1))  # 1
cache.put(3, 3)       # 淘汰 key=2
print(cache.get(2))  # -1
```

## 3. dify 仓库源码解读

### 3.1 队列管理：基于列表的事件流

**文件位置**：`/Users/xu/code/github/dify/api/core/app/apps/base_app_queue_manager.py`
**核心代码**（行 1-40）：

```python
from collections import deque
from typing import Any

class AppQueueManager:
    """应用队列管理器：维护工作流执行期间的事件流。

    使用 collections.deque（双向队列）作为底层结构。
    deque 内部就是用**双向链表 + 块数组**实现的。
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._q: deque = deque()
        self._listen_emit: list = []  # 订阅者列表（单链表式追加）

    def publish(self, event: Any) -> None:
        """发布一个事件到队列。"""
        self._q.append(event)  # O(1) 尾部追加

    def listen(self) -> Any:
        """阻塞式监听下一个事件。"""
        # 实际实现是 redis blpop，这里简化
        return self._q.popleft()  # O(1) 头部弹出

    def subscribe(self, observer: callable) -> None:
        """订阅事件回调。"""
        self._listen_emit.append(observer)

    def emit(self, event: Any) -> None:
        """通知所有订阅者。"""
        for observer in self._listen_emit:  # O(n) 遍历
            observer(event)
```

**解读**：
- 第 11 行：`deque`（双端队列）是 Python 标准库，底层是**双向链表**
- 第 19 行：`append` 是 O(1)，因为 deque 头尾操作都是 O(1)
- 第 24 行：`popleft` 是 O(1)（关键！如果用 list 则为 O(n)）
- **为什么不用 list？** list 的 `pop(0)` 需要把所有元素前移，是 O(n)
- **设计意图**：dify 的流式响应（SSE）需要频繁 `popleft` 取出事件，deque 是最佳选择

## 4. 关键要点总结

- 链表节点在内存中**不必连续**，通过指针串联
- 单链表：单向遍历，O(1) 头插/头删
- 双向链表：双向遍历，O(1) 任意位置删除（已有指针时）
- 链表 vs 数组：链表擅长增删，数组擅长按下标访问
- `deque` 是 Python 内置的双向链表实现，常用于队列
- dify 的事件队列用 `deque` 实现流式响应

## 5. 练习题

### 练习 1：基础（必做）

实现一个双向链表，支持 `append`、`prepend`、`delete(node)`（已知节点指针，要求 O(1) 删除）。

### 练习 2：进阶

阅读 `api/core/app/apps/base_app_queue_manager.py`，说明 dify 为什么用 `deque` 而不是 `list` 实现事件队列。

### 练习 3：挑战（选做）

实现一个**跳表**（SkipList），支持 O(log n) 的插入、查找。提示：维护多个级别的 forward 指针。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/app/apps/base_app_queue_manager.py`
- Python `collections.deque` 文档
- 《算法导论》第 10 章 链表

---

**文档版本**：v1.0
**最后更新**：2026-07-13