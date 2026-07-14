# 4.1 Python re 模块

> Python 的 `re` 模块提供完整的正则支持，是后端开发必备工具。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Python `re` 模块的 4 个核心函数
- 区分 `match` / `search` / `findall` / `finditer`
- 使用编译后的正则对象提升性能
- 在 dify 中应用 Python re 模块

## 📚 前置知识

- 01-13 正则基础

## 1. 核心概念

### 1.1 re 模块的 4 个核心函数

| 函数 | 用途 | 返回 |
|------|------|------|
| `re.match(pattern, string)` | 从**开头**匹配 | Match 对象或 None |
| `re.search(pattern, string)` | 找**第一个**匹配 | Match 对象或 None |
| `re.findall(pattern, string)` | 找**所有**匹配 | 列表（无分组时是字符串，有分组时是元组） |
| `re.finditer(pattern, string)` | 找所有匹配（迭代器） | Match 迭代器 |

### 1.2 常用修饰符

| 修饰符 | 含义 |
|--------|------|
| `re.I` | 忽略大小写 |
| `re.M` | 多行模式（`^/$` 匹配每行） |
| `re.S` | `.` 匹配换行 |
| `re.X` | 详细模式（允许注释和空白） |
| `re.A` | ASCII 模式 |

### 1.3 编译正则

```python
pattern = re.compile(r"\d+")  # 编译一次，多次使用
pattern.findall("abc123")     # 多次复用
```

## 2. 代码示例

### 2.1 4 个核心函数对比

```python
import re

text = "Hello 123 World 456"

# match：从开头匹配
m = re.match(r"\w+", text)
print(f"match: {m.group()}")   # "Hello"

# search：找第一个
m = re.search(r"\d+", text)
print(f"search: {m.group()}")  # "123"

# findall：找所有
print(f"findall: {re.findall(r'\d+', text)}")  # ['123', '456']

# finditer：迭代器
for m in re.finditer(r"\d+", text):
    print(f"finditer: {m.group()} at {m.start()}-{m.end()}")
```

### 2.2 替换与分割

```python
# sub：替换
text = "Hello 123 World 456"
result = re.sub(r"\d+", "X", text)
print(result)  # "Hello X World X"

# split：分割
result = re.split(r"\s+", "a  b   c")
print(result)  # ['a', 'b', 'c']
```

### 2.3 命名组与 groupdict

```python
text = "John 30 alice@example.com"

pattern = r"(?P<name>\w+)\s+(?P<age>\d+)\s+(?P<email>[\w.@]+)"
m = re.match(pattern, text)
if m:
    print(m.groupdict())  # {'name': 'John', 'age': '30', 'email': 'alice@example.com'}
    print(m.group("name"))
    print(m["age"])       # 也可以用 [] 访问
```

### 2.4 编译优化

```python
import re

# ❌ 每次都要编译
for text in texts:
    re.search(r"^\d{4}-\d{2}-\d{2}$", text)

# ✅ 预编译（推荐）
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
for text in texts:
    DATE_RE.search(text)  # 复用，性能更好
```

### 2.5 详细模式（re.X）

```python
import re

# 复杂正则的可读写法
pattern = re.compile(r"""
    ^                       # 开头
    (?P<year>\d{4})         # 年
    -(?P<month>\d{2})       # 月
    -(?P<day>\d{2})         # 日
    $                       # 结尾
""", re.X)

m = pattern.match("2026-07-13")
print(m.groupdict())  # {'year': '2026', 'month': '07', 'day': '13'}
```

## 3. dify 仓库源码解读

### 3.1 dify 的密码校验

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
import re

password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"

def valid_password(password):
    """校验密码——单次 re.match"""
    if re.match(password_pattern, password) is not None:
        return password
    raise ValueError("Password must contain letters and numbers...")
```

**解读**：
- 单次校验，无需预编译
- `re.match` 自动从开头匹配

### 3.2 dify 的 URL 提取（re.findall）

**位置**：`/Users/xu/code/github/dify/api/services/`
**核心代码**：

```python
import re

URL_PATTERN = re.compile(r"https?://[\w.-]+(?::\d+)?(?:/[^\s\"'<>]*)?")

def extract_urls(text: str) -> list[str]:
    """提取文本中所有 URL——用预编译 + findall"""
    return URL_PATTERN.findall(text)
```

**解读**：
- 预编译正则（多次复用）
- `findall` 返回所有匹配
- **整体设计**：高效、可维护

### 3.3 dify 的提示词变量提取

**位置**：`/Users/xu/code/github/dify/api/core/prompt/`
**核心代码**：

```python
import re

VARIABLE_RE = re.compile(r"\{\{(.+?)\}\}")

def extract_variables(template: str) -> list[str]:
    """提取提示词模板中的变量"""
    return VARIABLE_RE.findall(template)


def replace_variables(template: str, variables: dict) -> str:
    """替换模板中的变量"""
    def replacer(match):
        var_name = match.group(1).strip()
        return str(variables.get(var_name, match.group(0)))  # 找不到保留原样
    return VARIABLE_RE.sub(replacer, template)
```

**解读**：
- 预编译 `VARIABLE_RE`
- `findall` 提取所有变量名
- `sub` + 自定义函数做替换（找不到时保留原样）

## 4. 关键要点总结

- 4 个核心函数：`match` / `search` / `findall` / `finditer`
- `sub` 替换、`split` 分割
- 复杂场景用 `re.compile` 预编译
- 详细模式 `re.X` 让复杂正则可读
- 命名组 `groupdict()` 返回字典
- dify 用预编译提升性能

## 5. 练习题

### 练习 1：基础
用 Python re 模块提取一段文本中的所有邮箱地址。

### 练习 2：进阶
用 `re.compile` + 命名组实现一个 URL 解析器（协议、域名、路径、参数）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/dify/api/core/prompt/`
- Python re 文档：https://docs.python.org/3/library/re.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13