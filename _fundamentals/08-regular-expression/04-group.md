# 1.4 分组与捕获：`(...)` `(?:...)` `(?P<name>...)`

> 分组让正则能"记住"匹配的内容，是正则最强大的特性之一。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 3 种分组语法
- 区分捕获组 vs 非捕获组 vs 命名组
- 使用反向引用
- 在 dify/ruoyi 中应用分组

## 📚 前置知识

- 01-metachar.md
- 03-quantifier.md

## 1. 核心概念

### 1.1 分组语法

| 语法 | 含义 |
|------|------|
| `(...)` | 捕获组（默认） |
| `(?:...)` | 非捕获组 |
| `(?P<name>...)` | 命名组（Python） |
| `(?<name>...)` | 命名组（其他语言） |
| `\1, \2` | 反向引用 |

### 1.2 捕获组 vs 非捕获组

| 类型 | 语法 | 是否占编号 | 性能 |
|------|------|----------|------|
| 捕获组 | `(...)` | ✅ 占 | 较慢 |
| 非捕获组 | `(?:...)` | ❌ 不占 | 较快 |

### 1.3 反向引用

匹配重复出现的字符：
- `\1` 引用第 1 个捕获组
- `\2` 引用第 2 个捕获组
- `(?P=name)` 引用命名组

## 2. 代码示例

### 2.1 基础分组

```python
import re

# 捕获组
m = re.search(r"(\d{4})-(\d{2})-(\d{2})", "Today is 2026-07-13")
print(m.groups())   # ('2026', '07', '13')
print(m.group(1))  # 2026（年）
print(m.group(2))  # 07（月）
print(m.group(3))  # 13（日）

# 非捕获组（不占编号）
m = re.search(r"(?:\d{4})-(\d{2})-(\d{2})", "2026-07-13")
print(m.groups())  # ('07', '13')——只剩 2 个
```

### 2.2 命名组

```python
# 命名组——更易读
m = re.search(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})", "2026-07-13")
print(m.group("year"))   # 2026
print(m.group("month"))  # 07
print(m.groupdict())     # {'year': '2026', 'month': '07', 'day': '13'}
```

### 2.3 反向引用

```python
# 匹配重复的单词（如 "the the"）
pattern = r"\b(\w+)\s+\1\b"
print(re.findall(pattern, "the the cat sat"))   # ['the']

# 匹配成对的 HTML 标签
pattern = r"<(\w+)>.*?</\1>"
print(re.findall(pattern, "<div>content</div>"))   # ['div']

# 命名反向引用
pattern = r"<(?P<tag>\w+)>.*?</(?P=tag)>"
print(re.findall(pattern, "<span>hi</span>"))   # ['span']
```

### 2.4 实战：解析日志

```python
log_line = "2026-07-13 10:30:45 [INFO] User alice logged in"

pattern = r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+\[(?P<level>\w+)\]\s+(?P<message>.*)$"
m = re.match(pattern, log_line)
if m:
    print(m.groupdict())
# {'date': '2026-07-13', 'time': '10:30:45', 'level': 'INFO', 'message': 'User alice logged in'}
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的密码分组校验

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
# (?=...) 是非捕获组的前瞻断言
password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"
```

**解读**：
- `(?=.*[a-zA-Z])` 前瞻：断言后面有字母
- `(?=.*\d)` 前瞻：断言后面有数字
- 不消耗字符（不占捕获组）

### 3.2 ruoyi 的邮箱分组解析

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/`
**核心代码**：

```java
// 邮箱分组
public static final String EMAIL_REGEX = "^([A-Za-z0-9+_.-]+)@([A-Za-z0-9.-]+\\.[A-Za-z]{2,})$";

public static String[] extractEmailParts(String email) {
    Pattern p = Pattern.compile(EMAIL_REGEX);
    Matcher m = p.matcher(email);
    if (m.matches()) {
        return new String[]{m.group(1), m.group(2)};  // [username, domain]
    }
    return null;
}
```

**解读**：
- 第 1 个 `()` 捕获邮箱用户名
- 第 2 个 `()` 捕获域名
- 通过 `group(1)` / `group(2)` 获取

## 4. 关键要点总结

- `(...)` 捕获组，占编号
- `(?:...)` 非捕获组，不占编号（更高效）
- `(?P<name>...)` 命名组（Python）
- `\1` / `(?P=name)` 反向引用
- `(?=...)` 前瞻（不消耗字符）
- dify 用前瞻断言密码强度，ruoyi 用捕获组解析邮箱

## 5. 练习题

### 练习 1：基础
用命名组解析 URL（协议、域名、路径、参数）。

### 练习 2：进阶
用反向引用匹配"砂砂"这类叠词。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13