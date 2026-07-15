# 2.3 贪婪 vs 非贪婪匹配

> 贪婪 vs 非贪婪是新手最常踩的坑。理解差异能避免大量 bug。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分贪婪与非贪婪
- 知道何时用非贪婪
- 避免常见的贪婪陷阱
- 在 dify/ruoyi 中应用

## 📚 前置知识

- 03-quantifier.md
- 04-group.md

## 1. 核心概念

### 1.1 贪婪 vs 非贪婪

| 维度 | 贪婪 | 非贪婪 |
|------|------|--------|
| 写法 | `*` `+` `?` `{n,m}`（[量词](./03-quantifier.md)） | `*?` `+?` `??` `{n,m}?` |
| 行为 | 尽可能多匹配 | 尽可能少匹配 |
| 回溯 | 较多（引擎见 [09-engine](./09-engine.md)） | 较少（但要看场景） |

### 1.2 何时用非贪婪

- 提取成对的标签（HTML/XML）
- 提取括号内的内容
- 提取引号内的字符串

### 1.3 何时用贪婪

- 默认行为（多数场景够用）
- 提取最大块（如整个段落）

## 2. 代码示例

### 2.1 经典对比

```python
import re

text = "<div>hello</div><span>world</span>"

# 贪婪：<.+>
print(re.findall(r"<.+>", text))
# ['<div>hello</div><span>world</span>']  ← 整串匹配

# 非贪婪：<.+?>
print(re.findall(r"<.+?>", text))
# ['<div>', '</div>', '<span>', '</span>']  ← 每个标签单独
```

### 2.2 提取括号内容

```python
text = "(apple)(banana)(cherry)"

# 贪婪
print(re.findall(r"\(.+\)", text))
# ['(apple)(banana)(cherry)']  ← 整串

# 非贪婪
print(re.findall(r"\(.+?\)", text))
# ['(apple)', '(banana)', '(cherry)']  ← 每个
```

### 2.3 实战案例

```python
# 提取 markdown 链接
md_text = "看 [Dify](https://dify.ai) 和 [Python](https://python.org)"

# ❌ 贪婪：会跨链接
print(re.findall(r"\[.+?\]\(.+?\)", md_text))
# ['[Dify](https://dify.ai)', '[Python](https://python.org)']

# ✅ 用非贪婪即可
```

### 2.4 性能考虑

```python
import time

# ❌ 贪婪 + 模糊匹配（慢）
start = time.time()
for _ in range(1000):
    re.search(r"^.*\d+$", "abc" + "x" * 30 + "123")
greedy_time = time.time() - start

# ✅ 非贪婪（更快）
start = time.time()
for _ in range(1000):
    re.search(r"^.*?\d+$", "abc" + "x" * 30 + "123")
lazy_time = time.time() - start

print(f"Greedy: {greedy_time:.2f}s, Lazy: {lazy_time:.2f}s")
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的提示词模板提取（非贪婪）

**位置**：`/Users/xu/code/github/dify/api/core/prompt/`
**核心代码**：

```python
import re

# 提取提示词中的变量 {{name}}
def extract_variables(template: str) -> list[str]:
    """从模板提取所有变量名——用非贪婪避免跨变量"""
    pattern = r"\{\{(.+?)\}\}"
    return re.findall(pattern, template)


# 测试
tmpl = "Hello {{name}}, your code is {{code}}"
print(extract_variables(tmpl))  # ['name', 'code']
```

**解读**：
- `\{\{...\}\}` 提取变量内容
- `.+?` 非贪婪，避免跨越多个变量

### 3.2 ruoyi 的 HTML 清理（非贪婪）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`
**核心代码**：

```java
// 提取 HTML 标签内容（非贪婪）
public static final Pattern HTML_TAG_PATTERN = Pattern.compile("<[^>]+>");
// ❌ 贪婪：<.+> 会匹配整段 HTML
// ✅ 非贪婪：<[^>]+> 只匹配单个标签
```

**解读**：
- `[^>]+` 匹配非 `>` 的字符——天然非贪婪（因为遇到 `>` 就停）
- 比 `<.+?>` 更高效

## 4. 关键要点总结

- 贪婪默认多匹配，加 `?` 改非贪婪
- HTML/XML 解析必须用非贪婪
- 括号、引号配对提取用非贪婪
- dify 提示词变量提取用 `.+?`
- ruoyi HTML 清理用 `[^>]+`

## 5. 练习题

### 练习 1：基础
提取 markdown 文本中的所有链接 `[text](url)`。

### 练习 2：进阶
解释为什么 `<.+?>` 比 `<[^>]+>` 慢。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/prompt/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13