# 9.2 Dockerfile 编写最佳实践

> 学习如何写出**安全、体积小、构建快、可缓存**的 Dockerfile，能直接对照改造 dify 与 ruoyi 的镜像。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解**构建缓存**（Build Cache）的命中规则，写出高效的 Dockerfile
- 应用常见最佳实践（缓存、`--no-install-recommends`、非 root 用户、`exec` 形式 `ENTRYPOINT`）
- 看懂 dify `/api/Dockerfile` 的多阶段缓存策略
- 看懂 ruoyi `/yudao-server/Dockerfile` 的 JVM 参数注入设计

## 📚 前置知识

- [9.1 Docker 核心概念](./01-concepts.md)：镜像 / 容器 / 层
- Shell 基础、apt 或 yum 包管理
- 多阶段构建见 [03-multi-stage](./03-multi-stage.md)

## 1. 核心概念

### 1.1 构建缓存（Build Cache）

Docker 顺序执行 Dockerfile 中的每条指令时，**会对比当前指令的参数与上次构建是否一致**。如果一致，就复用上次的镜像层，跳过该指令的执行。这就是"缓存命中"。

**匹配规则**：
- `RUN apt-get install curl`：只要字符串完全相同就命中（哪怕只是为了命中而复制粘贴）
- `COPY api/ ./api/`：**只要文件内容或路径未变就命中**
- `ADD https://x.com/file.tar /app/`：**几乎不命中**（每次下载内容不同）

### 1.2 缓存的"破坏者"

任何**顺序靠后但失效的指令**，会导致后续所有层都失效。

```dockerfile
# ❌ 反面教材：COPY 整个源码 → 改一行就全失效
COPY . /app
RUN pip install -r /app/requirements.txt

# ✅ 正解：先 COPY 依赖清单，再装依赖，最后 COPY 源码
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt   # 这一层缓存长期命中
COPY . /app                                # 这一层每次重建
```

### 1.3 体积优化核心原则

1. **选择最小的基础镜像**（`slim` / `-alpine` / `-jre`）
2. **合并 `RUN` 命令**（一条 `RUN` = 一个层）
3. **清理缓存**：`apt-get install` 后 `rm -rf /var/lib/apt/lists/*`
4. **多阶段构建**：编译产物只取最终可执行物
5. **使用 `.dockerignore`**：避免无关文件进入构建上下文

### 1.4 安全实践

1. **非 root 用户运行**：避免容器逃逸后直接获得 root
2. **固定基础镜像版本**：禁用 `latest`
3. **不要把密钥写入镜像**
4. **多阶段构建**：构建工具不出现在最终镜像

## 2. 代码示例

### 2.1 标准 Python Dockerfile

```dockerfile
# 文件：Dockerfile.python-best
# 1. 固定版本：小且具体
FROM python:3.12-slim-bookworm

# 2. 设置环境变量（全局缓存生效）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 3. 先单独装系统依赖（缓存层）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 4. 利用层缓存：requirements 没变就不重新装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 最后才复制源码（最大变动部分）
COPY . .

# 6. 切换到非 root 用户
RUN useradd -m -u 1001 app && chown -R app:app /app
USER app

# 7. exec 形式 ENTRYPOINT（能被 docker run 参数覆盖）
ENTRYPOINT ["python", "main.py"]
```

### 2.2 常见错误：层数膨胀

```dockerfile
# ❌ 错误：每条 RUN 单独一层，镜像 800MB
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y vim
RUN apt-get install -y git
RUN rm -rf /var/lib/apt/lists/*

# ✅ 正确：合并到一条 RUN，体积 400MB
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl vim git && \
    rm -rf /var/lib/apt/lists/*
```

### 2.3 常见错误：COPY 顺序错误

