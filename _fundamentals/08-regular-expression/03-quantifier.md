# 1.3 量词：`*` `+` `?` `{n}` `{n,}` `{n,m}` 贪婪与非贪婪

> 量词控制匹配次数，是正则最强大的特性之一。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 6 种量词
- 区分贪婪 vs 非贪婪
- 在 Python/Java 中使用量词
- 在 dify/ruoyi 中应用量词

## 📚 前置知识

- 01-metachar.md
- 02-char-class.md

## 1. 核心概念

### 1.1 量词语法

| 量词 | 含义 | 例子 |
|------|------|------|
| `*` | 0 个或多个 | `ab*` 匹配 a、ab、abb |
| `+` | 1 个或多个 | `ab+` 匹配 ab、abb（不含 a） |
| `?` | 0 个或 1 个 | `ab?` 匹配 a、ab |
| `{n}` | 恰好 n 个 | `a{3}` 匹配 aaa |
| `{n,}` | 至少 n 个 | `a{2,}` 匹配 aa、aaa |
| `{n,m}` | n 到 m 个 | `a{2,4}` 匹配 aa、aaa、aaaa |

### 1.2 贪婪 vs 非贪婪

| 类型 | 写法 | 行为 |
|------|------|------|
| 贪婪 | `*`、`+`、`?`、`{n,m}` | 尽可能多匹配 |
| 非贪婪 | `*?`、`+?`、`??`、`{n,m}?` | 尽可能少匹配 |

**例子**：
```python
re.findall(r"<.+>", "<a><b>")      # ['<a><b>'] 贪婪
re.findall(r"<.+?>", "<a><b>")     # ['<a>', '<b>'] 非贪婪
```

### 1.3 实战原则

- 默认贪婪，需要精确时用 `?` 改为非贪婪
- 量词后加 `?` 表示非贪婪
- 量词作用于前一个字符或分组

## 2. 代码示例

### 2.1 基础量词

```python
import re

# {n} 恰好
print(re.findall(r"\d{3}", "abc12345"))   # ['123', '45' 凑不到 3 个 → 不匹配]
print(re.findall(r"\d{3}", "abc 123 45")) # ['123']

# {n,} 至少
print(re.findall(r"\d{2,}", "1 12 123 1234"))  # ['12', '123', '1234']

# {n,m} 范围
print(re.findall(r"\d{2,3}", "1 12 123 1234")) # ['12', '123', '123', '234']

# * 0 或多个
print(re.findall(r"ab*", "a ab abb abbb"))  # ['a', 'ab', 'abb', 'abbb']

# + 1 或多个
print(re.findall(r"ab+", "a ab abb abbb"))  # ['ab', 'abb', 'abbb']

# ? 0 或 1 个
print(re.findall(r"ab?", "a ab abb abbb"))  # ['a', 'ab', 'ab', 'ab']
```

### 2.2 贪婪 vs 非贪婪

```python
# HTML 标签提取
html = "<div>hello</div><span>world</span>"

# ❌ 贪婪：匹配整个字符串
print(re.findall(r"<.+>", html))
# ['<div>hello</div><span>world</span>']

# ✅ 非贪婪：匹配每个标签
print(re.findall(r"<.+?>", html))
# ['<div>', '</div>', '<span>', '</span>']

# 提取标签内容（更精确）
print(re.findall(r"<(\w+)>.+?</\1>", html))
# ['div', 'span']
```

### 2.3 实战：提取数字、邮箱

```python
# 提取数字（1 个或多个）
re.findall(r"\d+", "我有 100 元，他有 250 元")  # ['100', '250']

# 邮箱（限定字符范围）
re.findall(r"[\w.]+@[\w.]+", "alice@example.com")
# ['alice@example.com']

# 提取 URL 参数
url = "https://api.example.com/users?id=123&name=alice"
re.findall(r"[\w]+=[\w]+", url)  # ['id=123', 'name=alice']
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的密码长度校验（量词）

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
# 密码必须含字母、数字、长度≥8
password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"
```

**解读**：
- `{8,}` 至少 8 个字符
- `.*` 0 或多个任意字符（贪婪）
- `.{8,}` 任意字符至少 8 个

### 3.2 ruoyi 的手机号正则

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/`
**核心代码**：

```java
// 中国手机号
public static final String MOBILE_REGEX = "^1[3-9]\\d{9}$";
```

**解读**：
- `1` 开头
- `[3-9]` 第二位 3-9
- `\d{9}` 9 位数字
- `^...$` 精确匹配

### 3.3 dify 的 URL 提取

**位置**：`/Users/xu/code/github/dify/api/services/`
**核心代码**：

```python
url_pattern = r"https?://[\w.-]+(?::\d+)?(?:/[\w./?=&-]*)?"
```

**解读**：
- `https?` http 或 https（`s?` 0 或 1 个 s）
- `[\w.-]+` 域名
- `(?::\d+)?` 可选端口（分组 + `?` 表示可选）
- `(?:/[\w./?=&-]*)?` 可选路径（用 `(?:)` 非捕获分组）

## 4. 关键要点总结

- 6 种量词：`*, +, ?, {n}, {n,}, {n,m}`
- 默认贪婪，加 `?` 改为非贪婪
- HTML 解析常用非贪婪 `<.+?>`
- 量词作用于前一个元素（字符或分组）
- dify 用 `{8,}` 密码长度，ruoyi 用 `\d{9}` 手机号

## 5. 练习题

### 练习 1：基础
用 `{n,m}` 量词提取 3-5 位的数字。

### 练习 2：进阶
对比贪婪和非贪婪在 HTML 标签提取中的不同效果。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13