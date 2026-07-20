# 1.3.1 JVM 内存模型：堆、栈、方法区

> 理解 JVM 运行时数据区的核心结构，能解释 `OutOfMemoryError` 与 `StackOverflowError` 的触发场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 画出 JVM 运行时数据区的结构图
- 区分堆（线程共享）与栈（线程私有）
- 解释各区域放什么、什么时候 GC
- 能用 JVM 参数调整堆大小并排查 OOM

## 📚 前置知识

- Java 基础（对象、引用、方法）
- 集合基础

## 1. 核心概念

### 1.1 JVM 运行时数据区

```
+-----------------------------------+
|              方法区 (Metaspace)     |  <-- 类的元数据、常量池、静态变量
+-----------------------------------+
|                堆 (Heap)          |  <-- 对象实例（新生代/老年代）
|  +-------------+ +-------------+ |
|  |   Young Gen  | |  Old Gen    | |
|  | (Eden|S0|S1) | |              | |
|  +-------------+ +-------------+ |
+-----------------------------------+
+------------------+ +------------------+
|  虚拟机栈 (VM栈)  | |   本地方法栈        |  <-- 线程私有
|  - 栈帧         | |   (Native 方法)   |
+------------------+ +------------------+
|         程序计数器 |                    |  <-- 线程私有（当前指令地址）
+------------------+
```

### 1.2 各区域职责

| 区域             | 线程私有 | 放什么                | 异常                                       |
|----------------|------|--------------------|------------------------------------------|
| **程序计数器**      | 是    | 当前执行指令地址          | 唯一不会 OOM 的区域                            |
| **VM 栈**      | 是    | 每个方法的栈帧（局部变量表、操作数栈） | `StackOverflowError`（递归太深）               |
| **本地方法栈**      | 是    | JNI 调用            | 同上                                       |
| **堆（Heap）**   | 否    | 对象实例 + 数组         | `OutOfMemoryError: Java heap space`       |
| **方法区（元空间）**  | 否    | 类信息、常量池、静态变量      | `OutOfMemoryError: Metaspace`             |

### 1.3 堆的"分代"模型

GC 算法基于"大多数对象很快死亡"的观察，将堆分为：
- **新生代（Young Gen）**：刚创建的对象。分为 Eden + 2 Survivor (S0/S1)
- **老年代（Old Gen）**：熬过多次 GC 还存活的对象

新生代 GC（Minor GC）频繁快速，老年代 GC（Major GC）少但慢。

### 1.4 关键 JVM 参数

```bash
# 堆初始 / 最大
-Xms512m
-Xmx2g

# 新生代大小
-Xmn512m

# 元空间（替代永久代）
-XX:MetaspaceSize=256m
-XX:MaxMetaspaceSize=512m

# 打印 GC 日志
-Xlog:gc*:file=gc.log:time
```

## 2. 代码示例

### 2.1 模拟 `StackOverflowError`

```java
// 文件：StackOverflowDemo.java
public class StackOverflowDemo {

    private static void infiniteRecursion() {
        infiniteRecursion();   // 自身调用，永不返回
    }

    public static void main(String[] args) {
        // VM 栈的栈帧太多 → StackOverflowError
        infiniteRecursion();
    }
}
```

输出（截取）：
```
Exception in thread "main" java.lang.StackOverflowError
    at StackOverflowDemo.infiniteRecursion(StackOverflowDemo.java:5)
    at StackOverflowDemo.infiniteRecursion(StackOverflowDemo.java:5)
```

### 2.2 模拟 `OutOfMemoryError`

```java
// 文件：OOMDemo.java
import java.util.ArrayList;
import java.util.List;

public class OOMDemo {

    public static void main(String[] args) {
        // 1. 堆 OOM：一直往 List 加对象
        List<Object> list = new ArrayList<>();
        while (true) {
            list.add(new byte[1024 * 1024]);  // 每秒 1MB
        }
    }
}
```

运行命令（先限制堆到 256MB）：
```bash
java -Xmx256m OOMDemo
```

输出：
```
Exception in thread "main" java.lang.OutOfMemoryError: Java heap space
```

### 2.3 对象分配与 Young/Old 代流转

```java
// 文件：GcDemo.java
public class GcDemo {
    public static void main(String[] args) {
        // 分配 10 万个临时对象 → 进入 Eden
        for (int i = 0; i < 100000; i++) {
            new Object();
        }
        // GC 时大部分对象已死 → 清理
        System.gc();
    }
}
```

## 3. 关键要点总结

- 堆和栈分别存放"对象"和"方法栈帧"
- 堆是 GC 主战场，分为新生代（频）和老年代（少）
- `StackOverflowError` → 栈帧太多（递归、循环调用）
- `OutOfMemoryError: Java heap space` → 堆满
- ruoyi 部署时务必设置 `-Xms = -Xmx`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
