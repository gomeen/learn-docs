# 1.2 字符类：`[abc]` `[^abc]` `[a-z]` `\\d` `\\w` `\\s`

> 字符类用于匹配单个字符的"集合"，是正则的基础构件。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握字符类的 4 种语法
- 区分预定义字符类（`\d`、`\w`、`\s`）
- 理解 `^` 在字符类中的含义（否定）
- 在 dify/ruoyi 中应用字符类

## 📚 前置知识

- 01-metachar.md

## 1. 核心概念

### 1.1 字符类语法

| 语法 | 含义 | 等价 |
|------|------|------|
| `[abc]` | a 或 b 或 c | - |
| `[^abc]` | 非 a/b/c 的字符 | 否定 |
| `[a-z]` | a 到 z 的小写字母 | 范围 |
| `[a-zA-Z0-9]` | 所有字母数字 | 多范围 |
| `[a-z-]` | a-z 加连字符（用 - 在末尾） | - |

### 1.2 预定义字符类（简写）

| 简写 | 等价 | 含义 |
|------|------|------|
| `\d` | `[0-9]` | 数字 |
| `\D` | `[^0-9]` | 非数字 |
| `\w` | `[a-zA-Z0-9_]` | 单词字符 |
| `\W` | `[^a-zA-Z0-9_]` | 非单词字符 |
| `\s` | `[ \t\n\r\f\v]` | 空白字符 |
| `\S` | `[^ \t\n\r\f\v]` | 非空白字符 |

### 1.3 Python 中的转义

Python 字符串中 `\d` 需要写成 `\\d`（双反斜杠）或用 raw string `r"\d"`。

```python
# 普通字符串
pattern = "\\d+"          # 等价于 \d+
# Raw string（推荐）
pattern = r"\d+"          # 直接写 \d+
```

## 2. 代码示例

### 2.1 基础字符类

```python
import re

# [abc] 字符类
print(re.findall(r"[abc]", "abcdef"))      # ['a', 'b', 'c']
print(re.findall(r"[^abc]", "abcdef"))     # ['d', 'e', 'f']

# [a-z] 范围
print(re.findall(r"[a-z]", "Hello123"))    # ['e', 'l', 'l', 'o']
print(re.findall(r"[A-Z]", "Hello123"))    # ['H']
print(re.findall(r"[a-zA-Z]", "Hello123")) # ['H', 'e', 'l', 'l', 'o']

# [0-9] 数字
print(re.findall(r"[0-9]", "abc123"))      # ['1', '2', '3']
```

### 2.2 预定义字符类

```python
# \d 数字
print(re.findall(r"\d+", "我有 100 元"))    # ['100']

# \w 单词字符（字母+数字+下划线）
print(re.findall(r"\w+", "hello_world 123"))  # ['hello_world', '123']

# \s 空白字符
print(re.split(r"\s+", "a  b   c"))       # ['a', 'b', 'c']

# 大写表示否定
print(re.findall(r"\D+", "abc123"))      # ['abc']
print(re.findall(r"\W+", "hello, world")) # [', ', ' '] 不算 \w
```

### 2.3 实战案例

```python
# 提取所有数字
text = "订单 123456 价格 99.99 元"
numbers = re.findall(r"\d+\.?\d*", text)
print(numbers)  # ['123456', '99.99']

# 验证是否只含字母数字
print(bool(re.match(r"^[a-zA-Z0-9]+$", "abc123")))   # True
print(bool(re.match(r"^[a-zA-Z0-9]+$", "abc-123")))  # False

# 提取邮箱用户名
emails = "alice@example.com, bob@test.org"
usernames = re.findall(r"([a-zA-Z0-9._]+)@", emails)
print(usernames)  # ['alice', 'bob']
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的密码字符类

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
# 密码必须含字母、数字、长度≥8
password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"
```

**解读**：
- `[a-zA-Z]` 字符类：所有字母
- `\d` 等价于 `[0-9]`：所有数字
- 组合 `(?=.*[a-zA-Z])` 前瞻断言：至少 1 个字母

### 3.2 ruoyi 的身份证校验

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/`
**核心代码**：

```java
// 身份证 18 位（前 17 位数字 + 最后 1 位数字或 X）
public static final String ID_CARD_REGEX = "^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]$";
```

**解读**：
- `[1-9]` 第 1 位 1-9（不能 0 开头）
- `\d{5}` 接下来 5 位数字
- `(18|19|20)` 年份范围
- `(0[1-9]|1[0-2])` 月份（01-12）
- `(0[1-9]|[12]\d|3[01])` 日期
- `\d{3}` 顺序码
- `[\dXx]` 校验位（数字或 X）

## 4. 关键要点总结

- `[abc]` 单字符集合
- `[^abc]` 否定（字符类中）
- `[a-z]` 范围
- `\d \w \s` 预定义字符类
- Python 用 raw string `r"\d+"` 避免双重转义
- 身份证正则用组合字符类实现精确校验

## 5. 练习题

### 练习 1：基础
提取一段文本中的所有数字（含小数）。

### 练习 2：进阶
为 16 位银行卡号写校验正则（前缀规则可参考实际银行卡号段）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13