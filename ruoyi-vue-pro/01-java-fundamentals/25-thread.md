# 1.3.4 线程基础：Thread / Runnable / Callable

> 掌握 Java 多线程基础，能正确创建线程并使用三种返回值机制（无返回值、Future、CompletableFuture）。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `Thread`、`Runnable`、`Callable` 三种线程创建方式
- 理解线程生命周期（NEW → RUNNABLE → BLOCKED → WAITING → TIMED_WAITING → TERMINATED）
- 掌握 `Thread.join`、`Future.get` 等阻塞操作
- 能区分 ruoyi 中"同步阻塞"和"异步非阻塞"两种模式

## 📚 前置知识

- Lambda 表达式（详见 [08-stream-lambda](./09-stream-lambda.md)）
- 集合基础（详见 [07-collections](./08-collections.md)）
- [09-stream-lambda.md](./09-stream-lambda.md)

## 1. 核心概念

### 1.1 三种线程创建方式

| 方式               | 接口          | 返回值  | 异常    |
|------------------|-------------|------|-------|
| `Thread`         | -（直接继承类）    | 无    | -     |
| `Runnable`       | `void run()` | 无    | 不能抛检查异常 |
| `Callable<V>`    | `V call()`   | 有    | 可抛检查异常 |

### 1.2 线程生命周期

6 种状态：
```
       NEW（新建）
        ↓ start()
    RUNNABLE（运行，等待 CPU 时间片）
        ↓
   BLOCKED（等待锁）
        ↓
   WAITING（join / wait 无限期）
        ↓
   TIMED_WAITING（sleep / wait(timeout) 有期限）
        ↓
   TERMINATED（终止）
```

### 1.3 Thread 与 Runnable 的区别

- 直接继承 `Thread`：单继承受限
- 实现 `Runnable`：更灵活，可以与线程池混用
- 实现 `Callable<V>`：能返回值、能抛异常，配合 `FutureTask` 使用

### 1.4 关键 API

```java
new Thread(runnable).start();          // 启动线程
Thread.sleep(1000);                    // 阻塞当前线程 1 秒
thread.join();                         // 等待此线程结束
thread.interrupt();                    // 中断标志
Future.get();                          // 阻塞等待异步结果
CompletableFuture.supplyAsync(() -> ...)  // 异步任务
```

### 1.5 `wait()` / `notify()` 与 `join()` 的差别

- `wait()`：**释放锁**后进入 WAITING
- `notify()`：唤醒在该对象上 wait 的线程
- `join()`：**不释放锁**，等待另一个线程结束

## 2. 代码示例

### 2.1 Runnable 线程

```java
// 文件：RunnableDemo.java
public class RunnableDemo {
    public static void main(String[] args) throws InterruptedException {
        Thread t = new Thread(() -> {
            for (int i = 1; i <= 5; i++) {
                System.out.println("子线程：" + i);
                try {
                    Thread.sleep(500);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            }
        });
        t.start();          // 启动子线程
        t.join();           // 等子线程结束再继续

        System.out.println("主线程结束");
    }
}
```

### 2.2 Callable + FutureTask

```java
// 文件：CallableDemo.java
import java.util.concurrent.*;

public class CallableDemo {
    public static void main(String[] args) throws Exception {
        // 1. 用 FutureTask 包装 Callable
        FutureTask<Integer> task = new FutureTask<>(() -> {
            Thread.sleep(1000);
            return 42;
        });

        new Thread(task).start();

        // 2. 阻塞等待结果
        Integer result = task.get();   // 阻塞
        System.out.println("Result: " + result);   // Result: 42
    }
}
```

### 2.3 CompletableFuture（Java 8 推荐方式）

```java
// 文件：CompletableFutureDemo.java
import java.util.concurrent.CompletableFuture;

public class CompletableFutureDemo {
    public static void main(String[] args) throws Exception {
        // 异步调用，立即返回
        CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
            try { Thread.sleep(1000); } catch (InterruptedException e) {}
            return "async";
        });

        // 做别的事...

        // 阻塞拿结果
        System.out.println(future.get());   // async

        // 链式调用
        CompletableFuture<Integer> lengthFuture = future.thenApply(String::length);
        System.out.println(lengthFuture.get());   // 5
    }
}
```

## 3. 关键要点总结

- 三种线程创建：`Thread`（继承）、`Runnable`（实现）、`Callable`（有返回值）
- 生命周期 6 状态，区分 BLOCKED / WAITING / TIMED_WAITING
- `start()` 启动线程；`join()` / `get()` 等待结果
- 现代写法首选 `CompletableFuture`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
