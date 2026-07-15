# 1.1.6 异常体系：Checked vs Unchecked

> 掌握 Java 异常的分类、抛出与捕获，能看懂 ruoyi 的 `ServiceException` / `ErrorCode` 体系。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Checked Exception 与 Unchecked Exception
- 正确使用 `try/catch/finally` 和 `try-with-resources`
- 理解 ruoyi 自定义 `ServiceException` 的设计意图
- 能在 Controller 层做合理的异常处理

## 📚 前置知识

- 面向对象基础（继承、接口）
- 02-oop.md

## 1. 核心概念

### 1.1 Java 异常层次结构

```
                  Throwable
                  /        \
             Error         Exception
         (OutOfMemory)    /          \
                  RuntimeException    IOException
                  (Unchecked)        (Checked)
```

- **Error**：JVM 错误（如 `OutOfMemoryError`），应用程序不应捕获
- **Exception**：程序应处理的异常
  - **Checked Exception**：编译期强制处理（`IOException`、`SQLException`）
  - **Unchecked Exception**：`RuntimeException` 及其子类（`NullPointerException`、`IllegalArgumentException` 等），不强制处理

### 1.2 try-catch-finally

```java
try {
    doSomething();                  // 可能抛异常的代码
} catch (IOException e) {           // 捕获特定异常
    log.error("IO 异常", e);
} finally {                          // 不论是否异常都会执行
    cleanup();
}
```

### 1.3 try-with-resources（Java 7+）

自动关闭实现了 `AutoCloseable` 接口的资源：

```java
try (BufferedReader br = new BufferedReader(new FileReader("file.txt"))) {
    return br.readLine();
}  // 自动关闭 br
```

### 1.4 自定义异常

继承 `Exception`（Checked）或 `RuntimeException`（Unchecked）即可：

```java
public class BizException extends RuntimeException {
    public BizException(String message) { super(message); }
}
```

### 1.5 异常处理的最佳实践

1. **早抛出**：能抛就抛，不要吃掉异常
2. **晚捕获**：在能处理的地方捕获，不要捕获完不处理
3. **不要用异常控制流程**（异常对象创建有性能开销）
4. **要带上原始异常**（`throw new RuntimeException(e)`）

## 2. 代码示例

### 2.1 Checked vs Unchecked

```java
// 文件：ExceptionDemo.java
import java.io.*;

public class ExceptionDemo {

    // ❌ 错误写法：直接抛出 Checked 异常，调用方被迫处理
    public String readLine1(String path) throws IOException {
        BufferedReader br = new BufferedReader(new FileReader(path));
        return br.readLine();
    }

    // ✅ 正确写法：包装成 Unchecked 异常（业务错误无需强制处理）
    public String readLine2(String path) {
        try (BufferedReader br = new BufferedReader(new FileReader(path))) {
            return br.readLine();
        } catch (IOException e) {
            throw new RuntimeException("读取失败: " + path, e);
        }
    }
}
```

### 2.2 多 catch 与 finally

```java
// 文件：MultiCatch.java
public class MultiCatch {

    public void parse(String s) {
        try {
            int n = Integer.parseInt(s);
            System.out.println(n / 0);     // 抛出 ArithmeticException
        } catch (NumberFormatException e) {
            System.out.println("不是数字: " + s);
        } catch (ArithmeticException e) {
            System.out.println("不能除 0");
        } finally {
            System.out.println("永远会执行");
        }
    }

    public static void main(String[] args) {
        new MultiCatch().parse("abc");
        // 输出：不是数字: abc
        //       永远会执行
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 业务异常 `ServiceException`

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/exception/ServiceException.java`
**核心代码**（行 1-39）：

