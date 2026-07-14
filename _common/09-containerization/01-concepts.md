# 9.1 Docker 核心概念：镜像 / 容器 / 层

> 理解 Docker 三大核心对象：镜像（Image）、容器（Container）、仓库（Registry），并理解分层文件系统。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分镜像、容器、仓库三种对象的关系
- 理解 Docker 分层文件系统（UnionFS）的工作原理
- 解释 `docker run` 时镜像层是如何被复用的
- 能看懂 dify 与 ruoyi 项目中 Docker 镜像的实际结构

## 📚 前置知识

- Linux 基本命令行（`ls`、`cd`、`ps`）
- 进程与文件系统的基本概念

## 1. 核心概念

### 1.1 三个核心对象

| 对象 | 类比 | 特点 | 状态 |
|------|------|------|------|
| **镜像（Image）** | 类的定义 / 安装包 | 只读、分层、可分发 | 静态 |
| **容器（Container）** | 类的实例 / 运行中程序 | 在镜像之上加可写层 | 动态 |
| **仓库（Registry）** | GitHub / 应用商店 | 存储和分发镜像 | 中心化 |

```
Docker Hub (Registry)
   └── langgenius/dify-api:1.6.0  (Image, 只读分层)
          ├── ubuntu:22.04       (Layer 1)
          ├── python:3.12-slim   (Layer 2)
          ├── apt install ...    (Layer 3)
          └── COPY api/          (Layer 4)
                ↓ 启动
          dify-api-container     (Container, 增加可写层)
```

### 1.2 分层文件系统（UnionFS / OverlayFS）

Docker 镜像由**只读的堆叠层**组成，容器启动时会在最上层添加一个**可写层**（thin R/W layer）。这就是 UnionFS（联合文件系统）的核心思想。

**关键特性**：
- **Copy-on-Write**：容器修改文件时，先把只读层的文件复制到可写层，再修改
- **层共享**：多个镜像可以共享相同的基础层（节省磁盘）
- **镜像复用**：拉取 `python:3.12-slim` 镜像时，如果本机已有该层，则秒级完成

**对部署的意义**：修改一行代码不需要重新下载整个镜像，只需要重建最上层的应用代码层——这就是 Docker 部署相比虚拟机部署的**核心优势**。

### 1.3 镜像与容器的关系

```bash
# 查看镜像
docker images

# 查看容器
docker ps -a

# 运行容器（从镜像创建实例）
docker run -d --name my-api langgenius/dify-api:1.6.0

# 进入运行中的容器
docker exec -it my-api bash
```

**容器 = 镜像 + 运行时配置 + 可写层**

### 1.4 镜像命名规范

`registry/repo:tag`，例如 `langgenius/dify-api:1.6.0`：
- `langgenius` = 仓库命名空间（通常是组织或用户名）
- `dify-api` = 镜像名
- `1.6.0` = 标签（默认 `latest`，建议生产用具体版本）

## 2. 代码示例

### 2.1 镜像拉取、运行、查看

```bash
# 1. 拉取镜像（Ubuntu 官方镜像）
docker pull ubuntu:22.04

# 2. 查看本地镜像层信息
docker history ubuntu:22.04

# 3. 启动容器并进入交互式 Shell
docker run -it --name demo ubuntu:22.04 bash

# 4. 在容器内修改一个文件
root@abc123:/# echo "hello from container" > /tmp/test.txt
root@abc123:/# cat /tmp/test.txt
hello from container

# 5. 退出容器（在另一个终端查看）
docker ps -a                # 查看状态（Exited）
docker start demo           # 重新启动
docker attach demo          # 重新进入

# 6. 删除容器（容器内的修改不会影响镜像）
docker rm demo
```

### 2.2 镜像构建（简化版）

```dockerfile
# 文件：Dockerfile.simple
FROM ubuntu:22.04              # 基础层
RUN apt-get update && \        # 新层（安装 curl）
    apt-get install -y curl
COPY hello.sh /hello.sh        # 新层（复制脚本）
RUN chmod +x /hello.sh         # 新层（修改权限）
CMD ["/hello.sh"]              # 元数据（不增加层大小）
```

```bash
docker build -f Dockerfile.simple -t myapp:1.0 .
docker run myapp:1.0
```

