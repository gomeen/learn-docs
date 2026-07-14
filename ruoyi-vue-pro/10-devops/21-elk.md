# 5.4 ELK 日志收集

> 理解 ELK（Elasticsearch + Logstash + Kibana）日志收集架构，掌握 Spring Boot 应用接入 ELK 的方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ELK 三件套各自的作用
- 掌握 Spring Boot 日志输出到 ELK 的方案
- 能在 Kibana 中查询和分析日志
- 知道 ruoyi 的日志配置

## 📚 前置知识

- Linux 基础
- `18-actuator.md`
- JSON 基础

## 1. 核心概念

### 1.1 ELK 是什么？

| 组件 | 作用 |
|------|------|
| **Elasticsearch** | 分布式搜索引擎（存储 + 索引） |
| **Logstash** | 日志收集 + 解析 + 转发 |
| **Kibana** | 可视化界面（搜索 + 图表） |
| **Filebeat**（常与 ELK 配合） | 轻量级日志采集器 |

### 1.2 架构

```
Spring Boot App (写日志)
   ↓
  logback → JSON 文件
                 ↓ Filebeat 采集
                 ↓
            Logstash (解析 + 富化)
                 ↓
        Elasticsearch (索引存储)
                 ↓
             Kibana (查询 + 仪表盘)
```

### 1.3 核心概念

| 概念 | 含义 |
|------|------|
| **Index** | Elasticsearch 的索引（对应一张表） |
| **Document** | 一条日志（一个 JSON） |
| **Mapping** | 字段类型定义 |
| **Ingest Pipeline** | Logstash 的解析管道（也可在 ES 端做） |

## 2. 代码示例

### 2.1 Spring Boot 输出 JSON 日志

```xml
<!-- logstash-logback-encoder -->
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>7.4</version>
</dependency>
```

**logback-spring.xml**：

```xml
<configuration>
    <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeMdcKeyName>traceId</includeMdcKeyName>
            <customFields>{"app":"yudao-server"}</customFields>
        </encoder>
    </appender>

    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>/work/logs/yudao-server.json</file>
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeMdcKeyName>traceId</includeMdcKeyName>
            <customFields>{"app":"yudao-server"}</customFields>
        </encoder>
        <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
            <fileNamePattern>/work/logs/yudao-server.%d{yyyy-MM-dd}.%i.json.gz</fileNamePattern>
            <maxFileSize>100MB</maxFileSize>
            <maxHistory>30</maxHistory>
        </rollingPolicy>
    </appender>

    <root level="INFO">
        <appender-ref ref="STDOUT"/>
        <appender-ref ref="FILE"/>
    </root>
</configuration>
```

### 2.2 Filebeat 配置

```yaml
# 文件：filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /work/logs/yudao-server.json
    json.keys_under_root: true
    json.add_error_key: true

output.logstash:
  hosts: ["logstash:5044"]
```

### 2.3 docker-compose 部署 ELK

```yaml
version: "3.4"
services:
  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - es-data:/usr/share/elasticsearch/data

  logstash:
    image: logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的日志配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 173-201）：

```yaml
# 日志文件配置
logging:
  file:
    name: ${user.home}/logs/${spring.application.name}.log # 日志文件名，全路径
  level:
    # 配置自己写的 MyBatis Mapper 打印日志
    cn.iocoder.yudao.module.bpm.dal.mysql: debug
    cn.iocoder.yudao.module.infra.dal.mysql: debug
    cn.iocoder.yudao.module.infra.dal.mysql.logger.ApiErrorLogMapper: INFO # 配置 ApiErrorLogMapper 的日志级别为 info，避免和 GlobalExceptionHandler 重复打印
    cn.iocoder.yudao.module.infra.dal.mysql.job.JobLogMapper: INFO # 配置 JobLogMapper 的日志级别为 info
    cn.iocoder.yudao.module.infra.dal.mysql.file.FileConfigMapper: INFO # 配置 FileConfigMapper 的日志级别为 info
    cn.iocoder.yudao.module.pay.dal.mysql: debug
    cn.iocoder.yudao.module.pay.dal.mysql.notify.PayNotifyTaskMapper: INFO
    cn.iocoder.yudao.module.system.dal.mysql: debug
    cn.iocoder.yudao.module.system.dal.mysql.sms.SmsChannelMapper: INFO
    cn.iocoder.yudao.module.tool.dal.mysql: debug
    cn.iocoder.yudao.module.member.dal.mysql: debug
    cn.iocoder.yudao.module.trade.dal.mysql: debug
    cn.iocoder.yudao.module.promotion.dal.mysql: debug
    cn.iocoder.yudao.module.statistics.dal.mysql: debug
    cn.iocoder.yudao.module.crm.dal.mysql: debug
    cn.iocoder.yudao.module.erp.dal.mysql: debug
    cn.iocoder.yudao.module.mes.dal.mysql: debug
    cn.iocoder.yudao.module.wms.dal.mysql: debug
    cn.iocoder.yudao.module.iot.dal.mysql: debug
    cn.iocoder.yudao.module.iot.dal.tdengine: DEBUG
    cn.iocoder.yudao.module.iot.service.rule: debug
    cn.iocoder.yudao.module.ai.dal.mysql: debug
    cn.iocoder.yudao.module.im.dal.mysql: debug
    org.springframework.context.support.PostProcessorRegistrationDelegate: ERROR
