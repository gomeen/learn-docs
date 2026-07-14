# 2.3 Dockerfile 优化：JVM 镜像

> 理解 JVM 容器镜像的特殊性，掌握镜像层优化、CA 证书、字体支持等实战技巧。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 JVM 在容器中运行时的特殊性
- 掌握镜像层优化（合并 RUN、清理缓存）
- 知道如何支持中文字体（POI/EasyExcel 导出）
- 能针对 Spring Boot 应用优化 Docker 镜像

## 📚 前置知识

- Dockerfile 基础（`05-java-docker.md`）
- JVM 内存模型（Xms/Xmx）
- 容器时区与本地化

## 1. 核心概念

### 1.1 JVM 容器化踩坑点

| 踩坑 | 现象 | 解决方案 |
|------|------|---------|
| 容器内中文乱码 | 导出 Excel/IO 异常 | 基础镜像加 CJK 字体 |
| 时区错乱 | 日志时间相差 8 小时 | `ENV TZ=Asia/Shanghai` |
| 随机数慢 | Tomcat 启动 30s+ | `-Djava.security.egd=file:/dev/./urandom` |
| 内存超限 | OOMKilled | JVM 加 `-XX:MaxRAMPercentage` |
| 镜像过大 | 拉取慢、占空间 | 多阶段构建 + 清理 apt 缓存 |

### 1.2 JVM 内存与容器内存

```bash
# 容器限制 1G 内存
docker run -m 1g ...

# 推荐 JVM 参数（自适应）
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0"
# 让 JVM 最多使用容器内存的 75%
```

**比硬编码 `-Xmx512m` 更灵活**：
- 容器扩缩容时 JVM 自动跟随
- 避免"容器 2G 但 JVM 只用 512M"的浪费

### 1.3 镜像层合并原则

```dockerfile
# ❌ 错误：每行 RUN 都是一个层
RUN apt-get update
RUN apt-get install -y fonts-noto-cjk
RUN apt-get clean

# ✅ 正确：合并到一行 + 清理缓存
RUN apt-get update && \
    apt-get install -y --no-install-recommends fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/*
```

**关键**：
- `--no-install-recommends`：不装推荐包，减小体积
- `rm -rf /var/lib/apt/lists/*`：删除 apt 缓存（每行 RUN 完成后缓存占用 ~100MB）

## 2. 代码示例

### 2.1 支持中文的 Java 镜像

```dockerfile
FROM eclipse-temurin:8-jre

# 时区 + 字体
ENV TZ=Asia/Shanghai
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tzdata \
        fontconfig \
        fonts-noto-cjk && \
    ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo ${TZ} > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_OPTS="-Xms512m -Xmx512m -XX:MaxRAMPercentage=75.0"
WORKDIR /app
COPY target/app.jar app.jar
EXPOSE 8080
CMD java ${JAVA_OPTS} -jar app.jar
```

**说明**：
- `fonts-noto-cjk`：思源黑体，支持中/日/韩文
- `tzdata` + 软链 `/etc/localtime`：让 JVM 读到正确的时区
- `rm -rf /var/lib/apt/lists/*`：必须在同一 RUN 内删除

### 2.2 JVM 容器感知参数

```bash
# 完整推荐参数
JAVA_OPTS="
  -XX:MaxRAMPercentage=75.0       # 最大堆占容器内存的 75%
  -XX:InitialRAMPercentage=50.0   # 初始堆占 50%
  -XX:+UseG1GC                    # 使用 G1 垃圾收集器
  -XX:+HeapDumpOnOutOfMemoryError # OOM 时生成堆转储
  -XX:HeapDumpPath=/tmp/dump.hprof
  -Djava.security.egd=file:/dev/./urandom  # 解决启动慢
"
```

## 3. ruoyi 仓库源码解读

### 3.1 yudao-server Dockerfile

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 1-24）：

