# 0.4 Python 模块、包与导入

> 理解模块与包的组织方式，能看懂 dify 后端的目录结构与 import 语句。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解模块（.py 文件）与包（带 `__init__.py` 的目录）的关系
- 掌握 4 种 import 方式与各自的适用场景
- 理解相对导入与绝对导入
- 能看懂 dify 的 `api/` 目录结构

## 📚 前置知识

- [00-python-variables-and-types.md](./01-python-variables-and-types.md)

## 1. 核心概念

### 1.1 模块：单个 .py 文件

```python
# 文件：mymodule.py
def greet(name):
    return f"Hello, {name}"

PI = 3.14
```

```python
# 另一个文件
import mymodule          # 导入整个模块
print(mymodule.greet("Alice"))
print(mymodule.PI)
```

### 1.2 包：带 `__init__.py` 的目录

```
mypackage/
├── __init__.py        # 可以为空，也可以定义 __all__
├── module_a.py
├── module_b.py
└── subpackage/
    ├── __init__.py
    └── module_c.py
```

```python
# 导入子模块
from mypackage import module_a
from mypackage.subpackage import module_c
```

### 1.3 四种 import 方式

```python
# 1. import 模块
import os
os.path.join("a", "b")  # 必须用全名

# 2. import 模块 + as 别名
import numpy as np
np.array([1, 2, 3])

# 3. from 模块 import 名字
from os import path
path.join("a", "b")     # 直接用 path

# 4. from 模块 import *
from os import *        # 导入所有公开名字（不推荐）
```

### 1.4 相对导入 vs 绝对导入

```python
# 在 mypackage/subpackage/module_c.py 中：

# 绝对导入（推荐）
from mypackage.module_a import foo
from mypackage.subpackage import module_d

# 相对导入（用 . 表示当前包）
from ..module_a import foo          # .. 表示父包
from . import module_d              # . 表示当前包
from ..subpackage import module_c   # 上一级包的 subpackage
```

**PEP 8 推荐**：项目内用**绝对导入**，跨项目的第三方库用 `import 库名`。

### 1.5 入口文件：`if __name__ == "__main__"`

```python
# 文件：script.py
def main():
    print("执行主逻辑")

if __name__ == "__main__":
    main()
```

- 直接运行 `python script.py` 时，`__name__` 是 `"__main__`，会执行 `main()`
- 被 `import script` 时，`__name__` 是 `"script"`，**不会**执行 `main()`
- **作用**：让模块既能被导入使用，也能独立运行

## 2. 代码示例

### 2.1 `__all__` 控制 `import *`

```python
# 文件：mymodule.py
__all__ = ["public_func", "PublicClass"]  # 只导出这些

def public_func():
    pass

def _private_func():  # 以下划线开头，约定不导出
    pass

class PublicClass:
    pass

class _PrivateClass:
    pass
```

```python
# 使用
from mymodule import *  # 只会导入 public_func 和 PublicClass
```

### 2.2 循环导入问题

```python
# ❌ 错误：循环导入
# file_a.py
from file_b import func_b  # 报错！

def func_a():
    pass

# file_b.py
from file_a import func_a  # 报错！

def func_b():
    pass
```

**解决方案**：

```python
# ✅ 方案 1：延迟导入（在函数内部 import）
# file_a.py
def func_a():
    from file_b import func_b  # 在调用时才导入
    func_b()

# ✅ 方案 2：抽出公共模块
# common.py 定义共享内容，a 和 b 都从 common 导入
```

### 2.3 `sys.path` 与模块搜索路径

```python
import sys
print(sys.path)
# 输出类似：
# ['/current/dir', '/usr/lib/python3.11', '/site-packages', ...]

# Python 按 sys.path 顺序查找模块
# 第一个找到的胜出
```

## 3. 关键要点总结

- **模块** = 单个 `.py` 文件；**包** = 含 `__init__.py` 的目录
- `import x` 导入模块；`from x import y` 导入名字
- 项目内推荐**绝对导入**；跨包用相对导入（`from . import xxx`）
- 循环导入用**延迟导入**（函数内 import）解决
- `if __name__ == "__main__"` 让模块可独立运行
- dify 风格：标准库 → 第三方 → 项目内（每组空行分隔）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
