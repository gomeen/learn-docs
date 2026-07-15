# 1.1 元字符：`.` `*` `+` `?` `^` `$` `|` `[]`

> 元字符是正则表达式的核心，掌握 12 个元字符就能写出 80% 的正则。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 12 个核心元字符
- 理解元字符的转义规则
- 在 Python 中使用正则
- 在 dify/ruoyi 中识别正则表达式

## 📚 前置知识

- Python 字符串基础
- 字符串匹配概念

## 1. 核心概念

### 1.1 元字符分类

| 元字符 | 含义 | 例子 |
|--------|------|------|
| `.` | 任意单字符（除换行） | `a.c` 匹配 abc、aXc |
| `^` | 字符串开头 | `^abc` |
| `$` | 字符串结尾 | `abc$` |
| `*` | 0 个或多个 | `ab*` 匹配 a、ab、abb |
| `+` | 1 个或多个 | `ab+` 匹配 ab、abb（不含 a） |
| `?` | 0 个或 1 个 | `ab?` 匹配 a、ab |
| `\|` | 或 | `a\|b` 匹配 a 或 b |
| `[]` | 字符类（详见 [02-char-class](./02-char-class.md)） | `[abc]` 匹配 a、b、c |
| `()` | 分组捕获（详见 [04-group](./04-group.md)） | `(ab)+` 匹配 ab、abab |
| `{}` | 量词（详见 [03-quantifier](./03-quantifier.md)） | `a{3}` 匹配 aaa |
| `\` | 转义 | `\.` 匹配点 |
| `/` | 分隔符（部分语言） | `/abc/` |

### 1.2 元字符记忆口诀

```
单字符 .
零个多个 *
一个多个 +
可选     ?
开头     ^
结尾     $
或       |
字符类   []
分组捕获 ()
```

### 1.3 转义规则

匹配元字符本身需要转义：
- `\.` 匹配点
- `\*` 匹配星号
- `\\` 匹配反斜杠
- `\$` 匹配美元符

## 2. 代码示例

### 2.1 基础用法

```python
import re

# ^ 开头
print(bool(re.search(r"^Hello", "Hello World")))   # True
print(bool(re.search(r"^Hello", "Say Hello")))    # False

# $ 结尾
print(bool(re.search(r"World$", "Hello World")))   # True

# . 任意字符
print(bool(re.search(r"a.c", "abc")))   # True
print(bool(re.search(r"a.c", "aXc")))   # True
print(bool(re.search(r"a.c", "ac")))    # False

# * + ? 量词
print(bool(re.search(r"ab*", "a")))      # True（0 个 b）
print(bool(re.search(r"ab*", "ab")))     # True（1 个 b）
print(bool(re.search(r"ab+", "a")))      # False（至少 1 个 b）
print(bool(re.search(r"ab?", "a")))      # True（0 或 1 个 b）

# | 或
print(bool(re.search(r"cat|dog", "I have a cat")))  # True
print(bool(re.search(r"cat|dog", "I have a bird"))) # False

# [] 字符类
print(bool(re.search(r"[aeiou]", "Hello")))    # True（匹配 e）
print(bool(re.search(r"[0-9]", "abc123")))     # True（匹配 1）
```

### 2.2 实战案例

```python
# 验证手机号格式（中国）
pattern = r"^1[3-9]\d{9}$"
print(bool(re.match(pattern, "13800138000")))   # True
print(bool(re.match(pattern, "1380013800")))    # False（少一位）

# 提取文件名后缀
pattern = r"^.+\.(txt|pdf|doc)$"
m = re.match(pattern, "report.pdf")
if m:
    print(m.group(1))  # pdf
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的密码校验正则

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**（行 1-15）：

```python
import re

# 密码必须含字母、数字、长度≥8
password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"

def valid_password(password):
    if re.match(password_pattern, password) is not None:
        return password
    raise ValueError("Password must contain letters and numbers...")
```

**解读**：
- `^` 开头，`$` 结尾——精确匹配
- `(?=.*[a-zA-Z])` 断言至少一个字母（前瞻）
- `(?=.*\d)` 断言至少一个数字
- `.{8,}$` 长度至少 8 的任意字符

### 3.2 ruoyi 的邮箱校验

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/ValidationUtils.java`
**核心代码**：

```java
public class ValidationUtils {
    // 邮箱正则
    public static final String EMAIL_REGEX = "^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$";

    public static boolean isEmail(String email) {
        return Pattern.matches(EMAIL_REGEX, email);
    }
}
```

**解读**：
- `^...$` 精确匹配
- `[A-Za-z0-9+_.-]+` 邮箱用户名部分
- `@[A-Za-z0-9.-]+` 域名部分
- `\\.[A-Za-z]{2,}$` 顶级域名（至少 2 字符）

## 4. 关键要点总结

- 12 个核心元字符：`. * + ? ^ $ | [] () {} \`
- 元字符需转义才能匹配字面量
- `^...$` 表示精确匹配（整字符串）
- `?=` 是前瞻断言（更复杂的规则）
- dify/ruoyi 都用正则做参数校验

## 5. 练习题

### 练习 1：基础
写一个正则匹配 IP 地址（简单版：`X.X.X.X`，X 是 1-3 位数字）。

### 练习 2：进阶
阅读 ruoyi 的 `ValidationUtils.java`，分析它的手机号正则。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`
- Python re 模块：https://docs.python.org/3/library/re.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13