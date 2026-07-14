# 2.2 零宽断言：lookahead / lookbehind

> 零宽断言（Zero-Width Assertions）匹配"位置"而不是字符，是正则的高级特性。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 4 种零宽断言（2 瞻 + 2 顾）
- 区分前瞻与后顾
- 在复杂校验中应用零宽断言
- 在 dify/ruoyi 中识别应用

## 📚 前置知识

- 05-anchor.md
- 04-group.md

## 1. 核心概念

### 1.1 4 种零宽断言

| 语法 | 名称 | 含义 | 方向 |
|------|------|------|------|
| `(?=...)` | 前瞻肯定 | 后面是... | 前 |
| `(?!...)` | 前瞻否定 | 后面不是... | 前 |
| `(?<=...)` | 后顾肯定 | 前面是... | 后 |
| `(?<!...)` | 后顾否定 | 前面不是... | 后 |

### 1.2 前瞻 vs 后顾

```
前瞻 (?=...)   ：站在当前位置，向前看
后顾 (?<=...)  ：站在当前位置，向后看
```

### 1.3 零宽的意义

零宽 = 不消耗字符：
- `(?=\d)\d` 第一个 `\d` 是断言（不消耗），第二个 `\d` 实际匹配
- 与捕获组的区别：捕获组会消耗字符

## 2. 代码示例

### 2.1 前瞻

```python
import re

# 前瞻肯定 (?=...)
# 提取后面跟空格的单词
print(re.findall(r"\w+(?=\s)", "hello world foo"))
# ['hello', 'world']

# 前瞻否定 (?!...)
# 提取不是以 ing 结尾的单词
print(re.findall(r"\b\w+(?!ing\b)\b", "running jumping cat"))
# ['cat']
```

### 2.2 后顾

```python
# 后顾肯定 (?<=...)
# 提取 $ 后面的数字（金额）
print(re.findall(r"(?<=\$)\d+", "$100 and ¥200"))
# ['100']

# 后顾否定 (?<!...)
# 提取不在 $ 后面的数字
print(re.findall(r"(?<!\$)\d+", "$100 and 200"))
# ['100', '200']
```

### 2.3 实战：复杂密码校验

```python
# 强密码：8+ 位，必须含大小写、数字
strong_pwd = r"""
^
(?=.*[a-z])       # 前瞻：含小写
(?=.*[A-Z])       # 前瞻：含大写
(?=.*\d)          # 前瞻：含数字
(?=.*[!@#$%])     # 前瞻：含特殊字符
[A-Za-z\d!@#$%]{8,}  # 实际匹配
$
"""

print(bool(re.match(strong_pwd, "Hello123!", re.X)))   # True
print(bool(re.match(strong_pwd, "hello123", re.X)))    # False
```

### 2.4 提取 URL 协议和域名

```python
url = "https://api.example.com/users"

# 提取协议（不带 ://）
print(re.findall(r"^\w+(?=://)", url))   # ['https']

# 提取域名
print(re.findall(r"(?<=://)[\w.-]+", url))   # ['api.example.com']
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的强密码校验（前瞻）

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"
```

**解读**：
- `(?=.*[a-zA-Z])` 前瞻：断言后面有字母
- `(?=.*\d)` 前瞻：断言后面有数字
- **整体效果**：密码必须含字母和数字，但不实际"消耗"这两个字符

### 3.2 ruoyi 的业务校验（前瞻/后顾）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/`
**核心代码**：

```java
// 例如：提取中文字符
public static final Pattern CHINESE_PATTERN = Pattern.compile("[\\u4e00-\\u9fa5]+");

// 提取人民币金额
public static final Pattern RMB_AMOUNT_PATTERN = Pattern.compile("(?<=￥)\\d+(\\.\\d{1,2})?");
```

**解读**：
- 后顾肯定 `(?<=￥)` 匹配￥后面的金额
- 不消耗 ￥ 字符

## 4. 关键要点总结

- 4 种零宽断言：前/后顾 × 肯定/否定
- 零宽 = 不消耗字符，只检查位置
- dify 用前瞻做密码校验
- 强密码正则 = 多个前瞻 + 实际匹配

## 5. 练习题

### 练习 1：基础
写一个正则匹配价格：必须是 `$` 或 `￥` 开头的数字。

### 练习 2：进阶
写一个强密码校验正则（必须含大写、小写、数字、特殊字符）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13