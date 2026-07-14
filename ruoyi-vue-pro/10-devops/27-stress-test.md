# 6.4 压测：JMeter / Gatling

> 理解性能压测的核心指标与工具，掌握 JMeter / Gatling 对 Spring Boot 应用进行压力测试。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解压测核心指标（TPS / RT / 错误率）
- 掌握 JMeter 编写压测脚本
- 掌握 Gatling 编写压测脚本
- 能对 ruoyi 进行简单的压力测试

## 📚 前置知识

- HTTP 协议
- 性能测试基础概念
- `01-maven-build.md`

## 1. 核心概念

### 1.1 压测的核心指标

| 指标 | 含义 | 目标 |
|------|------|------|
| **TPS** | Transactions Per Second | 越高越好 |
| **QPS** | Queries Per Second | 类似 TPS |
| **RT** | Response Time（响应时间） | 越低越好 |
| **P99** | 99% 请求的响应时间 | 通常 < 500ms |
| **错误率** | 失败请求比例 | < 0.1% |
| **并发数** | 同时在线用户 | 业务决定 |

### 1.2 压测流程

```mermaid
graph LR
    A[明确目标] --> B[编写脚本]
    B --> C[单接口冒烟]
    C --> D[阶梯加压]
    D --> E[监控性能]
    E --> F[瓶颈分析]
    F --> G[优化重测]
```

### 1.3 主流压测工具对比

| 工具 | 语言 | 优势 | 适用 |
|------|------|------|------|
| **JMeter** | Java | GUI 友好、生态丰富 | 中小型项目 |
| **Gatling** | Scala | 高性能、代码化 | 大型项目 |
| **wrk** | C | 极轻量 | 简单 HTTP 压测 |
| **Locust** | Python | 脚本化（Python） | 灵活场景 |
| **k6** | Go | 云原生友好 | DevOps 流程 |

## 2. 代码示例

### 2.1 JMeter 测试计划（HTTP Request）

**步骤**：
1. 添加 Thread Group（线程组）
   - 线程数：100
   - 循环次数：100
   - Ramp-Up：10 秒
2. 添加 HTTP Request
   - Server: `localhost`
   - Port: 48080
   - Method: GET
   - Path: `/admin-api/system/user/get`
3. 添加 Listener（查看结果）
   - View Results Tree
   - Summary Report
   - Aggregate Report

**JMeter 命令行压测**：

```bash
# 命令行模式（无 GUI，性能更好）
jmeter -n -t test-plan.jmx -l result.jtl -e -o report/

# 参数说明：
# -n: 非 GUI 模式
# -t: 测试计划文件
# -l: 结果文件
# -e -o: 生成 HTML 报告
```

### 2.2 Gatling 压测脚本（Scala）

```scala
// 文件：src/test/scala/YudaoLoadTest.scala
import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class YudaoLoadTest extends Simulation {

  val httpProtocol = http
    .baseUrl("http://localhost:48080")
    .acceptHeader("application/json")

  val scn = scenario("Yudao Login")
    .exec(http("login")
      .post("/admin-api/system/auth/login")
      .header("Content-Type", "application/json")
      .body(StringBody("""{"username":"admin","password":"admin"}"""))
      .check(status.is(200))
      .check(jsonPath("$.data.token").saveAs("token")))

  setUp(
    scn.inject(
      rampUsers(100) during (10.seconds),  // 10 秒内启动 100 用户
      constantUsersPerSec(50) during (30.seconds)  // 持续 30 秒 50 QPS
    ).protocols(httpProtocol)
  ).assertions(
    global.responseTime.percentile(99).lt(500),  // P99 < 500ms
    global.failedRequests.percent.lt(0.1)        // 错误率 < 0.1%
  )
}
```

### 2.3 wrk 极简压测

```bash
# 启动 4 个线程，持续 30 秒，超时 10 秒
wrk -t4 -c100 -d30s --timeout 10s http://localhost:48080/admin-api/system/user/get

# 输出示例：
# Running 30s test @ http://...
#   12 threads and 100 connections
#   Thread Stats   Avg      Stdev     Max   +/- Stdev
#     Latency    12.34ms   5.67ms 89.12ms   89.00%
#     Req/Sec     2.34k   567.89   3.45k    78.00%
#   90000 requests in 30.00s, 45.00MB read
# Requests/sec:   3000.00
# Transfer/sec:     1.50MB
```

