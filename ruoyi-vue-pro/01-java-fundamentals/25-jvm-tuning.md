# 1.4.2 JVM 参数调优

> 掌握 JVM 常用调优参数的语义与组合，能为 Spring Boot 应用编写生产级启动脚本。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟记最常用的 30 个 JVM 参数及其作用
- 理解 **堆内存、GC、日志、OOM 排查** 四类参数的配置思路
- 能为 ruoyi-vue-pro 这类 Spring Boot 应用编写完整的启动 JVM 参数模板
- 在出现 OOM、频繁 Full GC 时知道去哪里查 GC 日志和 Heap Dump

## 📚 前置知识

- [18-jvm-memory.md](./18-jvm-memory.md)：JVM 内存模型
- [19-gc.md](./19-gc.md)：垃圾回收基础
- [24-jvm-gc-detail.md](./24-jvm-gc-detail.md)：各 GC 实现详解

## 1. 核心概念

### 1.1 JVM 参数的三种类型

| 类型 | 形式 | 稳定性 | 说明 |
|------|------|--------|------|
| **标准参数** | `-version`、`-jar` | 稳定 | 所有 JVM 都支持 |
| **-X 参数** | `-Xms`、`-Xmx` | 非标准但通用 | HotSpot 约定俗成 |
| **-XX 参数** | `-XX:+UseG1GC` | 实验/调优 | 不保证向后兼容，分类繁多 |

`-XX:+` 开启、`-XX:-` 关闭布尔型；`-XX:=` 设置数值型。

### 1.2 调优的三个目标优先级

1. **避免 Full GC**（最致命，单次可达秒级）
2. **降低 GC 频率**（Minor GC 也不要每秒一次）
3. **降低单次 GC 停顿**（G1 的目标）

### 1.3 内存相关参数（最常用）

```bash
# 堆内存
-Xms2g                  # 堆初始大小（生产环境推荐 = -Xmx）
-Xmx2g                  # 堆最大大小
-Xmn1g                  # 新生代大小（一般不显式设置，让 JVM 自动）

# 栈内存
-Xss512k                # 每个线程的栈大小（默认 1M，递归深时调小）

# 元数据区（取代 PermGen）
-XX:MetaspaceSize=256m
-XX:MaxMetaspaceSize=512m

# 直接内存（NIO 用）
-XX:MaxDirectMemorySize=1g
```

**经验值**：
- 物理内存 8G 的服务器：`-Xmx` 通常给 4G，留一半给 OS + 堆外内存
- 容器化部署：`-XX:MaxRAMPercentage=75.0` 让 JVM 自动根据容器 limit 计算堆

### 1.4 GC 选择与调优参数

```bash
# 选择 GC
-XX:+UseG1GC                              # JDK 9+ 默认
-XX:+UseParallelGC                        # JDK 8 默认，吞吐优先
-XX:+UseZGC                               # JDK 15+ 生产可用
-XX:+UseShenandoahGC                      # Shenandoah GC

# G1 调优（最常用的组合）
-XX:MaxGCPauseMillis=200                  # 软目标，单次停顿不超过 200ms
-XX:InitiatingHeapOccupancyPercent=45     # 堆占用 45% 启动并发标记
-XX:G1HeapRegionSize=4m                   # Region 大小（1~32MB）
-XX:ConcGCThreads=4                       # 并发 GC 线程数

# Parallel 调优
-XX:ParallelGCThreads=8                   # GC 线程数（默认 CPU 核数）
-XX:GCTimeRatio=99                        # 99% 应用时间，1% GC（吞吐目标）
-XX:MaxGCPauseMillis=200                  # 软目标
```

### 1.5 OOM 与 Dump 参数

```bash
# OOM 时自动 Dump 堆（救命参数！）
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/data/logs/app/heapdump.hprof

# 触发 OOM 时执行脚本（可选）
-XX:OnOutOfMemoryError="kill -9 %p"        # OOM 时杀进程
-XX:OnOutOfMemoryError="sh /scripts/notify.sh"

# 触发 Error 时（如 OOM）保留 Dump
-XX:ErrorFile=/data/logs/app/hs_err.log
```

### 1.6 GC 日志参数（JDK 9+ 统一日志）

```bash
# JDK 9+ 统一日志（推荐）
-Xlog:gc*:file=/data/logs/app/gc-%t.log:time,uptime,level,tags:filecount=10,filesize=100m

# 等价拆解：
#   -Xlog:gc*         日志类别：所有 gc 相关
#   file=...          输出文件，%t 是启动时间戳
#   :time,uptime      装饰器：时间戳 + 启动时长
#   ,level,tags       日志级别 + tag
#   :filecount=10     滚动保留 10 个文件
#   ,filesize=100m    单文件最大 100MB

# JDK 8 老格式（不推荐）
-XX:+PrintGCDetails
-XX:+PrintGCDateStamps
-XX:+PrintTenuringDistribution
-Xloggc:/data/logs/app/gc.log
```

