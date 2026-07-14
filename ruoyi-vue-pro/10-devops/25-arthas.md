# 6.2 Arthas 线上诊断

> 理解 Arthas 在线诊断工具的核心能力，掌握生产环境排查问题的实战方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Arthas 的核心命令（dashboard、thread、watch、trace）
- 掌握在线排查慢方法、热更新代码、查看调用栈
- 能在 ruoyi 容器内挂载 Arthas
- 知道生产环境的安全使用规范

## 📚 前置知识

- Java 基础
- JVM 工具（jstack / jmap / jstat）
- Docker 基础

## 1. 核心概念

### 1.1 为什么需要 Arthas？

生产环境问题排查的痛点：
- ❌ 不能重启（重启会丢现场）
- ❌ 看不到方法入参和返回值
- ❌ 不好定位慢 SQL / 慢方法
- ❌ 没有 IDE 调试

**Arthas（阿尔萨斯）** 是 Alibaba 开源的 Java 诊断工具：
- **无需重启** — 运行时 attach 到 Java 进程
- **动态查看** — 方法入参、返回值、异常、调用栈
- **热更新** — 反编译 + 在线修改代码（jad / redefine）
- **性能分析** — 找出最耗时的方法

### 1.2 核心概念

| 概念 | 含义 |
|------|------|
| **Attach** | 附加到目标 JVM 进程 |
| **Dashboard** | 实时仪表盘（线程 / 内存 / GC） |
| **Watch** | 观测方法（入参 / 返回值 / 异常） |
| **Trace** | 追踪方法调用链和耗时 |
| **Jad** | 反编译 class |
| **Redefine** | 热更新（在线修改代码） |
| **Profiler** | 火焰图分析 |

## 2. 代码示例

### 2.1 启动 Arthas

```bash
# 1. 下载 Arthas
curl -O https://arthas.aliyun.com/arthas-boot.jar

# 2. 运行（attach 到 Java 进程）
java -jar arthas-boot.jar

# 看到进程列表，输入序号选择目标进程
[INFO] Found existing java process, please choose one and input the serial number of the process to attach.
  [1]: 1234 yudao-server
```

### 2.2 Dashboard 实时监控

```bash
dashboard
# 输出：线程状态、CPU、内存、GC 情况
```

### 2.3 Thread 查看线程

```bash
# 找出阻塞线程
thread -b

# 找出 CPU 占用最高的线程
thread -n 3

# 查看指定线程栈
thread <thread-id>
```

### 2.4 Watch 监控方法

```bash
# 监控 OrderService.createOrder 的入参和返回值
watch cn.iocoder.yudao.module.trade.service.OrderService createOrder '{params, returnObj, throwExp}' -x 2
```

**说明**：
- `{params, returnObj, throwExp}` — 观察入参、返回值、异常
- `-x 2` — 遍历深度 2（默认值是 1）

### 2.5 Trace 追踪调用链

```bash
# 追踪 controller 方法调用链和耗时
trace cn.iocoder.yudao.module.trade.controller.OrderController createOrder '#cost > 50'
```

**说明**：`#cost > 50` 只显示耗时 > 50ms 的调用。

### 2.6 热更新代码

```bash
# 1. 反编译类
jad cn.iocoder.yudao.module.system.service.UserService getUser

# 2. 修改后编译
# ... (保存到 /tmp/UserService.java)

# 3. 编译
mc /tmp/UserService.java -d /tmp

# 4. 重新定义类
redefine /tmp/cn/iocoder/yudao/module/system/service/UserService.class
```

**注意**：
- 只能修改**方法体**，不能改方法签名、字段
- 热更新的代码在进程重启后失效

## 3. ruoyi 仓库源码解读

**注**：ruoyi 仓库**没有内置 Arthas 集成**，需要自己挂载。

### 3.1 推荐的 Arthas 集成方案

**Dockerfile 修改**：

```dockerfile
# 在 yudao-server/Dockerfile 中添加
RUN mkdir -p /opt/arthas
# 下载 Arthas
RUN curl -L -o /opt/arthas/arthas-boot.jar https://arthas.aliyun.com/arthas-boot.jar
```

### 3.2 进入容器使用 Arthas

```bash
# 1. 进入 yudao-server 容器
docker exec -it yudao-server bash

# 2. 启动 Arthas
cd /opt/arthas
java -jar arthas-boot.jar
# 选择 yudao-server 进程

# 3. 开始诊断
dashboard
trace cn.iocoder.yudao.module.system.controller.UserController getInfo
```

### 3.3 通过 docker-compose 挂载

**docker-compose.yml 修改**：

```yaml
  server:
    image: yudao-server
    volumes:
      - ./arthas-boot.jar:/opt/arthas/arthas-boot.jar
    command: ["sh", "-c", "java ${JAVA_OPTS} -jar app.jar & sleep infinity"]
```

**说明**：
- `sleep infinity` — 保持容器运行（避免主进程退出后容器停止）
- 用 `docker exec` 进入容器后再启动 Arthas

### 3.4 ruoyi 推荐的常用命令

**业务追踪（基于 ruoyi 的包名）**：

```bash
# 监控登录接口
watch cn.iocoder.yudao.module.system.controller.AuthController login '{params, returnObj}' -x 3

# 追踪订单创建
trace cn.iocoder.yudao.module.trade.service.OrderService createOrder

# 找出最慢的 3 个方法
profiler start --event cpu
profiler stop --format html > /tmp/flame.html  # 火焰图
```

**内存诊断**：

```bash
# 查看 dashboard
dashboard

# 查看内存中最大的对象
memory

# 强制 Full GC
vmtool --action forceGc
```

## 4. 关键要点总结

- Arthas 是 Alibaba 开源的 Java 诊断工具，**运行时 attach**，无需重启
- 核心命令：`dashboard` / `thread` / `watch` / `trace` / `jad` / `redefine`
- `watch` 看入参和返回值，`trace` 看调用链耗时
- **热更新**只能改方法体，重启后失效
- ruoyi 集成：Dockerfile 下载 arthas-boot.jar，`docker exec` 进入容器使用
- 生产环境**只读模式**（只看不改）避免误操作
- 输出火焰图：`profiler start` → `profiler stop --format html`

## 5. 练习题

### 练习 1：基础（必做）

下载 Arthas 启动，attach 到本地 yudao-server 进程，执行 `dashboard`、`thread -n 3`、`thread -b` 命令，观察输出。

### 练习 2：进阶

在 yudao-server 中选一个 Service 方法，用 `watch` 观察入参和返回值，故意构造异常触发，用 `trace` 查看完整的调用链。

### 练习 3：挑战（选做）

用 `profiler start` 录制 30 秒性能数据，生成火焰图，分析 ruoyi 启动时最耗时的方法，写一份优化建议报告。

## 6. 参考资料

- [Arthas 官方文档](https://arthas.aliyun.com/)
- [Arthas 实战教程](https://github.com/alibaba/arthas/wiki)
- ruoyi 部署文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
