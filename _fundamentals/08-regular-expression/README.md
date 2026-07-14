# 08 - 正则表达式

> 后端开发必备工具，用于日志解析、数据校验、字符串处理。

## 模块 8.1 基础语法

- [ ] [1.1 元字符：`.` `*` `+` `?` `^` `$` `|` `[]`](./01-metachar.md)
- [ ] [1.2 字符类：`[abc]` `[^abc]` `[a-z]` `\\d` `\\w` `\\s`](./02-char-class.md)
- [ ] [1.3 量词：`*` `+` `?` `{n}` `{n,}` `{n,m}` 贪婪与非贪婪](./03-quantifier.md)
- [ ] [1.4 分组与捕获：`(...)` `(?:...)` `(?P<name>...)`](./04-group.md)
- [ ] [1.5 锚点：`^` `$` `\\b` `\\B` 零宽断言](./05-anchor.md)

## 模块 8.2 进阶特性

- [ ] [2.1 反向引用与回溯](./06-backreference.md)
- [ ] [2.2 零宽断言：lookahead / lookbehind](./07-lookaround.md)
- [ ] [2.3 贪婪 vs 非贪婪匹配](./08-greedy.md)
- [ ] [2.4 正则引擎：DFA vs NFA](./09-engine.md)

## 模块 8.3 实战应用

- [ ] [3.1 邮箱 / 手机号 / URL 校验](./10-validation.md)
- [ ] [3.2 日志解析：Nginx / Apache 日志](./11-log-parse.md)
- [ ] [3.3 数据清洗：CSV / 文本](./12-data-cleaning.md)
- [ ] [3.4 密码强度校验](./13-password-strength.md)

## 模块 8.4 各语言实现

- [ ] [4.1 Python re 模块](./14-python-re.md)
- [ ] [4.2 Java 正则（java.util.regex）](./15-java-regex.md)

## 🎯 在 dify/ruoyi 中的应用

- **dify**：邮箱校验、URL 提取（`api/services/account_service.py`）
- **ruoyi**：手机号 / 身份证 / 银行卡校验（`yudao-common/`）
