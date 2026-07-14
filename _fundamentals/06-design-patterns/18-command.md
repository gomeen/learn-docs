# 3.6 命令模式（Command）

> 命令模式将请求封装为对象，从而可以参数化、队列化、撤销。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解命令模式的核心（请求对象化）
- 掌握命令模式的 4 个角色
- 识别 Celery 任务就是命令对象
- 知道命令模式的适用场景

## 📚 前置知识

- 02-factory-method.md
- 16-observer.md

## 1. 核心概念

### 1.1 命令模式的 4 个角色

1. **Command（命令接口）**：声明执行方法
2. **ConcreteCommand（具体命令）**：绑定接收者和动作
3. **Invoker（调用者）**：触发命令执行
4. **Receiver（接收者）**：真正执行操作的对象

### 1.2 命令模式的核心思想

把"请求"封装成对象，使请求可以被存储、传递、撤销、记录日志。

### 1.3 适用场景

- 需要撤销 / 重做操作
- 需要队列化请求（异步任务）
- 需要事务化请求
- 需要宏命令（多个命令组合）

## 2. 代码示例

### 2.1 经典命令模式

```python
from abc import ABC, abstractmethod

class Command(ABC):
    """命令接口"""
    @abstractmethod
    def execute(self) -> None:
        ...

    @abstractmethod
    def undo(self) -> None:
        ...


class Light:
    """接收者"""
    def on(self) -> None:
        print("Light ON")

    def off(self) -> None:
        print("Light OFF")


class LightOnCommand(Command):
    """具体命令：开灯"""
    def __init__(self, light: Light):
        self._light = light

    def execute(self) -> None:
        self._light.on()

    def undo(self) -> None:
        self._light.off()


class RemoteControl:
    """调用者：遥控器"""
    def __init__(self):
        self._history: list[Command] = []

    def press(self, command: Command) -> None:
        command.execute()
        self._history.append(command)

    def undo_last(self) -> None:
        if self._history:
            self._history.pop().undo()


# 使用
light = Light()
remote = RemoteControl()
remote.press(LightOnCommand(light))    # Light ON
remote.undo_last()                      # Light OFF
```

### 2.2 命令队列

```python
from collections import deque

class TaskQueue:
    """命令队列——异步任务"""
    def __init__(self):
        self._queue: deque = deque()

    def add(self, command: Command) -> None:
        self._queue.append(command)

    def execute_all(self) -> None:
        while self._queue:
            command = self._queue.popleft()
            command.execute()


# 批量处理
queue = TaskQueue()
queue.add(LightOnCommand(light))
queue.add(LightOnCommand(light))
queue.execute_all()  # 执行所有命令
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 Celery 任务（命令模式）

**文件位置**：`/Users/xu/code/github/dify/api/tasks/workflow.py`
**核心代码**（行 1-50）：

```python
from celery import shared_task

@shared_task
def run_workflow_task(workflow_id: str, inputs: dict, user_id: str) -> dict:
    """运行工作流任务——命令对象"""
    # 1. 加载工作流（接收者）
    workflow = load_workflow(workflow_id)

    # 2. 执行（命令的执行方法）
    result = execute_workflow(workflow, inputs, user_id)
    return result


# 调用者（API 层）
def trigger_workflow(workflow_id: str, inputs: dict) -> str:
    """触发工作流——把命令加入队列"""
    # 把"运行工作流"封装为命令对象（Celery 任务）
    run_id = run_workflow_task.delay(workflow_id, inputs, current_user.id)
    return str(run_id)
```

**解读**：
- `run_workflow_task` 是一个**命令对象**
- 可以序列化、队列化（Redis）、重试、撤销
- **整体设计**：Celery 把任务封装成命令对象，实现异步、队列化、可重试

### 3.2 ruoyi 的策略模式 + 命令模式

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
**核心代码**：

```java
// Spring Retry 把"重试"封装成命令
@Retryable(value = Exception.class, maxAttempts = 3)
public Object invoke(ProceedingJoinPoint pjp) throws Throwable {
    return pjp.proceed();  // 执行命令
}

// 使用：被注解的方法成为可重试的命令对象
@Service
public class OrderService {
    @Retryable(maxAttempts = 3)
    public void createOrder(OrderDTO dto) {
        // 业务逻辑
        orderMapper.insert(order);
    }
}
```

**解读**：
- `@Retryable` 把方法封装为可重试的命令
- 失败自动重试——命令模式 + AOP
- **整体设计**：把方法调用对象化，支持重试、超时等

## 4. 关键要点总结

- 命令 = 请求对象化
- 4 角色：Command、ConcreteCommand、Invoker、Receiver
- Celery 任务、Spring Retry 都是命令模式
- 适用：撤销/重做、队列化、宏命令
- 与策略区别：策略关注算法切换，命令关注请求封装

## 5. 练习题

### 练习 1：基础
实现一个简单的计算器，支持加、减、乘、除 4 个命令，且支持撤销。

### 练习 2：进阶
阅读 dify 的 `tasks/workflow.py`，分析 Celery 任务的命令模式应用。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/tasks/workflow.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-protection/`
- 《设计模式》第 5 章：命令模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13