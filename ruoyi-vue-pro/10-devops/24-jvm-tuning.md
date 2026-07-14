# 6.1 JVM 调优：GC 参数

> 理解 JVM 内存模型与 GC 工作原理，掌握 Spring Boot 应用的 JVM 调优实战参数。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 JVM 内存模型（堆 / 栈 / 元空间）
- 掌握 GC 收集器的选择与参数
- 能根据业务场景调优 JVM
- 知道 ruoyi 部署脚本的 JVM 参数配置

## 📚 前置知识

- Java 基础
- `02-spring-boot-jar.md`
- `07-jvm-image.md`

## 1. 核心概念

### 1.1 JVM 内存模型

```
┌──────────────────────────────────────┐
│            JVM 内存                    │
├──────────────────────────────────────┤
│ 堆 (Heap) - 线程共享                   │
│   ├── Young Gen (年轻代)              │
│   │    ├── Eden                       │
│   │    └── Survivor (S0, S1)         │
│   └── Old Gen (老年代)                 │
├──────────────────────────────────────┤
│ MetaSpace (元空间) - 类元数据          │
│ Code Cache - JIT 编译代码              │
│ Thread Stack - 线程栈（私有）          │
│ Direct Memory - NIO 直接内存          │
└──────────────────────────────────────┘
```

### 1.2 GC 类型

| GC | 范围 | 算法 | 适用 |
|----|------|------|------|
| **Serial** | Young/Old | 串行 | 客户端小应用 |
| **Parallel** | Young/Old | 多线程并行 | 吞吐量优先 |
| **G1** | 全堆 | 区域分代 | **服务端首选**（JDK 8+） |
| **ZGC** | 全堆 | 并发 | 超大堆（TB 级） |
| **Shenandoah** | 全堆 | 并发 | 类似 ZGC |

### 1.3 关键 JVM 参数

| 类别 | 参数 | 说明 |
|------|------|------|
| **堆大小** | `-Xms / -Xmx` | 初始/最大堆（建议相同避免扩容） |
| **容器感知** | `-XX:MaxRAMPercentage=N` | 最大堆占容器内存的 N% |
| **元空间** | `-XX:MaxMetaspaceSize=512m` | 限制元空间 |
| **GC** | `-XX:+UseG1GC` | 启用 G1 收集器 |
| **GC 日志** | `-Xloggc:/path/gc.log` | GC 日志路径 |
| **OOM** | `-XX:+HeapDumpOnOutOfMemoryError` | OOM 生成堆转储 |
| **JFR** | `-XX:StartFlightRecording=...` | Java Flight Recorder |

## 2. 代码示例

### 2.1 推荐 JVM 参数（生产环境）

```bash
JAVA_OPTS="
  -Xms4g
  -Xmx4g
  -XX:MaxRAMPercentage=75.0
  -XX:+UseG1GC
  -XX:MaxGCPauseMillis=200
  -XX:+HeapDumpOnOutOfMemoryError
  -XX:HeapDumpPath=/work/dump/heap.hprof
  -Xloggc:/work/logs/gc-%t.log
  -XX:+PrintGCDetails
  -XX:+PrintGCDateStamps
  -XX:+UseGCLogFileRotation
  -XX:NumberOfGCLogFiles=10
  -XX:GCLogFileSize=100M
  -Djava.security.egd=file:/dev/./urandom
"
```

**说明**：
- `-Xms4g -Xmx4g` — 固定堆大小（避免运行时扩容引起 GC 抖动）
- `-XX:+UseG1GC` — 使用 G1 收集器（JDK 8 默认，但显式声明更清晰）
- `-XX:MaxGCPauseMillis=200` — 目标最大 GC 暂停 200ms（G1 会自动调整）
- `-XX:+HeapDumpOnOutOfMemoryError` — OOM 自动生成堆转储
- GC 日志按 100MB 切分，保留 10 个文件

### 2.2 容器化 JVM 参数

```bash
# 推荐（容器感知）
JAVA_OPTS="
  -XX:MaxRAMPercentage=75.0
  -XX:InitialRAMPercentage=50.0
  -XX:+UseG1GC
"
```

**说明**：
- 不固定 `-Xmx`，让 JVM 根据容器内存自动计算
- 容器内存变化时 JVM 自动跟随（K8s 扩缩容友好）

## 3. ruoyi 仓库源码解读

### 3.1 Dockerfile 的默认 JVM 参数

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 14）：

