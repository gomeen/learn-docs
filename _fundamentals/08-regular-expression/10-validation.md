# 3.1 邮箱 / 手机号 / URL 校验

> 实际开发中 80% 的正则用于数据校验，本文总结最常用的校验场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 写出邮箱、手机号、URL 的校验正则
- 理解每种正则的局限性
- 在 dify/ruoyi 中应用校验
- 知道何时用专门的验证库

## 📚 前置知识

- 01-05 元字符和量词
- 04-group.md

## 1. 核心概念

### 1.1 邮箱校验的难点

RFC 5321 允许的邮箱字符非常复杂：
- 用户名：字母、数字、`.`、`_`、`+`、`-` 等
- 域名：多级域名、`-` 等
- 顶级域名：2-6 字符（`.cn`、`.com`、`.museum`）

**实用建议**：用宽松的校验，不要追求 RFC 完全合规。

### 1.2 中国手机号规则

- 11 位数字
- 开头：`1[3-9]`
- 第二位：3-9（覆盖所有运营商号段）

### 1.3 URL 校验

URL 结构复杂，包含协议、域名、端口、路径、参数、片段等。

## 2. 代码示例

### 2.1 邮箱校验

```python
import re

# 实用版（推荐）
EMAIL_RE = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

emails = ["alice@example.com", "bob@test.org", "invalid@", "@bad.com", "no-at-sign"]
for email in emails:
    print(f"{email}: {bool(re.match(EMAIL_RE, email))}")
# alice@example.com: True
# bob@test.org: True
# invalid@: False
# @bad.com: False
# no-at-sign: False
```

### 2.2 中国手机号校验

```python
MOBILE_RE = r"^1[3-9]\d{9}$"

mobiles = ["13800138000", "12345678901", "20012345678", "1380013800"]
for m in mobiles:
    print(f"{m}: {bool(re.match(MOBILE_RE, m))}")
# 13800138000: True
# 12345678901: False（第二位 2 不对）
# 20012345678: False（第二位 0 不对）
# 1380013800: False（少一位）
```

### 2.3 URL 校验

```python
URL_RE = r"^https?://[\w.-]+(?::\d+)?(?:/[^\s]*)?$"

urls = [
    "https://example.com",
    "http://api.example.com:8080/users",
    "https://example.com/path?q=1&p=2",
    "ftp://files.example.com",
    "not a url",
]
for url in urls:
    print(f"{url}: {bool(re.match(URL_RE, url))}")
# https://example.com: True
# http://api.example.com:8080/users: True
# https://example.com/path?q=1&p=2: True
# ftp://files.example.com: False
# not a url: False
```

### 2.4 提取而非校验

```python
# 从文本中提取邮箱
text = "联系我们: info@example.com 或 support@test.org"
emails = re.findall(r"[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}", text)
print(emails)  # ['info@example.com', 'support@test.org']

# 提取 URL
text = "访问 https://example.com 或 http://test.org 了解详情"
urls = re.findall(r"https?://[\w./?=&-]+", text)
print(urls)  # ['https://example.com', 'http://test.org']
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的密码和邮箱校验

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
import re

# 密码：必须含字母数字，长度≥8
password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"
```

**解读**：
- 前瞻断言确保密码强度
- **dify 中无直接邮箱校验示例**——通常依赖框架

### 3.2 ruoyi 的全方位校验

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/ValidationUtils.java`
**核心代码**：

```java
public class ValidationUtils {
    // 邮箱
    public static final String EMAIL_REGEX = "^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$";

    // 手机号
    public static final String MOBILE_REGEX = "^1[3-9]\\d{9}$";

    // 身份证 18 位
    public static final String ID_CARD_REGEX = "^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]$";

    // URL
    public static final String URL_REGEX = "^https?://[\\w.-]+(?::\\d+)?(?:/[\\w./?=&%-]*)?$";

    // 中文
    public static final String CHINESE_REGEX = "^[\\u4e00-\\u9fa5]+$";

    // 银行卡（16-19 位数字）
    public static final String BANK_CARD_REGEX = "^\\d{16,19}$";

    public static boolean isEmail(String s) { return s.matches(EMAIL_REGEX); }
    public static boolean isMobile(String s) { return s.matches(MOBILE_REGEX); }
    public static boolean isIdCard(String s) { return s.matches(ID_CARD_REGEX); }
    public static boolean isUrl(String s) { return s.matches(URL_REGEX); }
}
```

**解读**：
- ruoyi 提供完整的中文场景校验工具
- 覆盖邮箱、手机、身份证、银行卡、URL
- **整体设计**：标准化的工具类

### 3.3 dify 的 URL 提取

**位置**：`/Users/xu/code/github/dify/api/services/`
**核心代码**：

```python
import re

# 从 LLM 输出中提取 URL
def extract_urls(text: str) -> list[str]:
    """提取文本中所有 URL"""
    pattern = r"https?://[\w.-]+(?::\d+)?(?:/[^\s\"'<>]*)?"
    return re.findall(pattern, text)
```

**解读**：
- 简单但实用的 URL 提取正则
- 排除常见的 URL 终止字符

## 4. 关键要点总结

- 邮箱校验用宽松版（不追求 RFC 完整）
- 中国手机号：`^1[3-9]\d{9}$`
- URL 校验要支持端口、路径、参数
- 优先用专门的验证库（如 email-validator）
- ruoyi 提供全套中文场景校验工具

## 5. 练习题

### 练习 1：基础
实现一个函数 `validate_user_input(data)` 同时校验邮箱、手机号、URL。

### 练习 2：进阶
写一个提取 markdown 中所有链接的正则（支持 `[text](url)` 格式）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13