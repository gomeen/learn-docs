# 4.2 Java 正则（java.util.regex）

> Java 的 `java.util.regex` 包提供完整的正则支持，是企业级开发的标配。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 Java 正则的 3 个核心类
- 使用 `Pattern` / `Matcher` / `PatternSyntaxException`
- 对比 Python re 与 Java regex 的差异
- 在 ruoyi 中应用 Java 正则

## 📚 前置知识

- 14-python-re.md

## 1. 核心概念

### 1.1 3 个核心类

| 类 | 作用 |
|----|------|
| `Pattern` | 编译后的正则表达式 |
| `Matcher` | 在输入字符串上执行匹配操作的引擎 |
| `PatternSyntaxException` | 正则语法异常 |

### 1.2 典型用法

```java
Pattern p = Pattern.compile("\\d+");
Matcher m = p.matcher("abc123");
while (m.find()) {
    System.out.println(m.group());
}
```

### 1.3 Java vs Python 差异

| 维度 | Python `re` | Java `java.util.regex` |
|------|-------------|----------------------|
| 反斜杠 | `r"\d"`（raw） | `"\\d"`（需转义） |
| 命名组 | `(?P<name>...)` | `(?<name>...)` |
| 反向引用 | `(?P=name)` | `\k<name>` |
| 编译 | 隐式或 `re.compile()` | 必须 `Pattern.compile()` |

### 1.4 常用修饰符

| Flag | 含义 |
|------|------|
| `Pattern.CASE_INSENSITIVE` | 忽略大小写 |
| `Pattern.MULTILINE` | 多行模式 |
| `Pattern.DOTALL` | `.` 匹配换行 |
| `Pattern.COMMENTS` | 详细模式（允许注释） |

## 2. 代码示例

### 2.1 基本匹配

```java
import java.util.regex.*;

public class RegexDemo {
    public static void main(String[] args) {
        // 编译正则
        Pattern p = Pattern.compile("\\d+");
        Matcher m = p.matcher("abc123 def456");

        // 查找所有匹配
        while (m.find()) {
            System.out.println("匹配: " + m.group() +
                             ", 位置: " + m.start() + "-" + m.end());
        }
    }
}
```

### 2.2 命名组

```java
import java.util.regex.*;

public class NamedGroupDemo {
    public static void main(String[] args) {
        String text = "John 30 alice@example.com";

        Pattern p = Pattern.compile(
            "(?<name>\\w+)\\s+(?<age>\\d+)\\s+(?<email>[\\w.@]+)"
        );
        Matcher m = p.matcher(text);

        if (m.matches()) {
            System.out.println("Name: " + m.group("name"));
            System.out.println("Age: " + m.group("age"));
            System.out.println("Email: " + m.group("email"));
        }
    }
}
```

### 2.3 替换与分割

```java
// 替换
String result = "Hello 123 World 456".replaceAll("\\d+", "X");
System.out.println(result);  // Hello X World X

// 分割
String[] parts = "a,b,,c".split(",");
System.out.println(Arrays.toString(parts));  // [a, b, , c]

// 限制分割次数
String[] parts2 = "a,b,c,d".split(",", 2);
System.out.println(Arrays.toString(parts2));  // [a, b,c,d]
```

### 2.4 校验方法

```java
public static boolean isValidEmail(String email) {
    String regex = "^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$";
    return Pattern.matches(regex, email);
}

public static boolean isValidMobile(String mobile) {
    String regex = "^1[3-9]\\d{9}$";
    return Pattern.matches(regex, mobile);
}
```

### 2.5 捕获组提取

```java
String url = "https://api.example.com:8080/users?id=123";
Pattern p = Pattern.compile("^(?<protocol>https?)://(?<host>[\\w.-]+)(?::(?<port>\\d+))?(?<path>\\S*)?$");
Matcher m = p.matcher(url);
if (m.matches()) {
    System.out.println("Protocol: " + m.group("protocol"));
    System.out.println("Host: " + m.group("host"));
    System.out.println("Port: " + m.group("port"));
    System.out.println("Path: " + m.group("path"));
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的校验工具类

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/ValidationUtils.java`
**核心代码**：

```java
import java.util.regex.Pattern;

public class ValidationUtils {
    // 编译为静态常量（避免每次重新编译）
    private static final Pattern EMAIL_PATTERN = Pattern.compile(
        "^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"
    );
    private static final Pattern MOBILE_PATTERN = Pattern.compile(
        "^1[3-9]\\d{9}$"
    );
    private static final Pattern ID_CARD_PATTERN = Pattern.compile(
        "^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]$"
    );

    public static boolean isEmail(String email) {
        return email != null && EMAIL_PATTERN.matcher(email).matches();
    }

    public static boolean isMobile(String mobile) {
        return mobile != null && MOBILE_PATTERN.matcher(mobile).matches();
    }

    public static boolean isIdCard(String idCard) {
        return idCard != null && ID_CARD_PATTERN.matcher(idCard).matches();
    }
}
```

**解读**：
- 用静态常量预编译（性能优化）
- 提供全套中文场景校验
- **整体设计**：标准化、企业级

### 3.2 ruoyi 的注解校验

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/validation/`
**核心代码**：

```java
import jakarta.validation.Constraint;
import jakarta.validation.Payload;
import java.util.regex.Pattern;

@Constraint(validatedBy = MobileValidator.class)
@Target({ElementType.FIELD})
@Retention(RetentionPolicy.RUNTIME)
public @interface Mobile {
    String message() default "手机号格式不正确";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

public class MobileValidator implements ConstraintValidator<Mobile, String> {
    private static final Pattern MOBILE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        return value == null || MOBILE_PATTERN.matcher(value).matches();
    }
}
```

**解读**：
- 用 Jakarta Validation 自定义注解
- `@Mobile` 注解 + `MobileValidator` 校验器
- **整体设计**：声明式校验，业务代码无侵入

## 4. 关键要点总结

- Java 必须 `Pattern.compile()`（显式编译）
- Java 反斜杠需双重转义 `"\\d"`
- 命名组语法 `(?<name>...)`，反向引用 `\k<name>`
- 用静态常量预编译（性能最佳）
- ruoyi 用 Jakarta Validation + 自定义注解

## 5. 练习题

### 练习 1：基础
用 Java 正则实现邮箱、手机号校验工具类。

### 练习 2：进阶
实现自定义 Jakarta Validation 注解 `@StrongPassword`，校验强密码。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/validation/`
- Java Pattern 文档：https://docs.oracle.com/javase/8/docs/api/java/util/regex/Pattern.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13