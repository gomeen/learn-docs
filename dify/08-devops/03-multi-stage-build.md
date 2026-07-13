# 1.3 多阶段构建：减小镜像体积

> 掌握 Docker 多阶段构建，让最终镜像只包含运行所需的最小文件集。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多阶段构建的原理与价值
- 用 `COPY --from=` 在阶段间传递构建产物
- 能看懂 dify 的 `api/Dockerfile` 中 `base` / `packages` / `production` 三阶段的设计

## 📚 前置知识

- `08-devops/01-docker-concepts.md`
- `08-devops/02-dockerfile.md`

## 1. 核心概念

### 1.1 什么是多阶段构建？

多阶段构建是在**一个 Dockerfile 中**使用多个 `FROM` 指令，每个 `FROM` 开启一个**独立的构建阶段**。前阶段的产物可以选择性复制到后阶段。

**单阶段问题**：
- 构建工具（编译器、构建依赖）被打入最终镜像
- 镜像包含源代码、中间文件
- 镜像体积大、安全风险高

### 1.2 多阶段的核心机制

```dockerfile
# 阶段 1：构建（用大镜像）
FROM golang:1.22 AS builder
WORKDIR /src
COPY . .
RUN go build -o app      # 编译产物在 /src/app

# 阶段 2：运行（用小镜像）
FROM alpine:3.20
COPY --from=builder /src/app /app   # 只复制二进制
CMD ["/app"]
```

**关键点**：
- `AS <name>` 给阶段命名，方便 `COPY --from=` 引用
- 每个阶段是**独立的文件系统视图**，互不污染
- 最终镜像只包含**最后一个阶段**的文件
- 未被引用的阶段**不会进入最终镜像**

### 1.3 典型价值

| 维度 | 单阶段 | 多阶段 |
|------|--------|--------|
| 镜像体积 | 大（含编译器） | 小（仅运行时） |
| 安全 | 攻击面大 | 攻击面小 |
| 构建缓存 | 难以复用 | 可分别缓存 |
| 可读性 | 一般 | 阶段分明 |

## 2. 代码示例

### 2.1 反例：单阶段把编译器也装进镜像

```dockerfile
# ❌ 反例：GCC 进入最终镜像（增加 ~500MB）
FROM python:3.12
RUN apt-get update && apt-get install -y gcc     # 编译器
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt              # 编译 numpy/pandas 等
COPY . .
CMD ["python", "app.py"]
```

最终镜像包含 gcc 编译器、构建依赖、apt 缓存，但运行时根本不需要。

### 2.2 正例：多阶段构建

```dockerfile
# ✅ 正例：构建与运行分离
# Stage 1: builder
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt \
    && find /root/.local -name "__pycache__" -type d | xargs rm -rf

# Stage 2: runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

**收益**：构建阶段有 gcc 编译 C 扩展，运行阶段只复制已编译好的 `.so` / `.pyc`，镜像可减小 30%-50%。

### 2.3 选择性复制：用 `--from`

```dockerfile
# 从指定阶段复制
COPY --from=builder /app/build/output /app/

# 从外部镜像复制（可用于借用工具）
COPY --from=alpine:3.20 /etc/os-release /tmp/

# 用阶段编号（不需要 AS 命名）
COPY --from=0 /app/build /app/
```

## 3. dify 仓库源码解读

### 3.1 dify 的三阶段 Dockerfile

**文件位置**：`/Users/xu/code/github/dify/api/Dockerfile`
**核心代码**（行 1-43）：

```dockerfile
# base image
FROM python:3.12-slim-bookworm AS base

WORKDIR /app/api

# Install uv
ENV UV_VERSION=0.8.9

RUN pip install --no-cache-dir uv==${UV_VERSION}


FROM base AS packages

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
          git g++ \
          libmpfr-dev libmpc-dev

# Install Python dependencies (workspace members under providers/vdb/)
COPY api/pyproject.toml api/uv.lock ./
COPY api/providers ./providers
COPY dify-agent/pyproject.toml dify-agent/README.md /app/dify-agent/
COPY dify-agent/src /app/dify-agent/src
RUN uv sync --frozen --no-dev --no-editable

# production stage
FROM base AS production

ENV FLASK_APP=app.py
ENV EDITION=SELF_HOSTED
ENV DEPLOY_ENV=PRODUCTION
ENV CONSOLE_API_URL=http://127.0.0.1:5001

EXPOSE 5001
```

**解读**：
- 第 2 行：`AS base` 阶段只装 `uv`（轻量），所有后续阶段共享
- 第 12 行：`FROM base AS packages` 装编译工具（`g++` `libmpfr-dev`）和 Python 依赖
- 第 33 行：`FROM base AS production` 重用 base，**故意不继承 packages 阶段**，避免把 `g++` 带入最终镜像
- 第 23 行：`uv sync --frozen --no-dev` 编译期需要，装包后会得到编译好的 wheel
- **镜像瘦身技巧**：后续会从 `packages` 阶段 `COPY --from=packages` 复制已编译好的 `.venv`，**但 `g++` 留在 packages 阶段不进 production**

### 3.2 阶段间复制：虚拟环境

**文件位置**：`/Users/xu/code/github/dify/api/Dockerfile`
**核心代码**（行 97-100）：

```dockerfile
# Copy Python environment and packages
ENV VIRTUAL_ENV=/app/api/.venv
COPY --from=packages --chown=dify:dify ${VIRTUAL_ENV} ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
```

**解读**：
- 第 3 行：`COPY --from=packages` 从 packages 阶段复制整个虚拟环境（约几百 MB 的包）
- `--chown=dify:dify` 复制时直接修改文件属主，避免后续 `chown` 产生新层
- 第 4 行：把 venv 的 `bin` 加到 `PATH`，后续 `RUN python` 自动用 venv 里的解释器
- **关键设计**：production 阶段镜像**不包含** `g++` `libmpfr-dev` 等编译工具，但**包含**编译好的包

## 4. 关键要点总结

- 多阶段构建用**多个 `FROM`**，每个阶段独立文件系统
- 用 `COPY --from=<阶段名>` 在阶段间传递产物
- **最终镜像只包含最后一个阶段**的文件
- dify 的三阶段：`base`（uv 工具）→ `packages`（装编译工具+Python 依赖）→ `production`（仅运行时）
- 阶段间复制时配合 `--chown` 避免后续 `chown` 多余层

## 5. 练习题

### 练习 1：基础（必做）

为以下需求写多阶段 Dockerfile：编译一个 Go 程序，构建阶段用 `golang:1.22`，运行阶段用 `alpine:3.20`，最终镜像只包含编译好的二进制。

### 练习 2：进阶

阅读 dify `api/Dockerfile`，比较如果把 `packages` 阶段合并到 `production` 阶段，最终镜像会增大多少？哪些包是不必要的？

### 练习 3：挑战（选做）

用 `docker history langgenius/dify-api:1.16.0-rc1` 查看镜像各层大小，定位最大的几层，思考如何进一步瘦身。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/Dockerfile`
- Docker 多阶段构建官方文档：https://docs.docker.com/build/building/multi-stage/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
