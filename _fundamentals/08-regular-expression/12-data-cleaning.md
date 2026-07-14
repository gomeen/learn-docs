# 3.3 数据清洗：CSV / 文本

> 数据清洗是正则的实战应用，处理 CSV、TXT、日志中的脏数据。

## 🎯 学习目标

完成本文档后，你将能够：
- 用正则清洗常见脏数据
- 处理 CSV 中的特殊字符（引号、换行、逗号）
- 提取文本中的关键信息
- 在 dify/ruoyi 中应用

## 📚 前置知识

- 01-09 正则基础
- 字符串处理基础

## 1. 核心概念

### 1.1 常见脏数据

- 空白字符（多余空格、Tab、换行）
- 特殊字符（HTML 标签、URL 编码）
- 不一致格式（日期、电话）
- 重复内容

### 1.2 CSV 的复杂性

```
name,age,city
"Alice, Jr.",30,"New York"
"Bob","25","San Francisco"
"Carol with ""quotes""",28,"Beijing"
```

- 字段含 `,` 时用 `"..."` 包裹
- 字段含 `"` 时用 `""` 转义

### 1.3 数据清洗 vs 数据转换

- **清洗**：去除不需要的内容（如 HTML 标签）
- **转换**：改变格式（如日期 `2026/07/13` → `2026-07-13`）
- **提取**：从原文提取关键信息

## 2. 代码示例

### 2.1 去除空白

```python
import re

text = "  Hello   World  \n\n  "

# 去除两端空白
print(repr(text.strip()))  # 'Hello   World'

# 去除所有空白（替换为单个空格）
cleaned = re.sub(r"\s+", " ", text).strip()
print(repr(cleaned))  # 'Hello World'
```

### 2.2 去除 HTML 标签

```python
html = "<p>Hello <b>World</b>!</p>"

# 去除所有标签
text = re.sub(r"<[^>]+>", "", html)
print(text)  # Hello World!

# 提取纯文本（保留结构）
text = re.sub(r"<[^>]+>", "", html)
text = re.sub(r"\s+", " ", text).strip()
print(text)
```

### 2.3 URL 解码和清理

```python
import re
from urllib.parse import unquote

# 从 HTML 中提取 URL
html = '<a href="https://example.com/path?q=hello%20world">Link</a>'

# 提取 URL
urls = re.findall(r'href="([^"]+)"', html)
print(urls)  # ['https://example.com/path?q=hello%20world']

# URL 解码
for url in urls:
    print(unquote(url))  # https://example.com/path?q=hello world
```

### 2.4 日期格式归一化

```python
import re

dates = ["2026/07/13", "2026-7-13", "2026.07.13", "July 13, 2026", "20260713"]

# 标准化为 YYYY-MM-DD
patterns = [
    (r"(\d{4})[/\.](\d{1,2})[/\.](\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
    (r"(\d{4})-(\d{1,2})-(\d{1,2})", lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
    (r"(\d{4})(\d{2})(\d{2})", lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
]

for date in dates:
    result = date
    for pattern, repl in patterns:
        new_result = re.sub(pattern, repl, result)
        if new_result != result:
            result = new_result
            break
    print(f"{date} → {result}")
```

### 2.5 CSV 解析（简单版）

```python
import re

csv_line = '"Alice, Jr.",30,"New York"'

# 复杂 CSV 字段解析
def parse_csv_line(line: str) -> list[str]:
    """支持引号和逗号"""
    fields = []
    # 匹配：要么是引号内的内容，要么是不含逗号的连续字符
    pattern = r'"([^"]*(?:""[^"]*)*)"|([^,]+)'
    for m in re.finditer(pattern, line):
        # 两个组，要么第一个匹配，要么第二个
        field = m.group(1) if m.group(1) is not None else m.group(2)
        # 处理 "" → "
        field = field.replace('""', '"')
        fields.append(field)
    return fields


print(parse_csv_line(csv_line))
# ['Alice, Jr.', '30', 'New York']

print(parse_csv_line('"Bob","25","San Francisco"'))
# ['Bob', '25', 'San Francisco']
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的提示词模板清理

**位置**：`/Users/xu/code/github/dify/api/core/prompt/`
**核心代码**：

```python
import re

def clean_prompt_template(template: str) -> str:
    """清理提示词模板——去除多余空白"""
    # 去除连续空白（保留单个空格）
    template = re.sub(r"\s+", " ", template)
    # 去除首尾空白
    template = template.strip()
    return template


# 测试
tmpl = """
You are a helpful   assistant.

Please help the user.
"""
print(repr(clean_prompt_template(tmpl)))
# 'You are a helpful assistant. Please help the user.'
```

**解读**：
- 去除多余空白——LLM 处理更稳定
- dify 用正则做简单的文本预处理

### 3.2 ruoyi 的 HTML 内容清理

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`
**核心代码**：

```java
public class StringUtils {
    // 去除 HTML 标签
    public static String stripHtml(String html) {
        if (html == null) return "";
        return html.replaceAll("<[^>]+>", "").replaceAll("\\s+", " ").trim();
    }

    // 提取 HTML 中的纯文本（保留换行）
    public static String extractText(String html) {
        if (html == null) return "";
        // 把块级标签替换为换行
        String text = html.replaceAll("(?i)</?(p|br|div|li|h[1-6])[^>]*>", "\n");
        // 去除其他标签
        text = text.replaceAll("<[^>]+>", "");
        // 去除多余空白
        text = text.replaceAll("[ \\t]+", " ").replaceAll("\\n+", "\n").trim();
        return text;
    }
}
```

**解读**：
- ruoyi 用正则做 HTML 清理
- 块级标签替换为换行，保留结构

### 3.3 dify 的 LLM 输出解析

**位置**：`/Users/xu/code/github/dify/api/core/llm_generator/`
**核心代码**：

```python
import re

def extract_code_from_llm_output(text: str) -> str:
    """从 LLM 输出提取代码（被 ``` 包裹）"""
    # 匹配 ```language\ncode\n```
    pattern = r"```(?:\w+)?\n(.*?)\n```"
    matches = re.findall(pattern, text, re.DOTALL)
    return "\n\n".join(matches) if matches else text
```

**解读**：
- LLM 输出常用 markdown 代码块
- 用非贪婪提取代码内容

## 4. 关键要点总结

- 数据清洗：去除空白、HTML 标签、特殊字符
- 用 `re.sub` 替换，`re.findall` 提取
- CSV 解析要注意引号和转义
- 日期格式归一化用多个正则依次尝试
- dify/ruoyi 都用正则做文本预处理

## 5. 练习题

### 练习 1：基础
清洗一段脏文本：去除 HTML 标签、多余空白、特殊字符。

### 练习 2：进阶
解析一段 CSV 数据（含引号、转义），输出结构化字段。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/prompt/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13