```dockerfile
## 设置 JAVA_OPTS 环境变量，可通过 docker run -e "JAVA_OPTS=" 进行覆盖
ENV JAVA_OPTS="-Xms512m -Xmx512m -Djava.security.egd=file:/dev/./urandom"
```

**解读**：
- `-Xms512m -Xmx512m` — 固定 512M（适合本地开发或轻量部署）
- **生产环境建议** 通过 `docker run -e "JAVA_OPTS=..."` 覆盖

### 3.2 部署脚本的 JVM 参数

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 17-19）：

```bash
# heapError 存放路径
HEAP_ERROR_PATH=$BASE_PATH/heapError
# JVM 参数
JAVA_OPS="-Xms512m -Xmx512m -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=$HEAP_ERROR_PATH"
```

**解读**：
- 第 4 行：OOM 堆转储路径 `/work/projects/yudao-server/heapError/`
- **生产环境建议**：根据物理内存调整 `-Xms / -Xmx`
- **注意**：变量名是 `JAVA_OPS`（不是 `JAVA_OPTS`），自定义时注意拼写

### 3.3 docker-compose 注入 JVM 参数

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 40-45）：

```yaml
      JAVA_OPTS:
        ${JAVA_OPTS:-
          -Xms512m
          -Xmx512m
          -Djava.security.egd=file:/dev/./urandom
        }
```

**解读**：
- 第 1-6 行：多行 YAML 写法，会合并为单行字符串
- `${JAVA_OPTS:-...}` — 从 `docker.env` 读取 `JAVA_OPTS` 变量
- 未定义则使用默认 512M 堆
- **生产环境**：在 `docker.env` 中设置 `JAVA_OPTS=-Xms4g -Xmx4g -XX:+UseG1GC`

### 3.4 启动命令使用 JAVA_OPTS

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 23）：

```dockerfile
## 启动后端项目
CMD java ${JAVA_OPTS} -jar app.jar $ARGS
```

**解读**：
- `${JAVA_OPTS}` 引用环境变量
- Docker 启动时通过 `environment.JAVA_OPTS` 覆盖

### 3.5 推荐的生产环境调优

**生产环境 JVM 参数**（基于 ruoyi）：

```bash
# docker.env
JAVA_OPTS="
  -Xms4g
  -Xmx4g
  -XX:MaxRAMPercentage=75.0
  -XX:+UseG1GC
  -XX:MaxGCPauseMillis=200
  -XX:+HeapDumpOnOutOfMemoryError
  -XX:HeapDumpPath=/dump/heap.hprof
  -Xloggc:/var/log/gc.log
  -XX:+PrintGCDetails
  -XX:+PrintGCDateStamps
  -XX:+UseGCLogFileRotation
  -XX:NumberOfGCLogFiles=10
  -XX:GCLogFileSize=100M
  -Djava.security.egd=file:/dev/./urandom
  -XX:+UnlockExperimentalVMOptions
  -XX:+UseCGroupMemoryLimitForHeap
"
```

## 4. 关键要点总结

- JDK 8+ 用 **G1 GC** 是首选（默认）
- 生产环境建议 `-Xms = -Xmx` 避免堆扩容引起 GC
- 容器化用 `-XX:MaxRAMPercentage=75.0` 自适应内存
- 必须设置 `-XX:+HeapDumpOnOutOfMemoryError` 自动生成堆转储
- ruoyi 默认 512M 是**开发用**，生产环境需要 4-8G
- 通过 `docker-compose` 的 `JAVA_OPTS` 环境变量覆盖

## 5. 练习题

### 练习 1：基础（必做）

启动 yudao-server 时通过 `-Xms256m -Xmx256m` 限制堆为 256M，故意用代码触发 OOM（`new ArrayList<>(); while (true) list.add(new byte[10*1024*1024])`），观察 `-XX:HeapDumpOnOutOfMemoryError` 是否生成堆转储。

### 练习 2：进阶

用 `jstat -gc <pid> 1s` 观察 G1 GC 频率和暂停时间，调整 `-XX:MaxGCPauseMillis` 参数，对比 GC 行为变化。

### 练习 3：挑战（选做）

用 **JDK Mission Control**（或 VisualVM）分析 GC 日志和堆转储，识别内存泄漏点，提交优化报告。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- `/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
- [Java HotSpot VM Options](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html)
- [G1 GC 调优指南](https://www.oracle.com/technical-resources/articles/java/g1gc.html)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
