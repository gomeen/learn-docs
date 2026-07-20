# 1.4.1 垃圾回收器详解（GC Implementations）

> 掌握主流 JVM 垃圾回收器的工作原理与适用场景，能为 ruoyi-vue-pro 这类 Spring Boot 应用选择合适的 GC。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 HotSpot JVM 中 4 大经典 GC 算法（Serial / Parallel / CMS / G1）以及新一代 ZGC、Shenandoah
- 说出各 GC 的 STW（Stop-The-World）行为差异与吞吐量、延迟特性
- 根据业务场景（吞吐量优先 vs 延迟优先）选择合适的 GC
- 能读懂 ruoyi-vue-pro 启动脚本中的 GC 配置

## 📚 前置知识

- [22-jvm-memory.md](./22-jvm-memory.md)：JVM 内存模型
- [23-gc.md](./23-gc.md)：垃圾回收基础（标记-清除、复制、标记-整理）
- 基础的分代理论：Young / Old / Metaspace

## 1. 核心概念

### 1.1 评估 GC 的三个维度

| 维度 | 含义 | 典型关注点 |
|------|------|------------|
| **吞吐量（Throughput）** | 应用运行时间 / 总时间（GC + 应用） | 批处理、离线计算 |
| **延迟（Latency）** | 单次 STW 时长 | Web API、实时系统 |
| **内存占用（Footprint）** | GC 自身数据结构占用 | 容器化部署 |

**鱼与熊掌不可兼得**：吞吐量高了，延迟通常会变差（GC 收集得少，每次停顿长）；延迟低了，需要更多 GC 线程与更复杂的数据结构，吞吐量可能下降。

### 1.2 GC 分代假说（Generational Hypothesis）

HotSpot 把堆分成：
- **Young（新生代）**：存放新创建的对象。绝大多数对象"朝生夕死"，采用 **复制算法**（Copying）。
- **Old（老年代）**：存活较久的对象。采用 **标记-整理（Mark-Compact）** 或 **标记-清除（Mark-Sweep）**。
- **Metaspace（元数据区）**：JDK 8+ 取代 PermGen，存放类元数据。

对象晋升路径：`Eden → Survivor(from) → Survivor(to) → Old`

### 1.3 各 GC 实现对比

```
┌──────────────┬───────────┬───────────┬────────────────┬─────────────────┐
│ GC           │ 算法      │ STW       │ 适用场景       │ JDK             │
├──────────────┼───────────┼───────────┼────────────────┼─────────────────┤
│ Serial       │ 串行      │ 全程      │ 单核、客户端   │ 所有            │
│ Parallel     │ 并行      │ 全程      │ 吞吐量优先     │ 所有            │
│ CMS          │ 并发标记  │ 短        │ 延迟优先（弃用）│ 8-14            │
│ G1           │ 分区+并发 │ 可预测     │ 大堆、平衡型   │ 9+ 默认         │
│ ZGC          │ 染色指针  │ <1ms      │ 超大堆、超低延迟│ 11+ 实验，15+生产│
│ Shenandoah   │ 并发整理  │ <10ms     │ 类似 ZGC       │ 12+（非 Oracle）│
│ Epsilon      │ 无回收    │ 无        │ 性能测试       │ 11+             │
└──────────────┴───────────┴───────────┴────────────────┴─────────────────┘
```

### 1.4 Serial / Parallel：吞吐量为王

- **Serial**：单线程 STW，简单高效，适合客户端或单核容器。
- **Parallel（ParNew + Parallel Old）**：JDK 8 默认，多线程并行收集，目标是**最大吞吐量**。

```bash
# JDK 8 默认即 Parallel
java -XX:+UseParallelGC -jar app.jar
```

### 1.5 CMS（Concurrent Mark Sweep）

JDK 8 时期延迟优先的首选。过程分 4 阶段：

```
1. 初始标记（Initial Mark）  → STW，标记 GC Roots
2. 并发标记（Concurrent Mark）→ 与应用并发
3. 重新标记（Remark）        → STW，修正并发期间变化
4. 并发清除（Concurrent Sweep）→ 与应用并发
```

**致命缺陷**：
- 内存碎片（只用 Mark-Sweep，不整理）
- Concurrent Mode Failure：并发回收跟不上分配速度，退化为 Serial Old（超长 STW）
- JDK 14 起被废弃（JEP 363），JDK 9 默认 G1

### 1.6 G1（Garbage-First）：平衡型王者

**核心理念**：把堆分成约 2048 个 **Region**（每个 1~32MB），跟踪每个 Region 的"垃圾比例"，优先回收垃圾最多的 Region（Garbage-First 由此得名）。

```
┌─────────────────────────────────────────┐
│  E │ E │ S │ S │  O  │  O  │ H │ ...  │
│ Eden Survivor   Old     Humongous       │
└─────────────────────────────────────────┘
                  ↑ Region 大小可动态调整
```

