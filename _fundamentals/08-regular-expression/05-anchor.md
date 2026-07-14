# 1.5 锚点：`^` `$` `\\b` `\\B` 零宽断言

> 锚点匹配"位置"而不是字符，是正则的精妙之处。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 4 种锚点（`^`、`$`、`\b`、`\B`）
- 区分单词边界与非单词边界
- 理解零宽断言的本质
- 在 dify/ruoyi 中应用锚点

## 📚 前置知识

- 01-metachar.md
- 04-group.md

## 1. 核心概念

### 1.1 锚点分类

| 锚点 | 含义 | 匹配内容 |
|------|------|---------|
| `^` | 字符串开头 | 位置 |
| `$` | 字符串结尾 | 位置 |
| `\b` | 单词边界 | 位置 |
| `\B` | 非单词边界 | 位置 |

### 1.2 单词边界 `\b`

```
"hello" → \b 在开头（h 前）和结尾（o 后）
"hello world" → 5 个 \b（h 前、o 后、w 前、d 后、字符串两端）
```

**判断条件**：一边是 `\w`，另一边不是 `\w`（或字符串边界）。

### 1.3 零宽断言

零宽 = 不消耗字符，只检查位置：

| 语法 | 名称 | 含义 |
|------|------|------|
| `(?=...)` | 前瞻肯定 | 后面是... |
| `(?!...)` | 前瞻否定 | 后面不是... |
| `(?<=...)` | 后顾肯定 | 前面是... |
| `(?<!...)` | 后顾否定 | 前面不是... |

## 2. 代码示例

### 2.1 基础锚点

```python
import re

# ^ 开头
print(bool(re.search(r"^Hello", "Hello World")))  # True
print(bool(re.search(r"^Hello", "Say Hello")))    # False

# $ 结尾
print(bool(re.search(r"World$", "Hello World")))  # True
print(bool(re.search(r"World$", "World!")))       # False（! 不匹配 W）

# 多行模式 ^/$ 匹配每行
text = "Line 1\nLine 2\nLine 3"
print(re.findall(r"^Line \d$", text))            # [] （多行模式下）
print(re.findall(r"^Line \d$", text, re.M))       # ['Line 1', 'Line 2', 'Line 3']
```

### 2.2 单词边界

```python
# \b 单词边界
print(re.findall(r"\bcat\b", "cat scatter catalog"))  # ['cat']——scatter、catalog 不算
print(re.findall(r"cat", "cat scatter catalog"))     # ['cat', 'cat', 'cat']——全部

# 精确匹配整词
print(bool(re.search(r"\b\d+\b", "abc123")))         # True（123 是单词）
print(bool(re.search(r"\b\d+\b", "abc123xyz")))      # False（123xyz 不是单词）

# \B 非单词边界
print(re.findall(r"\Bcat\B", "scattered"))           # ['cat']
```

### 2.3 零宽断言

```python
# 前瞻肯定 (?=...)
print(re.findall(r"\w+(?=\s)", "hello world foo"))   # ['hello', 'world']——后面有空格

# 前瞻否定 (?!...)
print(re.findall(r"\d+(?!\d)", "abc123 def45 6"))    # ['23', '5', '6']——后面没数字

# 后顾肯定 (?<=...)
print(re.findall(r"(?<=\$)\d+", "$100 and ¥200"))    # ['100']——前面是 $

# 后顾否定 (?<!...)
print(re.findall(r"(?<!\$)\d+", "$100 and 200"))     # ['100', '200']——前面不是 $
```

### 2.4 实战：强密码校验

```python
# 强密码：8+ 位，必须含大小写、数字、特殊字符
strong_pwd = r"""
^
(?=.*[a-z])      # 至少 1 个小写
(?=.*[A-Z])      # 至少 1 个大写
(?=.*\d)         # 至少 1 个数字
(?=.*[!@#$%^&*]) # 至少 1 个特殊字符
[A-Za-z\d!@#$%^&*]{8,}
$
"""

print(bool(re.match(strong_pwd, "Hello123!"), re.X))   # True
print(bool(re.match(strong_pwd, "hello123"), re.X))    # False（无大写无特殊）
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的精确密码匹配（^...$）

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"
```

**解读**：
- `^...$` 锚定整字符串
- `(?=.*[a-zA-Z])` 前瞻：含字母
- `(?=.*\d)` 前瞻：含数字

### 3.2 ruoyi 的身份证严格匹配

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/`
**核心代码**：

```java
// 身份证（18 位，严格匹配）
public static final String ID_CARD_REGEX = "^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]$";
```

**解读**：
- `^` 开头
- `$` 结尾
- `(18|19|20)` 分组：年份限定范围

### 3.3 dify 的精确格式校验

**位置**：`/Users/xu/code/github/dify/api/services/`
**核心代码**：

```python
import re

# 提取用户邮箱中的域名（用前瞻）
def extract_email_domain(email: str) -> str | None:
    pattern = r"^[\w.+-]+@(?P<domain>[\w.-]+\.[a-zA-Z]{2,})$"
    m = re.match(pattern, email)
    return m.group("domain") if m else None

print(extract_email_domain("alice@example.com"))  # example.com
```

**解读**：
- `^[\w.+-]+@` 邮箱用户名 + @
- `(?P<domain>...)` 命名组捕获域名
- `$` 结尾

## 4. 关键要点总结

- `^` 开头，`$` 结尾，`\b` 单词边界
- 零宽断言 = 不消耗字符，只检查位置
- 前瞻 `(?=...)` / `(?!...)`，后顾 `(?<=...)` / `(?<!...)`
- 多行模式 `re.M` 让 `^/$` 匹配每行
- dify 用 `^...$` + 前瞻，ruoyi 用 `^...$` 严格校验

## 5. 练习题

### 练习 1：基础
提取一段文本中的所有整词数字（如 "123" 算，"abc123def" 不算）。

### 练习 2：进阶
写一个强密码正则：必须含大小写、数字、特殊字符，长度 8+。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13