```dockerfile
## AdoptOpenJDK 停止发布 OpenJDK 二进制，而 Eclipse Temurin 是它的延伸，提供更好的稳定性
## 感谢复旦核博士的建议！灰子哥，牛皮！
FROM eclipse-temurin:8-jre

## 创建目录，并使用它作为工作目录
RUN mkdir -p /yudao-server
WORKDIR /yudao-server
## 将后端项目的 Jar 文件，复制到镜像中
COPY ./target/yudao-server.jar app.jar

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
- 第 3 行：`FROM eclipse-temurin:8-jre` — Eclipse 维护的 JRE 8 镜像
- 第 6-7 行：创建工作目录
- 第 9 行：复制 jar（重命名为 `app.jar`）
- 第 12 行：`ENV TZ=Asia/Shanghai` — 设置时区
- 第 14 行：`JAVA_OPTS` 包含 `Xms/Xmx`（固定内存）和 `egd`（解决启动慢）
  - **未使用 `MaxRAMPercentage`**：是改进点
- 第 23 行：`CMD java ${JAVA_OPTS} -jar app.jar $ARGS` — 启动命令

### 3.2 deploy.sh 的 JVM 参数

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 17-26）：

```bash
# heapError 存放路径
HEAP_ERROR_PATH=$BASE_PATH/heapError
# JVM 参数
JAVA_OPS="-Xms512m -Xmx512m -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=$HEAP_ERROR_PATH"

# SkyWalking Agent 配置
#export SW_AGENT_NAME=$SERVER_NAME
#export SW_AGENT_COLLECTOR_BACKEND_SERVICES=192.168.0.84:11800
#export SW_GRPC_LOG_SERVER_HOST=192.168.0.84
#export SW_AGENT_TRACE_IGNORE_PATH="Redisson/PING,/actuator/**,/admin/**"
#export JAVA_AGENT=-javaagent:/work/skywalking/apache-skywalking-apm-bin/agent/skywalking-agent.jar
```

**解读**：
- 第 4 行：`JAVA_OPS`（不是 `JAVA_OPTS`）— 注意拼写差异
- 第 4 行：包含 `HeapDumpOnOutOfMemoryError` 和 `HeapDumpPath`
  - OOM 时自动生成 `heapError/xxx.hprof` 堆转储
- 第 11 行：`JAVA_AGENT` 注释用于挂载 SkyWalking agent
- **设计意图**：部署脚本是 JVM 调优和链路追踪的统一入口

## 4. 关键要点总结

- 基础镜像选 `eclipse-temurin:8-jre`（推荐）或 `openjdk:8-jre-slim`
- 时区设置 `ENV TZ=Asia/Shanghai` + 软链 `/etc/localtime`
- 解决启动慢：`-Djava.security.egd=file:/dev/./urandom`
- 容器感知内存：`-XX:MaxRAMPercentage=75.0` 优于硬编码 `-Xmx`
- OOM 自动堆转储：`-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=...`
- 合并 RUN 减少层数 + 清理 apt 缓存减小体积

## 5. 练习题

### 练习 1：基础（必做）

修改 `yudao-server/Dockerfile` 加入 `apt-get install fonts-noto-cjk`，重建镜像，在容器内执行 `fc-list :lang=zh` 验证中文字体是否安装成功。

### 练习 2：进阶

把硬编码的 `-Xms512m -Xmx512m` 改为 `-XX:MaxRAMPercentage=75.0 -XX:InitialRAMPercentage=50.0`，用 `docker run -m 1g` 启动，观察容器内 `jcmd <pid> VM.native_memory` 输出的内存分配。

### 练习 3：挑战（选做）

写一个脚本，故意在 Spring Boot 应用内 `new byte[Integer.MAX_VALUE]` 触发 OOM，验证 ruoyi 的 `-XX:HeapDumpOnOutOfMemoryError` 是否生成堆转储，并用 `jhat` 或 `VisualVM` 分析。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- [Eclipse Temurin 镜像](https://hub.docker.com/_/eclipse-temurin)
- [JVM Container Awareness](https://developers.redhat.com/articles/2022/04/19/java-17-vs-java-8-container-memory)
- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