**过程**（类似 CMS，但分 Region）：
1. **Initial Mark**（STW）：标记 GC Roots，伴随 Young GC
2. **Concurrent Mark**：并发遍历对象图
3. **Remark**（STW）：SATB 算法修正
4. **Cleanup / Copy**（部分 STW）：把存活对象复制到空 Region（同时整理）

**关键参数**：
- `-XX:MaxGCPauseMillis=200`：G1 尽量把单次停顿控制在 200ms 内
- `-XX:InitiatingHeapOccupancyPercent=45`：堆占用 45% 启动并发标记
- `-XX:G1HeapRegionSize=4m`：Region 大小

**适用场景**：JDK 9+ 默认 GC，堆 4~32GB，平衡吞吐与延迟。

### 1.7 ZGC：亚毫秒延迟

**革命性设计**：**染色指针（Colored Pointers）** + **内存多重映射（Mapped Memory）**。

```
普通 64 位指针：       0000 0000 0000 0000 0000 | 对象地址（42 位）
ZGC 染色指针：         M0 M1 Remapped | 对象地址（42 位）
                       ↑ 染色位
```

- **并发整理**：对象移动与标记同时进行，几乎不需要 STW
- **内存多重映射**：把同一段物理内存映射到三段虚拟地址，分别对应染色位的不同状态

**优势**：
- STW 时间与堆大小**无关**（哪怕 TB 级堆，停顿 < 1ms）
- 支持 TB 级堆（最大 16TB）

**JDK 演进**：
- JDK 11：实验性（`-XX:+UnlockExperimentalVMOptions -XX:+UseZGC`）
- JDK 15：生产可用
- JDK 21+：**分代 ZGC**（JEP 439），性能大幅提升

```bash
# JDK 21 推荐分代 ZGC
java -XX:+UseZGC -XX:+ZGenerational -jar app.jar
```

## 2. 代码示例

### 2.1 观察 GC 日志

```java
// 文件：GCDemo.java
public class GCDemo {
    public static void main(String[] args) throws InterruptedException {
        // 持续分配对象，触发 GC
        for (int i = 0; i < 1000; i++) {
            // 每个 byte[] 都是新生对象
            byte[] allocation = new byte[1 << 20]; // 1MB
            Thread.sleep(50);
        }
    }
}
```

**启动命令**（打印详细 GC 日志）：

```bash
# JDK 9+ 统一日志格式
java -Xlog:gc*:file=gc.log:time,uptime,level,tags:filecount=5,filesize=100m \
     -XX:+UseG1GC \
     -Xms2g -Xmx2g \
     GCDemo
```

**日志示例**：
```
[0.512s][info][gc] Using G1
[1.234s][info][gc] GC(0) Pause Young (Normal) (G1 Evacuation Pause) 24M->8M(2048M) 12.345ms
[2.456s][info][gc] GC(1) Pause Young (Concurrent Start) (G1 Humongous Allocation) 32M->12M(2048M) 15.678ms
```

**解读**：
- `Pause Young`：新生代 GC
- `24M->8M`：回收前 24MB，回收后 8MB
- `12.345ms`：本次 STW 时长
- `(2048M)`：总堆大小

### 2.2 触发 Full GC 的常见场景

```java
// 文件：FullGCDemo.java
public class FullGCDemo {
    public static void main(String[] args) {
        // 分配大对象 → 直接进入老年代
        byte[] big = new byte[10 * 1024 * 1024]; // 10MB > G1 HumongousThreshold

        // 内存泄漏模拟：静态集合持有对象引用
        java.util.List<byte[]> leak = new java.util.ArrayList<>();
        for (int i = 0; i < 100; i++) {
            leak.add(new byte[10 * 1024 * 1024]);
        }
    }
}
```

**何时会触发 Full GC**：
1. 老年代空间不足
2. **Humongous Object**（巨型对象）分配失败
3. `System.gc()`（仅是建议，JVM 可忽略）
4. CMS 的 Concurrent Mode Failure
5. 元数据区（Metaspace）不足

## 3. 关键要点总结

- **JDK 8 默认 Parallel**，**JDK 9+ 默认 G1**，**JDK 21 推荐分代 ZGC**
- **G1**：堆 4~32GB 的通用选择，平衡吞吐与延迟
- **ZGC**：堆 > 32GB 或要求 < 10ms 延迟（金融、游戏服务器）
- **CMS 已废弃**（JDK 14），新项目不要再用
- 生产环境务必设置 `-Xms = -Xmx`，避免运行时堆扩容
- `-XX:+HeapDumpOnOutOfMemoryError` 是 OOM 排查的救命稻草
- ruoyi-vue-pro `main` 分支基于 **JDK 8**，默认 GC 是 **ParallelGC**，未显式开启 GC 日志

> **注意**：ruoyi-vue-pro 的 `main` 分支是 **JDK 8 / Spring Boot 2.7** 基线版本（截至 2026.06），分代 ZGC、虚拟线程等特性在 `jdk21` 分支才会涉及。本文档以 JDK 8 ~ 21 通用知识为基准。

---

**文档版本**：v1.0
**最后更新**：2026-07-13
