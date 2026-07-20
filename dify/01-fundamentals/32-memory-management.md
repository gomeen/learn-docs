# 1.1.25 Python 内存管理与 GC

> 理解 CPython 的内存管理机制：引用计数 + 循环 GC + 小对象池，能识别内存泄漏的常见模式。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释引用计数（reference counting）的工作原理
- 知道循环引用（circular reference）为何需要 GC 兜底
- 用 `sys.getrefcount` / `gc` 模块排查内存问题
- 在 dify 中识别 `__del__` 与资源清理的正确模式

## 📚 前置知识

- Python 基础：变量、对象、可变性
- [GIL](./31-gil.md)
- 操作系统的「栈 vs 堆」基础

## 1. 核心概念

### 1.1 Python 内存管理的三层结构

1. **引用计数**（主要机制）——每个对象维护 `ob_refcnt`，实时增减，归零立即回收
2. **循环 GC**（兜底机制）——定期扫描容器对象，回收循环引用
3. **内存池**（优化机制）——`pymalloc` 管理小块内存（≤ 512 字节），避免频繁调 `malloc/free`

### 1.2 引用计数

每个 Python 对象都有 `ob_refcnt` 字段：

```python
import sys
a = "hello"
print(sys.getrefcount(a))  # 2（a + getrefcount 的临时引用）

b = a
print(sys.getrefcount(a))  # 3

del b
print(sys.getrefcount(a))  # 2
```

> 注意：`sys.getrefcount` 本身会临时让 refcount +1（因为把 a 作为参数传入）。

**增减规则**：
- 对象创建：`refcount = 1`
- 变量赋值 / 容器插入：`+1`
- `del` / 变量重赋值：`-1`
- `refcount == 0`：对象立即被销毁（`__del__` 调用，内存归还内存池）

### 1.3 为什么需要循环 GC

引用计数**无法回收循环引用**：

```python
a = []
b = []
a.append(b)  # b 的 refcount = 2
b.append(a)  # a 的 refcount = 2

del a, b  # 两者 refcount 都是 1，互相引用，永远不会归零
```

循环 GC（garbage collector）会**定期**扫描容器对象（list / dict / class instance），找出循环引用并断开：

```python
import gc
gc.collect()  # 手动触发一次 GC
gc.disable()  # 关闭循环 GC（不推荐）
```

### 1.4 GC 触发时机

循环 GC 在以下情况自动触发：
- 创建新对象时，检查 `gc.get_threshold()` 返回的计数
- 默认阈值 `(700, 10, 10)`：每分配 700 个对象触发一次

```python
import gc
print(gc.get_threshold())  # (700, 10, 10)
print(gc.get_stats())
# [{'collected': 2, 'uncollectable': 0, 'collections': 1}, ...]
```

### 1.5 `__del__` 与 GC

`__del__` 在对象被销毁时调用。**注意**：循环 GC 也能调用 `__del__`，但顺序不确定。

```python
class File:
    def __del__(self):
        print("closing...")

f = File()
del f  # 触发 __del__
```

> `__del__` 不是好的析构函数，建议用 `contextlib` 或显式 `close()`。

### 1.6 `weakref`：弱引用

弱引用**不增加**引用计数，常用于缓存、观察者模式：

```python
import weakref

class Big:
    pass

big = Big()
r = weakref.ref(big)
print(r())  # <Big object>
del big
print(r())  # None（big 已被回收）
```

应用：缓存（key 还在但 value 已 GC → 自动删除）。

## 2. 代码示例

### 2.1 引用计数演示

```python
import sys

x = object()
print(sys.getrefcount(x))  # 2

y = x
print(sys.getrefcount(x))  # 3

lst = [x]
print(sys.getrefcount(x))  # 4（lst 里也引用了）

del y, lst
print(sys.getrefcount(x))  # 2（只剩 x 和 getrefcount 的临时引用）
```

### 2.2 循环引用陷阱

```python
import gc

class Node:
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.children = []

    def __del__(self):
        print(f"del {self.name}")

# 创建循环引用
root = Node("root")
child = Node("child")
root.children.append(child)
child.parent = root

# 即使显式删 root，root 的 refcount 也不会归零（因为 child.parent 还引用）
del root
del child
# 注意：可能不会打印 "del root/del child"

gc.collect()  # 手动触发后才会真正销毁
# 现在打印 del root, del child
```

### 2.3 常见错误：`__del__` 中访问已删除的对象

```python
# ❌ 错误：循环 GC 销毁顺序不确定
class A:
    def __init__(self):
        self.b = None
    def __del__(self):
        # 此时 self.b 可能已被销毁（不可预测）
        print(self.b.name)

# ✅ 正确：用 close() 显式释放，或不用 __del__
```

### 2.4 弱引用缓存

```python
import weakref

class CachedObject:
    pass

cache = weakref.WeakValueDictionary()
obj = CachedObject()
cache['key'] = obj

print(cache['key'])  # CachedObject
del obj
print(cache.get('key'))  # None（自动清理）
```

## 3. 关键要点总结

- Python 用「**引用计数 + 循环 GC + 内存池**」三层管理内存
- 引用计数实时回收（非循环对象）；循环 GC 兜底处理循环引用
- `sys.getrefcount(obj)` 查看引用计数（注意 +1 临时引用）
- `gc.collect()` 手动触发循环 GC；`gc.disable()` 不推荐
- `__del__` 不是好的析构函数，**顺序不可控**——dify 仅把它作为「最后防线」
- `weakref` 不增加引用计数，适合做缓存

---

**文档版本**：v1.0
**最后更新**：2026-07-13