```java
package cn.iocoder.yudao.framework.common.exception;

import cn.iocoder.yudao.framework.common.exception.enums.ServiceErrorCodeRange;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 业务逻辑异常 Exception
 */
@Data
@EqualsAndHashCode(callSuper = true)
public final class ServiceException extends RuntimeException {

    /**
     * 业务错误码
     *
     * @see ServiceErrorCodeRange
     */
    private Integer code;
    /**
     * 错误提示
     */
    private String message;

    /**
     * 空构造方法，避免反序列化问题
     */
    public ServiceException() {
    }

    public ServiceException(ErrorCode errorCode) {
        this.code = errorCode.getCode();
        this.message = errorCode.getMsg();
    }

    public ServiceException(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
```

**解读**：
- 第 1 行：继承 `RuntimeException`，是 **Unchecked 异常**，调用方不必强制 try/catch
- 第 1 行：`final` 类，禁止再被继承（统一异常处理策略）
- 第 7 行：自定义 `code` 字段，避免只看 `message` 区分错误类型
- 第 13 行：保留空构造方法避免 Jackson 反序列化失败
- **设计意图**：业务代码只需 `throw new ServiceException(USER_NOT_EXISTS)`，全局异常处理器会捕获并返回 JSON 给前端（全局异常处理详见 [17-exception-handler](../02-spring-boot/17-exception-handler.md)）

### 3.2 错误码 `ErrorCode`

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/exception/ErrorCode.java`
**核心代码**（行 1-32）：

```java
package cn.iocoder.yudao.framework.common.exception;

import cn.iocoder.yudao.framework.common.exception.enums.GlobalErrorCodeConstants;
import cn.iocoder.yudao.framework.common.exception.enums.ServiceErrorCodeRange;
import lombok.Data;

/**
 * 错误码对象
 *
 * 全局错误码，占用 [0, 999], 参见 {@link GlobalErrorCodeConstants}
 * 业务异常错误码，占用 [1 000 000 000, +∞)，参见 {@link ServiceErrorCodeRange}
 *
 * TODO 错误码设计成对象的原因，为未来的 i18 国际化做准备
 */
@Data
public class ErrorCode {

    /**
     * 错误码
     */
    private final Integer code;
    /**
     * 错误提示
     */
    private final String msg;

    public ErrorCode(Integer code, String message) {
        this.code = code;
        this.msg = message;
    }

}
```

**解读**：
- 第 11 行：`final` 字段让 `ErrorCode` 对象不可变，线程安全
- 第 8 行：预留 i18n（国际化）能力，未来可以根据地区返回不同语言
- 第 11 行：注释说明错误码分段设计——全局错误码段是 `[0, 999]`，业务错误码段是 `[10亿, +∞)`，避免冲突
- 配合 `ServiceException` 使用：`throw new ServiceException(new ErrorCode(1_001_001_001, "用户不存在"))`

## 4. 关键要点总结

- `Throwable` 有两个子类：`Error`（不处理）和 `Exception`（应处理）
- `Checked Exception` 必须显式处理；`Unchecked`（`RuntimeException`）可不处理
- `try-with-resources` 是管理资源的最佳方式
- ruoyi 自定义 `ServiceException` + `ErrorCode` 把"业务错误"统一化，便于全局异常处理

## 5. 练习题

### 练习 1：基础（必做）

写一个 `UserService.login(username, password)` 方法，要求：
- 用户名为 null 抛 `IllegalArgumentException`
- 用户不存在抛自定义 `UserNotFoundException`（继承 `ServiceException`）
- 密码错误抛 `BadCredentialsException`

### 练习 2：进阶

阅读 `CommonResult#checkError()` 方法（行 99-114），解释它是如何把 `CommonResult` 错误转换为 `ServiceException` 的。

### 练习 3：挑战（选做）

> 学完 [17-exception-handler](../02-spring-boot/17-exception-handler.md) 后再做：实现一个 `@ControllerAdvice` 风格的全局异常处理类（伪代码即可），捕获 `ServiceException` 后返回对应的 `CommonResult`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/exception/ServiceException.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/exception/ErrorCode.java`
- 《Java 核心技术 卷 I》第 7 章：异常、断言和日志
- Alibaba Java 开发手册：异常处理章节

---

**文档版本**：v1.0
**最后更新**：2026-07-13
