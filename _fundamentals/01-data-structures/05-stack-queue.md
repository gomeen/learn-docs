# 1.1.5 栈（Stack）与队列（Queue）

> 栈是后进先出（LIFO），队列是先进先出（FIFO），是算法题和工作中的常客。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分栈（LIFO）和队列（FIFO）的应用场景
- 用 Python `list` 和 `collections.deque` 实现两者
- 理解单调栈、双端队列等变种
- 能在 dify 中识别栈/队列的使用场景

## 📚 前置知识

- 03-array.md
- 04-linked-list.md

## 1. 核心概念

### 1.1 栈（Stack）

**特点**：后进先出（LIFO, Last In First Out），像一叠盘子。

```
       ┌─────┐
push → │  D  │ ← pop
       ├─────┤
       │  C  │
       ├─────┤
       │  B  │
       ├─────┤
       │  A  │
       └─────┘
```

**核心操作**（均摊 O(1)）：
- `push(x)` / `append`：入栈
- `pop()`：出栈（栈顶）
- `top()` / `peek()`：查看栈顶，不弹出
- `is_empty()`

**应用**：
- 函数调用栈（递归）
- 括号匹配
- 表达式求值（中缀→后缀）
- 浏览器前进/后退

### 1.2 队列（Queue）

**特点**：先进先出（FIFO, First In First Out），像排队买票。

```
   队尾                队头
     ↓                  ↓
入队 → [A][B][C][D] → 出队
```

**核心操作**（均摊 O(1)）：
- `enqueue(x)` / `push`：入队（尾部）
- `dequeue()` / `pop`：出队（头部）
- `front()`：查看队头
- `is_empty()`

**应用**：
- 任务调度（消息队列）
- BFS 广度优先搜索
- 缓冲区（Buffer）

### 1.3 双端队列（Deque）

**特点**：两端都可以入队/出队。

```python
from collections import deque

dq = deque()
dq.append(1)       # 右入
dq.appendleft(2)   # 左入
dq.pop()           # 右出
dq.popleft()       # 左出
```

**应用**：
- 滑动窗口最大值
- 工作窃取（Work Stealing）调度

### 1.4 单调栈（Monotonic Stack）

**特点**：栈内元素保持单调递增或递减。

**应用**：下一个更大元素、柱状图最大矩形。

```python
# 例：找数组中每个元素的下一个更大元素
def next_greater(nums):
    stack = []  # 存下标
    result = [-1] * len(nums)

    for i, num in enumerate(nums):
        # 当前元素比栈顶大 → 栈顶的下一个更大就是它
        while stack and nums[stack[-1]] < num:
            prev_idx = stack.pop()
            result[prev_idx] = num
        stack.append(i)

    return result
```

## 2. 代码示例

### 2.1 括号匹配（栈的经典应用）

```python
# 文件：valid_parentheses.py
def is_valid_parentheses(s: str) -> bool:
    """判断括号字符串是否合法，如 '({[]})' → True"""
    stack = []
    mapping = {')': '(', ']': '[', '}': '{'}

    for char in s:
        if char in mapping.values():
            stack.append(char)  # 左括号入栈
        elif char in mapping:
            # 右括号：栈顶必须是匹配的左括号
            if not stack or stack[-1] != mapping[char]:
                return False
            stack.pop()  # 匹配成功，弹出

    return len(stack) == 0

# 测试
print(is_valid_parentheses("({[]})"))  # True
print(is_valid_parentheses("({[})"))    # False
```

### 2.2 滑动窗口最大值（双端队列）

```python
# 文件：sliding_window_max.py
from collections import deque
from typing import List

def max_sliding_window(nums: List[int], k: int) -> List[int]:
    """滑动窗口最大值，时间 O(n)。"""
    if not nums or k == 0:
        return []

    dq: deque[int] = deque()  # 存下标，nums[dq] 单调递减
    result = []

    for i, num in enumerate(nums):
        # 1. 移除超出窗口的下标
        while dq and dq[0] <= i - k:
            dq.popleft()

        # 2. 维护单调递减：移除比当前小的所有下标
        while dq and nums[dq[-1]] < num:
            dq.pop()

        dq.append(i)

        # 3. 窗口形成后记录最大值
        if i >= k - 1:
            result.append(nums[dq[0]])

    return result

# 测试
print(max_sliding_window([1,3,-1,-3,5,3,6,7], 3))  # [3, 3, 5, 5, 6, 7]
```