```

**解读**：
- 第 2-3 行：日志文件路径 `${user.home}/logs/yudao-server.log`
- 第 4-29 行：**关键** — 按模块细粒度配置日志级别
  - 大部分 module 用 `debug` 打印 SQL
  - 但 `*ErrorLogMapper` 用 `INFO`（避免和 `GlobalExceptionHandler` 重复）
  - `JobLogMapper` 同样 `INFO`（定时任务日志由 AOP 单独记录）
- 第 29 行：禁用 Spring 启动时的 DEBUG 提示

### 3.2 部署脚本中的日志文件

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 130-141）：

```bash
        # 健康检查未通过，则异常退出 shell 脚本，不继续部署。
        if [ ! "$result" == "200" ]; then
            echo "[healthCheck] 健康检查不通过，可能部署失败。查看日志，自行判断是否启动成功";
            tail -n 10 nohup.out
            exit 1;
        # 健康检查通过，打印最后 10 行日志，可能部署的人想看下日志。
        else
            tail -n 10 nohup.out
        fi
    # 如果未配置健康检查，则 sleep 120 秒，人工看日志是否部署成功。
    else
        echo "[healthCheck] HEALTH_CHECK_URL 未配置，开始 sleep 120 秒";
        sleep 120
        echo "[healthCheck] sleep 120 秒完成，查看日志，自行判断是否启动成功";
        tail -n 50 nohup.out
    fi
```

**解读**：
- 第 130 行：`tail -n 10 nohup.out` — 健康检查失败时输出启动日志最后 10 行
- 第 135 行：成功后也输出最后 10 行
- 第 141 行：未配置健康检查时输出 50 行
- **设计意图**：部署脚本辅助人工排查问题

### 3.3 建议的 ELK 集成方案

由于 ruoyi 当前日志是纯文本，**ELK 集成需要做以下调整**：

1. 引入 `logstash-logback-encoder` 依赖
2. 修改 `logback-spring.xml` 输出 JSON
3. 部署 Filebeat 采集日志
4. Kibana 创建 Index Pattern 索引 yudao-server-*

## 4. 关键要点总结

- ELK = Elasticsearch（存储） + Logstash（解析） + Kibana（可视化）
- Spring Boot 输出 JSON 日志：`logstash-logback-encoder`
- 用 Filebeat 采集 JSON 日志推到 Logstash
- Kibana 搜索日志：按字段过滤（如 `level:ERROR AND app:yudao-server`）
- ruoyi 当前是**纯文本日志**，需要集成 ELK 时改用 JSON 格式
- **关键技巧**：日志中包含 `traceId` 字段便于链路追踪

## 5. 练习题

### 练习 1：基础（必做）

修改 yudao-server 的 `logback-spring.xml`，加入 `logstash-logback-encoder`，启动后查看 `${user.home}/logs/yudao-server.log` 是否输出 JSON 格式。

### 练习 2：进阶

用 docker-compose 启动 Elasticsearch + Kibana，配置 Kibana 创建 `yudao-server-*` 索引模式，在 Discover 页面搜索 `level:ERROR` 找出所有错误日志。

### 练习 3：挑战（选做）

为 Kibana 配置 Dashboard：展示最近 24 小时的错误日志数量、各模块的日志分布、Top 10 异常堆栈。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- [ELK 官方文档](https://www.elastic.co/guide/index.html)
- [logstash-logback-encoder](https://github.com/logfellow/logstash-logback-encoder)
- ruoyi 部署文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