### 1.7 容器化部署的专用参数

```bash
# 让 JVM 感知容器内存限制（必须！）
-XX:+UseContainerSupport                # JDK 8u191+ 默认开启
-XX:InitialRAMPercentage=50.0           # 初始堆占容器内存 %
-XX:MaxRAMPercentage=75.0               # 最大堆占容器内存 %
-XX:MinRAMPercentage=50.0               # 容器内存 ≤ 256MB 时使用

# 让 JVM 感知 CPU 限制
-XX:+UseContainerSupport                # 自动获取容器 CPU 配额

# 主动让出 CPU 给其他容器
-XX:+AllowUserSignalHandlers
```

### 1.8 性能诊断参数

```bash
# 远程 JMX（生产慎用）
-Dcom.sun.management.jmxremote
-Dcom.sun.management.jmxremote.port=9010
-Dcom.sun.management.jmxremote.authenticate=false
-Dcom.sun.management.jmxremote.ssl=false

# 偏向锁（JDK 15 默认禁用）
-XX:+UseBiasedLocking                   # 高并发下反成累赘，新版本默认关闭

# 字符串去重（G1 特有，节省堆）
-XX:+UseStringDeduplication             # JDK 8u20+
-XX:StringDeduplicationAgeThreshold=3   # 经历 3 次 GC 仍未死的字符串才去重
```

## 2. 代码示例

### 2.1 完整生产级启动脚本模板

```bash
#!/bin/bash
# 文件：start.sh —— Spring Boot 应用生产启动模板

APP_NAME="yudao-server"
JAR_FILE="$APP_NAME.jar"
LOG_DIR="/data/logs/$APP_NAME"
GC_LOG="$LOG_DIR/gc-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"

# JVM 参数：吞吐 + 低延迟 + 可观测性 + 容器感知
JAVA_OPTS="
  -server
  -Xms2g -Xmx2g
  -XX:MaxRAMPercentage=75.0
  -XX:+UseG1GC
  -XX:MaxGCPauseMillis=200
  -XX:+HeapDumpOnOutOfMemoryError
  -XX:HeapDumpPath=$LOG_DIR/heapdump.hprof
  -Xlog:gc*:file=$GC_LOG:time,uptime,level,tags:filecount=10,filesize=100m
  -XX:+UseStringDeduplication
  -Dfile.encoding=UTF-8
  -Duser.timezone=Asia/Shanghai
  -Dspring.profiles.active=prod
"

# exec 让 JVM 替换 shell 进程，方便 kill -15 优雅停机
exec java $JAVA_OPTS -jar $JAR_FILE
```

### 2.2 常见错误配置

```bash
# ❌ 错误 1：堆设置过小（远小于机器内存）
java -Xmx128m -Xms128m -jar app.jar  # 4G 机器只用 128MB，大量内存浪费

# ✅ 正确：按容器/机器内存的 50%~75% 设置
java -Xms2g -Xmx2g -jar app.jar

# ❌ 错误 2：未开启 OOM Dump
java -jar app.jar  # OOM 后无任何线索

# ✅ 正确：开启 HeapDumpOnOutOfMemoryError
java -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dump/heap.hprof -jar app.jar

# ❌ 错误 3：JDK 8 + 大堆却用 CMS（GC 碎片化）
java -Xmx8g -XX:+UseConcMarkSweepGC -jar app.jar

# ✅ 正确：大堆用 G1 或 ZGC
java -Xmx8g -XX:+UseG1GC -jar app.jar
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 Dockerfile 中的 JVM 参数

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 12-23）：

```dockerfile
## 设置 TZ 时区
ENV TZ=Asia/Shanghai

## 设置 JAVA_OPTS 环境变量，可通过 docker run -e "JAVA_OPTS=" 进行覆盖
ENV JAVA_OPTS="-Xms512m -Xmx512m -Djava.security.egd=file:/dev/./urandom"

## 应用参数
ENV ARGS=""

## 暴露后端项目的 48080 端口
EXPOSE 48080