每一条 `RUN` / `COPY` 都会在镜像中新增一个只读层，**但不影响镜像运行**——这意味着你可以在不改变最终运行环境的前提下，频繁重建镜像。

### 2.3 常见错误：把容器当镜像使用

```bash
# ❌ 错误：把容器改动 commit 成新镜像
# 这种"手工镜像"无法追溯、无法复用、不能跨环境
docker commit my-container myapp:custom

# ✅ 正确：把改动写进 Dockerfile，重新 build
# Dockerfile 中体现"声明式"的镜像构建
docker build -t myapp:1.1 .
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify API 镜像的多阶段构建

**文件位置**：`/Users/xu/code/github/dify/api/Dockerfile`
**核心代码**（行 1-12，32-45）：

```dockerfile
# base image
FROM python:3.12-slim-bookworm AS base

WORKDIR /app/api

# Install uv
ENV UV_VERSION=0.8.9

RUN pip install --no-cache-dir uv==${UV_VERSION}

# if you located in China, you can use aliyun mirror to speed up
# RUN sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
          # basic environment
          git g++ \
          # for building gmpy2
          libmpfr-dev libmpc-dev
```

**解读**：
- 第 2 行：`FROM python:3.12-slim-bookworm AS base`——debian-slim 是精简的基础镜像，每一行 RUN 都是新的只读层
- 第 9 行：`pip install uv`——比直接用 pip 同步依赖快 10-100 倍
- 第 17-22 行：一个 `RUN` 命令装多个依赖包可以减少层数（每多一层都会让镜像膨胀）
- 第 18-22 行的注释：`--no-install-recommends` 跳过可选依赖，进一步减小层大小

### 3.2 ruoyi JVM 镜像：精简到极致

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
**核心代码**（行 1-23）：

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
- 第 3 行：`eclipse-temurin:8-jre`——**只含 JRE，不含 JDK**，相比 JDK 镜像体积小约 200MB
- 第 9 行：`COPY ./target/yudao-server.jar app.jar`——只复制 jar（几十 MB），不复制源码
- 第 14 行：通过 `ENV JAVA_OPTS` 暴露 JVM 参数，运行容器时可以 `docker run -e "JAVA_OPTS=-Xmx2g"` 覆盖
- 第 23 行：`CMD` 是默认启动命令，可以在运行时被 `docker run yudao-server java -Xmx1g -jar app.jar` 覆盖

**对比**：dify 用多阶段构建是为了把 Python 依赖与运行时分离；ruoyi 用单阶段是因为 JVM 应用天然"编译产物 = jar"非常小，不需要分阶段。

## 4. 关键要点总结

- **镜像**（只读、分层）vs **容器**（运行实例 + 可写层）
- **分层存储**：每条 `RUN` / `COPY` 是新的一层，层可共享、不可改
- **Copy-on-Write**：修改文件时才把只读层文件复制到可写层
- **声明式 vs 命令式**：始终用 Dockerfile 重建镜像，不要 `docker commit`
- **生产建议**：tag 必须用具体版本（如 `1.6.0`），**禁止**用 `latest`
- **JVM 镜像选择**：生产用 `-jre`（小），开发可用 `-jdk`（大）

## 5. 练习题

### 练习 1：基础（必做）

在不依赖 Docker 的情况下，画出 `dify/api/Dockerfile` 的镜像分层结构图，标注每层的来源（基础层 / apt / pip / 源码）。

**参考答案**：见 `solutions/01-docker-layers.md`

### 练习 2：进阶

观察 `ruoyi-vue-pro/yudao-server/Dockerfile`，回答：
1. 这个镜像一共有多少层？
2. 如果改了 `JAVA_OPTS` 环境变量，**是否需要重新 build 镜像**？
3. 如果只想改 `yudao-server.jar` 的版本，应当如何最小化重建成本？

### 练习 3：挑战（选做）

阅读 `api/Dockerfile` 的 production 阶段（第 32-126 行），找出所有"为了减小镜像体积"的优化措施（至少列 5 个）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/Dockerfile`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- Docker 官方文档：https://docs.docker.com/get-started/overview/
- UnionFS / OverlayFS 原理：https://docs.docker.com/storage/storagedriver/overlayfs-driver/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
