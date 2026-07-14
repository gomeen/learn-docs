# 2.1 反向引用与回溯

> 反向引用让正则"记住"之前匹配的内容，回溯是正则引擎的核心机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握反向引用的语法和用法
- 理解正则的回溯机制
- 知道如何避免灾难性回溯
- 在 dify/ruoyi 中应用

## 📚 前置知识

- 04-group.md
- 05-anchor.md

## 1. 核心概念

### 1.1 反向引用

| 语法 | 含义 |
|------|------|
| `\1`, `\2` | 引用第 1、2 个捕获组 |
| `(?P=name)` | 引用命名组（Python） |
| `\k<name>` | 引用命名组（其他语言） |

### 1.2 回溯（Backtracking）

正则引擎的核心机制：
- 尝试匹配失败时，回到上一步换其他路径
- 嵌套量词 + 模糊匹配 = 可能大量回溯
- 可能导致**灾难性回溯**（CPU 飙升）

### 1.3 灾难性回溯

```python
import re

# ❌ 灾难性回溯
pattern = r"^(a+)+$"
re.match(pattern, "aaaaaaaaaaaaaaaaaab")  # CPU 飙升！
```

## 2. 代码示例

### 2.1 反向引用

```python
import re

# 匹配成对标签
pattern = r"<(\w+)>.*?</\1>"
print(re.findall(pattern, "<div>hi</div><span>ok</span>"))
# ['div', 'span']

# 命名反向引用
pattern = r"<(?P<tag>\w+)>.*?</(?P=tag)>"
print(re.findall(pattern, "<a>link</a>"))
# ['a']

# 检测重复单词
pattern = r"\b(\w+)\s+\1\b"
print(re.findall(pattern, "the the cat"))
# ['the']

# 匹配日期（分隔符一致）
pattern = r"(\d{4})([-/.])(\d{2})\2(\d{2})"
print(re.match(pattern, "2026-07-13").groups())  # ('2026', '-', '07', '13')
print(re.match(pattern, "2026/07/13").groups())  # ('2026', '/', '07', '13')
```

### 2.2 回溯演示

```python
import re
import time

# 简单正则 + 短字符串：快速
start = time.time()
re.search(r"^a+b", "aaaaab")
print(f"Simple: {(time.time() - start) * 1000:.2f}ms")  # < 1ms

# 灾难性回溯 + 长字符串：极慢
start = time.time()
try:
    re.search(r"^(a+)+b", "a" * 25 + "c")  # 故意不匹配
except Exception as e:
    print(f"Error: {e}")
# 可能 1-30 秒（CPU 占用 100%）
```

### 2.3 避免灾难性回溯

```python
# ❌ 反例：嵌套量词
pattern = r"^(a+)+$"

# ✅ 正例：消除嵌套
pattern = r"^a+$"

# ❌ 反例：贪婪 + 模糊
pattern = r"a.*b.*c"

# ✅ 正例：使用更具体的字符类
pattern = r"a[^b]*b[^c]*c"
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify/ruoyi 中的反向引用

**示例**：校验成对的 XML/HTML 标签

```python
# dify/ruoyi 都可能用反向引用校验标签平衡
import re

def validate_balanced_tags(html: str) -> bool:
    """校验标签是否平衡"""
    pattern = r"<(\w+)(?:\s+[^>]*)?>(?:[^<]|<(?!/\1>))*?</\1>"
    return bool(re.fullmatch(pattern, html))
```

**解读**：
- `<(\w+)>` 捕获开标签名
- `(?!/\1>)` 负向前瞻：确保不立即遇到同标签的关闭
- `</\1>` 反向引用：必须匹配相同标签名

### 3.2 dify/ruoyi 中无直接示例

**说明**：灾难性回溯的反面案例，dify/ruoyi 中较少直接展示。但开发者写复杂正则时需注意。

## 4. 关键要点总结

- 反向引用 `\1` / `(?P=name)` 引用之前的捕获
- 回溯 = 失败后换路径尝试
- 嵌套量词 + 模糊匹配 = 灾难性回溯
- 避免：消除嵌套、具体化字符类、避免贪婪 + 模糊

## 5. 练习题

### 练习 1：基础
写一个正则匹配成对的 `<tag>...</tag>`（如 `<div>...</div>`）。

### 练习 2：进阶
构造一个灾难性回溯的例子，并分析如何优化。

## 6. 参考资料

- Python re：https://docs.python.org/3/library/re.html
- 《精通正则表达式》第 5 章：回溯

---

**文档版本**：v1.0
**最后更新**：2026-07-13