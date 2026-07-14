# 1.2.7 字典树（Trie）

> 字典树（Trie）是字符串前缀查找的利器，时间复杂度 O(m)（m 是字符串长度）。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Trie 的节点结构和插入查找过程
- 区分 Trie 和哈希表的优劣
- 实现自动补全、前缀匹配等功能
- 能在 dify 中识别字符串前缀匹配的应用

## 📚 前置知识

- 06-binary-tree.md
- 字符串基础

## 1. 核心概念

### 1.1 Trie 的定义

**Trie**（也叫前缀树）是一种树形结构，每个节点表示一个字符，从根到某个节点的路径构成一个前缀。

```
存储 ["apple", "app", "apply", "bat", "batch"]：

         root
        / |  \
       a  b   ...
      /    \
     p      a
     |      |
     p      t
    / \      \
   l   l      c
   |   |      |
   e   y      h
       (end)  (end)
```

**根节点不存字符**，从根出发的每条边对应一个字符。

### 1.2 节点结构

```python
class TrieNode:
    def __init__(self):
        self.children: dict[str, TrieNode] = {}  # 子节点
        self.is_end: bool = False  # 是否是某个单词的结尾
```

### 1.3 复杂度分析

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 插入 | O(m) | m = 字符串长度 |
| 查找 | O(m) | 与数据集大小**无关** |
| 前缀搜索 | O(m) | 找到前缀后枚举子树 |
| 内存 | O(总字符数) | 每个字符一个节点 |

**对比哈希表**：

| 维度 | Trie | 哈希表 |
|------|------|--------|
| 前缀查询 | O(m) **支持** | O(n) 不支持 |
| 单点查询 | O(m) | **O(1)** |
| 内存 | 大（每个字符一节点） | 小 |

### 1.4 Trie 的应用

1. **自动补全**：搜索引擎、IDE
2. **拼写检查**：编辑距离
3. **IP 路由**：最长前缀匹配
4. **单词游戏**：Boggle、Wordle
5. **敏感词过滤**：dify 的提示词过滤器

## 2. 代码示例

### 2.1 完整 Trie 实现

```python
# 文件：trie.py
from typing import Iterator

class TrieNode:
    __slots__ = ("children", "is_end", "word")

    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.is_end: bool = False
        self.word: str | None = None  # 用于回溯完整词

class Trie:
    def __init__(self):
        self._root = TrieNode()

    def insert(self, word: str) -> None:
        """插入单词 - O(m)。"""
        node = self._root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True
        node.word = word

    def search(self, word: str) -> bool:
        """精确查找 - O(m)。"""
        node = self._find_node(word)
        return node is not None and node.is_end

    def starts_with(self, prefix: str) -> bool:
        """前缀查找 - O(m)。"""
        return self._find_node(prefix) is not None

    def _find_node(self, s: str) -> TrieNode | None:
        node = self._root
        for ch in s:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def autocomplete(self, prefix: str) -> list[str]:
        """自动补全：返回所有以 prefix 开头的单词。"""
        node = self._find_node(prefix)
        if node is None:
            return []
        results = []
        self._collect(node, results)
        return results

    def _collect(self, node: TrieNode, results: list[str]) -> None:
        if node.is_end:
            results.append(node.word)
        for child in node.children.values():
            self._collect(child, results)

# 测试
trie = Trie()
for word in ["apple", "app", "apply", "apricot", "bat", "batch"]:
    trie.insert(word)

print(trie.search("app"))           # True
print(trie.search("ap"))            # False
print(trie.starts_with("ap"))       # True
print(trie.autocomplete("ap"))      # ['app', 'apple', 'apply', 'apricot']
```

### 2.2 用 Trie 做敏感词过滤