## 启动后端项目
CMD java ${JAVA_OPTS} -jar app.jar $ARGS
```

**解读**：
- **第 14 行**：通过环境变量传入 JVM 参数，支持 `docker run -e "JAVA_OPTS=..."` 覆盖（生产部署友好）
- **第 17 行**：使用 `CMD` 而非 `ENTRYPOINT`，允许 `docker run ... image /bin/bash` 进入容器调试
- **`-Xms512m -Xmx512m`**：固定堆大小，避免运行时扩容抖动（但生产建议根据容器内存调大）
- **`-Djava.security.egd=file:/dev/./urandom`**：让 Tomcat 等使用 `/dev/urandom` 作为随机数源（避免启动卡顿）
- **未启用**：GC 日志、HeapDump、G1/ZGC —— 这些是生产环境建议补充的

### 3.2 Linux 部署脚本：HeapDumpOnOutOfMemoryError

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 16-26, 93-103）：

```bash
# heapError 存放路径
HEAP_ERROR_PATH=$BASE_PATH/heapError
# JVM 参数
JAVA_OPS="-Xms512m -Xmx512m -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=$HEAP_ERROR_PATH"

# SkyWalking Agent 配置（默认注释掉）
#export SW_AGENT_NAME=$SERVER_NAME
#export SW_AGENT_COLLECTOR_BACKEND_SERVICES=192.168.0.84:11800
#export SW_GRPC_LOG_SERVER_HOST=192.168.0.84
#export SW_AGENT_TRACE_IGNORE_PATH="Redisson/PING,/actuator/**,/admin/**"
#export JAVA_AGENT=-javaagent:/work/skywalking/apache-skywalking-apm-bin/agent/skywalking-agent.jar
```

```bash
# 启动：启动后端项目
function start() {
    echo "[start] 开始启动 $BASE_PATH/$SERVER_NAME"
    echo "[start] JAVA_OPS: $JAVA_OPS"
    echo "[start] JAVA_AGENT: $JAVA_AGENT"
    echo "[start] PROFILES: $PROFILES_ACTIVE"

    BUILD_ID=dontKillMe nohup java -server $JAVA_OPS $JAVA_AGENT -jar $BASE_PATH/$SERVER_NAME.jar --spring.profiles.active=$PROFILES_ACTIVE &
    echo "[start] 启动 $BASE_PATH/$SERVER_NAME 完成"
}
```

**解读**：
- **第 17 行**：唯一显式配置的 GC 参数是 `-XX:+HeapDumpOnOutOfMemoryError`（救命参数！）
- **第 102 行**：`-server` 进入 Server 模式
- **第 104 行**：`BUILD_ID=dontKillMe` 是 Jenkins 部署专用环境变量，防止 Jenkins 部署完杀掉新启动的进程
- **第 20-26 行**：SkyWalking Agent 默认注释，但保留模板方便启用
- **实际生产改进建议**：补充 `-XX:+UseG1GC -XX:MaxGCPauseMillis=200 -Xlog:gc*:` 等参数

## 4. 关键要点总结

- **生产必备 4 件套**：`-Xms = -Xmx`、`-XX:+UseG1GC`、`-XX:+HeapDumpOnOutOfMemoryError`、GC 日志
- **容器化必备**：`-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0`
- **JDK 8** 默认 Parallel；**JDK 9+** 默认 G1；**JDK 15+** 生产可用 ZGC
- **调优优先级**：先避免 Full GC → 再降 GC 频率 → 最后降单次停顿
- ruoyi-vue-pro 推荐 G1，OOM 自动 Dump 已内置

## 5. 练习题

### 练习 1：基础（必做）

为 ruoyi-vue-pro 写一个完整的 `start.sh`，包含：堆 2G、G1、200ms 停顿目标、OOM Dump 到 `/data/logs/`、GC 日志滚动保留 10 个文件。

### 练习 2：进阶

使用 `jstat -gc <pid> 1s` 持续观察一个运行中的 Spring Boot 应用的 GC 情况，记录 1 分钟内：
- Young GC 次数、平均耗时
- Full GC 次数、平均耗时
- 各代内存占用变化

### 练习 3：挑战（选做）

模拟一次 OOM：写一个无限往 `List<byte[]>` 里添加 1MB 数组的程序，触发 OOM 后用 MAT 或 VisualVM 分析 heap dump，找出内存泄漏点。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-prod.yml`
- [JVM 工具手册](https://docs.oracle.com/en/java/javase/17/troubleshoot/troubleshooting-guide-using-troubleshoot-tools.html)
- [HotSpot VM Options](https://chriswhocodes.com/hotspot_option_differences.html)
- [G1 Tuning Guideline](https://www.oracle.com/technical-resources/articles/java/g1gc.html)

---

**文档版本**：v1.0
**最后更新**：2026-07-13