```dockerfile
# ❌ 错误：源码变动导致依赖层全部重装
COPY . .
RUN pip install -r requirements.txt   # 永远不命中缓存

# ✅ 正确：先 COPY 依赖清单
COPY requirements.txt .
RUN pip install -r requirements.txt   # 命中缓存
COPY . .                              # 仅这一层重建
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：先 COPY 依赖清单再装包

**文件位置**：`/Users/xu/code/github/dify/api/Dockerfile`
**核心代码**（行 25-30）：

```dockerfile
# Install Python dependencies (workspace members under providers/vdb/)
COPY api/pyproject.toml api/uv.lock ./
COPY api/providers ./providers
COPY dify-agent/pyproject.toml dify-agent/README.md /app/dify-agent/
COPY dify-agent/src /app/dify-agent/src
# Trust the checked-in lock during image builds; local path sources are copied from the repository context.
RUN uv sync --frozen --no-dev --no-editable
```

**解读**：
- 第 25 行：`COPY pyproject.toml uv.lock ./`——**先把锁定文件复制进来**。这是分层缓存的关键
- 第 26 行：`COPY api/providers ./providers`——因为本地 path 依赖，必须 copy
- 第 30 行：`uv sync --frozen`——严格按 `uv.lock` 安装，禁止自动更新依赖（保证可复现性）
- 第 30 行：`--no-dev`——不装开发依赖，减小镜像体积
- 第 30 行：`--no-editable`——安装到 site-packages 而非 develop 模式

**优化点**：如果哪天 `pyproject.toml` 不变，光改源码就不需要重新跑 `uv sync`——这就是分层缓存的价值。

### 3.2 dify：创建非 root 用户并切换

**文件位置**：`/Users/xu/code/github/dify/api/Dockerfile`
**核心代码**（行 55-62，113-125）：

```dockerfile
# Create non-root user
ARG dify_uid=1001
ARG NODE_MAJOR=22
ARG NODE_PACKAGE_VERSION=22.21.0-1nodesource1
ARG NODESOURCE_KEY_FPR=6F71F525282841EEDAF851B42F59B5F99B1BE0B4
RUN groupadd -r -g ${dify_uid} dify && \
    useradd -r -u ${dify_uid} -g ${dify_uid} -s /bin/bash dify && \
    chown -R dify:dify /app

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
```

**解读**：
- 第 56 行：`ARG dify_uid=1001`——通过构建参数传 UID，方便在不同环境调整
- 第 60-62 行：`groupadd` + `useradd`——dify 自建非 root 账户
- 第 124 行（后文）：`USER dify`——**关键**：切换到非 root 用户后再启动应用

**为什么必须 non-root？** 如果容器逃逸（breakout），攻击者只能拿到普通用户权限，而不是 root。

### 3.3 ruoyi：通过 ENV 注入 JVM 参数

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
- 第 14 行：`ENV JAVA_OPTS="-Xms512m -Xmx512m ..."`——**默认值**。注意 `JAVA_OPTS` 暴露给运行时，覆盖无需重建镜像
- 第 17 行：`ENV ARGS=""`——分隔 JVM 参数和应用参数（`--spring.profiles.active=prod` 等）
- 第 23 行：`CMD java ${JAVA_OPTS} -jar app.jar $ARGS`——Shell 形式，会执行变量展开

**运行期覆盖示例**（无需重新 build）：

```bash
docker run -e "JAVA_OPTS=-Xmx2g -XX:+UseG1GC" \
           -e "ARGS=--spring.profiles.active=production" \
           -p 48080:48080 yudao-server
```

**对比 dify 的设计**：dify 的 `Dockerfile` 直接 `ENV CONSOLE_API_URL=...` 写死默认值，但允许 `environment` 段在 compose 时覆盖；ruoyi 因为是单 jar，更倾向于在镜像层留 `JAVA_OPTS` 占位。

## 4. 关键要点总结

- **缓存顺序**：变化的代码放最后，稳定的依赖放前面
- **合并 RUN + 清理缓存**：`apt-get install ... && rm -rf /var/lib/apt/lists/*`
- **非 root 用户**：`USER` 切换是生产环境强制要求
- **ENV vs ARG**：ARG 只在 build 期生效，ENV 在运行期生效
- **exec 形式 CMD**：`CMD ["python", "main.py"]` 而非 `CMD python main.py`（后者启动 shell 接收信号，不优雅）
- **JVM 应用**：`-jre` 而非 `-jdk`；`JAVA_OPTS` 通过环境变量注入

## 5. 练习题

### 练习 1：基础（必做）

改正以下 Dockerfile 的所有问题（至少 5 个）：

```dockerfile
FROM python:latest
RUN apt-get update
RUN apt-get install -y gcc
RUN pip install flask
COPY . /app
WORKDIR /app
RUN useradd -m app
USER app
CMD python /app/main.py
```

**参考答案**：见 `solutions/01-fix-dockerfile.md`

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/Dockerfile` 全文（第 32-126 行 production 阶段），列出至少 5 处体现"最佳实践"的设计选择。

### 练习 3：挑战（选做）

重写 `ruoyi-vue-pro/yudao-server/Dockerfile`，加入：
- 多阶段构建（先 maven 编译，再只 copy jar 到运行时镜像）
- 非 root 用户
- 健康检查（`HEALTHCHECK`）

写完后估算改动前后镜像体积的差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/Dockerfile`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/Dockerfile`
- Dockerfile 官方最佳实践：https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
- 多阶段构建：https://docs.docker.com/build/building/multi-stage/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
