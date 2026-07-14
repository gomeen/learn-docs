# 3.4 密码强度校验

> 密码强度校验是用户系统的关键防线。本文总结常用的密码强度正则。

## 🎯 学习目标

完成本文档后，你将能够：
- 写出不同强度的密码校验正则
- 区分弱、中、强密码
- 用前瞻断言实现复杂规则
- 在 dify/ruoyi 中应用

## 📚 前置知识

- 01-metachar.md
- 07-lookaround.md（零宽断言）

## 1. 核心概念

### 1.1 密码强度的衡量

| 强度 | 规则 | 适用场景 |
|------|------|---------|
| 弱 | 6+ 位纯字母数字 | 不推荐 |
| 中 | 8+ 位，含字母+数字 | 一般系统 |
| 强 | 8+ 位，含大小写+数字+特殊 | 重要系统 |
| 超强 | 12+ 位，多种字符 | 金融/政企 |

### 1.2 前瞻断言组合

强密码 = 多个 `(?=...)` 前瞻 + 实际匹配段：

```python
^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%]).{8,}$
```

### 1.3 常见密码规则

- 不允许连续字符（如 `123`、`abc`）
- 不允许常见密码（如 `password`、`qwerty`）
- 不允许用户名
- 必须含特殊字符

## 2. 代码示例

### 2.1 弱密码（仅长度）

```python
import re

# 6 位以上
weak = r"^.{6,}$"
print(bool(re.match(weak, "abc")))       # False
print(bool(re.match(weak, "abcdef")))    # True
```

### 2.2 中等密码（dify 默认）

```python
# 8+ 位，含字母和数字
medium = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"

tests = [
    "abc123",      # False（太短）
    "abcdefgh",    # False（无数字）
    "12345678",    # False（无字母）
    "abc12345",    # True
    "Hello123!",   # True
    "abcdefg1",    # True
]

for pwd in tests:
    print(f"{pwd}: {bool(re.match(medium, pwd))}")
```

### 2.3 强密码

```python
# 8+ 位，含大小写、数字、特殊字符
strong = r"""
^
(?=.*[a-z])         # 至少 1 个小写
(?=.*[A-Z])         # 至少 1 个大写
(?=.*\d)            # 至少 1 个数字
(?=.*[!@#$%^&*])    # 至少 1 个特殊字符
[A-Za-z\d!@#$%^&*]{8,}
$
"""

tests = [
    "abc123",           # False（太短）
    "ABCDEFG1",         # False（无小写）
    "abcdefg1",         # False（无大写）
    "Abcdefgh",         # False（无数字）
    "Abcdefg1",         # False（无特殊）
    "Abc12345!",        # True
    "Hello2026@",       # True
]

for pwd in tests:
    print(f"{pwd}: {bool(re.match(strong, pwd, re.X))}")
```

### 2.4 超强密码（12+ 位，多种字符）

```python
super_strong = r"""
^
(?=.*[a-z])
(?=.*[A-Z])
(?=.*\d)
(?=.*[!@#$%^&*])
(?=.*[^a-zA-Z\d\s])  # 至少 1 个非字母数字空白字符
[A-Za-z\d!@#$%^&*]{12,}
$
"""

# 测试
print(bool(re.match(super_strong, "MyPassword2026!@", re.X)))   # True
```

### 2.5 完整密码验证函数

```python
import re

COMMON_PASSWORDS = {"password", "123456", "qwerty", "admin", "letmein"}

def validate_password(password: str, username: str = "") -> tuple[bool, str]:
    """完整密码校验"""
    # 1. 长度
    if len(password) < 8:
        return False, "密码至少 8 位"

    # 2. 常见密码
    if password.lower() in COMMON_PASSWORDS:
        return False, "密码过于简单"

    # 3. 不能含用户名
    if username and username.lower() in password.lower():
        return False, "密码不能包含用户名"

    # 4. 强密码规则
    pattern = r"""
    ^
    (?=.*[a-z])
    (?=.*[A-Z])
    (?=.*\d)
    (?=.*[!@#$%^&*])
    [A-Za-z\d!@#$%^&*]{8,}
    $
    """
    if not re.match(pattern, password, re.X):
        return False, "密码必须含大小写字母、数字、特殊字符"

    return True, "OK"


# 测试
print(validate_password("weak"))                    # False, 太短
print(validate_password("password"))                # False, 常见密码
print(validate_password("alice123", "alice"))       # False, 含用户名
print(validate_password("Hello123!"))               # True, OK
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的密码校验

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
import re

# 8+ 位，含字母和数字
password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"

def valid_password(password):
    if re.match(password_pattern, password) is not None:
        return password
    raise ValueError("Password must contain letters and numbers, and the length must be at least 8 characters.")
```

**解读**：
- 前瞻断言确保含字母和数字
- dify 默认中等强度——平衡安全与可用性

### 3.2 ruoyi 的密码校验（注解方式）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/validation/`
**核心代码**：

```java
// ruoyi 用 Jakarta Validation + 自定义注解
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = PasswordValidator.class)
public @interface Password {
    String message() default "密码必须含大小写字母、数字、特殊字符，长度 8+";
    int minLength() default 8;
    Class<?>[] groups() default {};
}

public class PasswordValidator implements ConstraintValidator<Password, String> {
    private static final Pattern STRONG_PASSWORD = Pattern.compile(
        "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[!@#$%^&*]).{8,}$"
    );

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        return value != null && STRONG_PASSWORD.matcher(value).matches();
    }
}
```

**解读**：
- ruoyi 用 `@Password` 注解做密码校验
- 强密码规则（大小写+数字+特殊字符）
- **整体设计**：注解 + 校验器，简洁优雅

## 4. 关键要点总结

- 弱密码：仅长度
- 中等密码：字母+数字（dify 用）
- 强密码：大小写+数字+特殊（ruoyi 用）
- 用前瞻断言组合实现复杂规则
- 还要检查常见密码、用户名包含等

## 5. 练习题

### 练习 1：基础
写一个正则校验：8+ 位，必须含大小写、数字。

### 练习 2：进阶
实现完整密码校验函数：含常见密码检查、用户名包含检查、强度规则。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/`
- OWASP 认证备忘单：https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13