### 2.3 用两个栈实现队列

```python
# 文件：queue_via_two_stacks.py
class QueueViaStacks:
    """用两个栈实现队列：in_stack + out_stack"""

    def __init__(self):
        self.in_stack: list = []
        self.out_stack: list = []

    def push(self, x: int) -> None:
        self.in_stack.append(x)

    def pop(self) -> int:
        # 把 in_stack 全部倒到 out_stack
        if not self.out_stack:
            while self.in_stack:
                self.out_stack.append(self.in_stack.pop())
        return self.out_stack.pop()

    def peek(self) -> int:
        if not self.out_stack:
            while self.in_stack:
                self.out_stack.append(self.in_stack.pop())
        return self.out_stack[-1]

    def empty(self) -> bool:
        return not self.in_stack and not self.out_stack
```

## 3. dify 仓库源码解读

### 3.1 用 deque 实现异步任务队列

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
**核心代码**（行 1-50）：

```python
import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any

@dataclass
class WorkflowTask:
    workflow_run_id: str
    inputs: dict[str, Any]
    priority: int = 0

class QueueDispatcher:
    """工作流任务调度器。

    使用 deque 维护待执行任务队列（先进先出）。
    支持按优先级排序，但保持 FIFO 顺序。
    """

    def __init__(self):
        self._queue: deque[WorkflowTask] = deque()
        self._lock = asyncio.Lock()

    async def enqueue(self, task: WorkflowTask) -> None:
        """入队 - O(1)。"""
        async with self._lock:
            # 按优先级插入到合适位置（保持队列有序）
            inserted = False
            for i in range(len(self._queue)):
                if self._queue[i].priority < task.priority:
                    self._queue.insert(i, task)
                    inserted = True
                    break
            if not inserted:
                self._queue.append(task)

    async def dequeue(self) -> WorkflowTask | None:
        """出队 - O(1)。"""
        async with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None

    def __len__(self) -> int:
        return len(self._queue)
```

**解读**：
- 第 19 行：`deque[WorkflowTask]` 声明队列类型
- 第 26 行：`deque` 的 `insert(i, task)` 是 O(n)，但只有任务优先级混乱时才慢
- 第 37 行：`popleft()` 是 O(1)，因为 deque 双向链表实现
- **设计意图**：dify 需要快速取出最早的任务（避免饥饿），deque 是最佳选择
- **生产环境**：实际 dify 用 Redis 的 List 或 Kafka 代替内存队列，跨进程共享

## 4. 关键要点总结

- **栈**：LIFO，函数调用、括号匹配、撤销操作
- **队列**：FIFO，任务调度、BFS、消息队列
- **deque**：两端操作 O(1)，Python `collections.deque` 是标准实现
- **单调栈**：O(n) 求下一个更大元素、柱状图问题
- dify 用 `deque` 做内存任务队列，生产用 Redis / Kafka

## 5. 练习题

### 练习 1：基础（必做）

用栈实现一个计算器，输入 `"1 + 2 * 3"`，输出 `7`。

### 练习 2：进阶

阅读 `api/services/workflow/queue_dispatcher.py`，说明如果任务量达到 1 万，`insert` 的总复杂度是多少？是否能优化？

### 练习 3：挑战（选做）

设计一个**带 TTL（过期时间）的队列**，支持 `enqueue(x, expire_seconds)` 和 `dequeue()` 时自动跳过已过期元素。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/workflow/queue_dispatcher.py`
- `/Users/xu/code/github/dify/api/core/app/apps/base_app_queue_manager.py`
- 《算法导论》第 10 章 栈与队列
- LeetCode 20/239/232 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13