## 3. ruoyi 仓库源码解读

**注**：ruoyi 仓库**没有内置压测脚本**。以下是建议的压测方案。

### 3.1 ruoyi 压测关注点

**核心接口**：

| 接口 | 路径 | 风险 |
|------|------|------|
| 登录 | `POST /admin-api/system/auth/login` | 加密、Redis 写入 |
| 用户列表 | `GET /admin-api/system/user/page` | 分页、关联查询 |
| 字典查询 | `GET /admin-api/system/dict/type/list` | 高频调用 |
| 权限验证 | `GET /admin-api/system/permission/list` | 每次请求都查 |
| 导出 | `GET /admin-api/infra/file/list` | 大数据量 |

### 3.2 推荐的压测计划

**JMeter 测试计划**（`yudao-loadtest.jmx`）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testname="Yudao 压测计划">
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments">
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testname="登录压测" enabled="true">
        <stringProp name="ThreadGroup.num_threads">100</stringProp>  <!-- 100 用户 -->
        <stringProp name="ThreadGroup.ramp_time">10</stringProp>     <!-- 10 秒启动 -->
        <stringProp name="ThreadGroup.duration">60</stringProp>     <!-- 持续 60 秒 -->
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
      </ThreadGroup>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

### 3.3 压测时的 JVM 监控

**jstat 监控 GC**：

```bash
# 每秒输出 GC 情况
jstat -gc <pid> 1s

# 字段含义：
# S0C/S1C: Survivor 0/1 容量
# EC: Eden 容量
# OC: Old 容量
# YGC: Young GC 次数
# FGC: Full GC 次数
# YGCT: Young GC 总耗时
# FGCT: Full GC 总耗时
```

**jstack 导出线程栈**：

```bash
# 压测时导出线程栈，找阻塞
jstack <pid> > /tmp/thread-dump.txt

# 用 fastthread.io 分析
```

### 3.4 压测环境准备

**JVM 调优（压测前）**：

```bash
JAVA_OPTS="
  -Xms4g -Xmx4g
  -XX:+UseG1GC
  -XX:MaxGCPauseMillis=200
  -XX:+HeapDumpOnOutOfMemoryError
  -Xloggc:/var/log/gc.log
  -XX:+PrintGCDetails
"
```

**MySQL 调优**：

```sql
-- 压测前关闭慢日志（避免影响）
SET GLOBAL slow_query_log = OFF;

-- 压测后恢复
SET GLOBAL slow_query_log = ON;
```

## 4. 关键要点总结

- 压测核心指标：**TPS / RT / P99 / 错误率**
- JMeter 适合中小型项目，GUI 友好
- Gatling 适合大型项目，代码化、高性能
- wrk 适合简单 HTTP 压测
- 压测前调整 JVM 参数（-Xms = -Xmx）和关闭慢日志
- 压测中用 `jstat -gc` 监控 GC，`jstack` 找阻塞
- 压测目标：找到 **TPS 上限** 和 **P99 拐点**

## 5. 练习题

### 练习 1：基础（必做）

用 JMeter 对 `GET /admin-api/system/user/get` 压测：50 用户、持续 30 秒，观察 Summary Report 中的 Average、Median、90% Line、Error %。

### 练习 2：进阶

用 Gatling 编写脚本压测登录接口：100 用户阶梯加压 10 秒 → 持续 200 QPS 压 60 秒，断言 P99 < 500ms、错误率 < 0.1%。

### 练习 3：挑战（选做）

模拟生产流量录制：用 JMeter 的 HTTP Test Script Recorder 录制 5 分钟真实操作，转换为压测脚本进行回放，对比录制与回放的 TPS 差异。

## 6. 参考资料

- [JMeter 官方文档](https://jmeter.apache.org/usermanual/index.html)
- [Gatling 官方文档](https://gatling.io/docs/current/)
- [wrk GitHub](https://github.com/wg/wrk)
- ruoyi 性能测试建议：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
