# 01 - Java 基础与工具

> Java 后端开发的基石。掌握这部分才能阅读 ruoyi-vue-pro 的源码。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 模块 1.1 Java 语言基础

- [ ] [1.1.1 Java 语法基础：变量、类型、控制流](./01-java-syntax.md)
- [ ] [1.1.2 面向对象：类、继承、接口、抽象类](./02-oop.md)
- [ ] [1.1.3 泛型与类型擦除](./03-generics.md)
- [ ] [1.1.4 注解（Annotation）原理与自定义](./04-annotation.md)
- [ ] [1.1.5 反射（Reflection）](./05-reflection.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [06-*-java-basics: Java 语言核心](./06-*-java-basics.md)
  - 覆盖：01-java-syntax.md, 02-oop.md, 03-generics.md, 04-annotation.md, 05-reflection.md

- [ ] [1.1.6 异常体系：Checked vs Unchecked](./07-exception.md)
- [ ] [1.1.7 集合框架：List / Set / Map](./08-collections.md)
- [ ] [1.1.8 Stream API 与 Lambda](./09-stream-lambda.md)
- [ ] [1.1.9 Optional 与空值处理](./10-optional.md)
- [ ] [1.1.10 Java 8 时间 API（java.time）](./11-time-api.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [12-*-collections-stream: 集合 / Stream / Optional / 时间 API](./12-*-collections-stream.md)
  - 覆盖：07-exception.md, 08-collections.md, 09-stream-lambda.md, 10-optional.md, 11-time-api.md


## 模块 1.2 Java 工程化工具

- [ ] [1.2.1 Maven 多模块项目结构](./13-maven-modules.md)
- [ ] [1.2.2 Maven 依赖管理：BOM 与 dependencyManagement](./14-maven-bom.md)
- [ ] [1.2.3 Maven 生命周期与插件](./15-maven-lifecycle.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [16-*-maven-tools: Maven 多模块与生命周期](./16-*-maven-tools.md)
  - 覆盖：13-maven-modules.md, 14-maven-bom.md, 15-maven-lifecycle.md

- [ ] [1.2.4 Lombok 原理与常用注解](./17-lombok.md)
- [ ] [1.2.5 MapStruct 对象映射](./18-mapstruct.md)
- [ ] [1.2.6 Hutool 工具库](./19-hutool.md)
- [ ] [1.2.7 日志框架：SLF4J + Logback](./20-logging.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [21-*-lombok-tools: Lombok / MapStruct / Hutool / 日志](./21-*-lombok-tools.md)
  - 覆盖：17-lombok.md, 18-mapstruct.md, 19-hutool.md, 20-logging.md


## 模块 1.3 JVM 基础

- [ ] [1.3.1 JVM 内存模型：堆、栈、方法区](./22-jvm-memory.md)
- [ ] [1.3.2 垃圾回收（GC）基础](./23-gc.md)
- [ ] [1.3.3 类加载机制](./24-classloader.md)
- [ ] [1.3.4 线程基础：Thread / Runnable / Callable](./25-thread.md)
- [ ] [1.3.5 线程池：ExecutorService](./26-thread-pool.md)
- [ ] [1.3.6 JUC 工具类：CountDownLatch / CyclicBarrier](./27-juc.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [28-*-jvm-thread: JVM / 线程 / 线程池 / JUC 基础](./28-*-jvm-thread.md)
  - 覆盖：22-jvm-memory.md, 23-gc.md, 24-classloader.md, 25-thread.md, 26-thread-pool.md, 27-juc.md


## 模块 1.4 Java 进阶（高级特性）

- [ ] [1.4.1 垃圾回收器详解：Serial / Parallel / CMS / G1 / ZGC](./29-jvm-gc-detail.md)
- [ ] [1.4.2 JVM 参数调优](./30-jvm-tuning.md)
- [ ] [1.4.3 并发集合：ConcurrentHashMap / CopyOnWriteArrayList](./31-concurrent-collections.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [32-*-concurrent: GC 调优视角与并发集合](./32-*-concurrent.md)
  - 覆盖：29-jvm-gc-detail.md, 30-jvm-tuning.md, 31-concurrent-collections.md

- [ ] [1.4.4 锁机制：synchronized / ReentrantLock / ReadWriteLock](./33-lock.md)
- [ ] [1.4.5 原子类：AtomicInteger / AtomicReference](./34-atomic.md)
- [ ] [1.4.6 AQS 抽象队列同步器原理](./35-aqs.md)
- [ ] [1.4.7 ThreadLocal 与 InheritableThreadLocal](./36-threadlocal.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [37-*-lock-aqs: 锁 / 原子类 / AQS / ThreadLocal](./37-*-lock-aqs.md)
  - 覆盖：33-lock.md, 34-atomic.md, 35-aqs.md, 36-threadlocal.md

- [ ] [1.4.8 虚拟线程（Java 21 / Project Loom）](./38-virtual-thread.md)
- [ ] [1.4.9 Netty 网络编程（高并发网络框架）](./39-netty.md)
- [ ] [1.4.10 Reactor / RxJava 响应式编程](./40-reactive.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [41-*-netty-reactive: Netty 与响应式入门](./41-*-netty-reactive.md)
  - 覆盖：38-virtual-thread.md, 39-netty.md, 40-reactive.md


## 🎯 ruoyi-vue-pro 仓库对应位置

- 主项目结构：`/Users/xu/code/github/ruoyi-vue-pro/`
- 父 pom：`pom.xml`
- 依赖管理：`yudao-dependencies/`
- 工具库：`yudao-framework/yudao-common/`
