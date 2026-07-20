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

## 3. 关键要点总结

- `Throwable` 有两个子类：`Error`（不处理）和 `Exception`（应处理）
- `Checked Exception` 必须显式处理；`Unchecked`（`RuntimeException`）可不处理
- `try-with-resources` 是管理资源的最佳方式
- ruoyi 自定义 `ServiceException` + `ErrorCode` 把"业务错误"统一化，便于全局异常处理

---

**文档版本**：v1.0
**最后更新**：2026-07-13