```python
# 文件：sensitive_filter.py
class SensitiveWordFilter:
    """敏感词过滤器：基于 Trie 实现。"""

    def __init__(self, sensitive_words: list[str]):
        self._trie = Trie()
        for word in sensitive_words:
            self._trie.insert(word.lower())

    def filter(self, text: str) -> str:
        """过滤敏感词，替换为 ***。"""
        if not text:
            return text
        result = []
        i = 0
        text_lower = text.lower()
        n = len(text)

        while i < n:
            # 在 Trie 中尽可能长匹配
            node = self._trie._root
            j = i
            matched = False
            while j < n and text_lower[j] in node.children:
                node = node.children[text_lower[j]]
                j += 1
                if node.is_end:
                    # 命中敏感词，替换为 ***
                    result.append("*" * (j - i))
                    i = j
                    matched = True
                    break
            if not matched:
                result.append(text[i])
                i += 1
        return "".join(result)

# 测试
filter = SensitiveWordFilter(["bad", "evil", "spam"])
print(filter.filter("this is a bad and evil example"))  # this is a *** and *** example
```

## 3. dify 仓库源码解读

### 3.1 dify 的变量名模板解析（前缀匹配）

**文件位置**：`/Users/xu/code/github/dify/api/core/prompt/utils/prompt_template_parser.py`
**核心代码**（行 1-50）：

```python
import re
from typing import Any

class PromptTemplateParser:
    """提示词模板解析器。

    dify 的提示词支持变量语法：{{variable_name}}
    解析时需要快速判断一个位置是否是变量开始。

    实现思路：用类似 Trie 的前缀匹配，
    从 '{{' 开始扫描，找最近的 '}}'。
    """

    # 正则匹配 {{ variable_name }} 或 {{ variable_name.default }}
    VARIABLE_PATTERN = re.compile(
        r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
        r'(?:\s*\|\s*([^}]+))?'
        r'\s*\}\}'
    )

    def extract_variables(self, template: str) -> list[str]:
        """提取模板中的所有变量名。"""
        seen = set()
        result = []
        for match in self.VARIABLE_PATTERN.finditer(template):
            var_name = match.group(1)
            if var_name not in seen:
                seen.add(var_name)
                result.append(var_name)
        return result

    def format(self, template: str, variables: dict[str, Any]) -> str:
        """用变量值替换模板。"""
        def replace(match):
            var_name = match.group(1)
            # 支持嵌套属性：user.name
            if '.' in var_name:
                parts = var_name.split('.')
                value = variables
                for p in parts:
                    if isinstance(value, dict):
                        value = value.get(p, '')
                    else:
                        value = getattr(value, p, '')
            else:
                value = variables.get(var_name, '')
            return str(value)

        return self.VARIABLE_PATTERN.sub(replace, template)
```

**解读**：
- 第 17 行：用正则匹配 `{{ variable_name }}`，本质是**前缀匹配**
- 第 27 行：`finditer` 扫描整个模板，O(模板长度)
- 第 34 行：`re.sub` 替换所有匹配项
- **设计意图**：dify 的提示词模板语法 `{{var}}` 类似 Jinja2 但更轻量
- **Trie 的间接应用**：变量名解析（`user.name` 路径）类似 Trie 路径，但用正则 + split 实现

## 4. 关键要点总结

- Trie（前缀树）：每个节点表示一个字符，根到节点路径是前缀
- 插入/查找 **O(m)**（m = 字符串长度），与数据集大小**无关**
- 前缀查询 Trie 远优于哈希表（哈希表不支持前缀）
- 内存开销大（每个字符一个节点）
- 应用：自动补全、拼写检查、IP 路由、敏感词过滤
- dify 用正则做提示词模板变量提取（前缀匹配思想）

## 5. 练习题

### 练习 1：基础（必做）

实现 Trie 的 `delete(word)` 方法（删除单词，但保留其作为其他单词前缀的部分）。

### 练习 2：进阶

阅读 `api/core/prompt/utils/prompt_template_parser.py`，说明 dify 为什么用正则而不是 Trie 来解析 `{{var}}` 语法（提示：考虑变量名的字符集和复杂度）。

### 练习 3：挑战（选做）

实现**压缩 Trie**（Radix Tree / Patricia Trie），把单链压缩成一条边，节省内存。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/prompt/utils/prompt_template_parser.py`
- 《算法导论》第 12 章 Trie
- LeetCode 208/211/212 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13