# 10 - DevOps 与部署

> ruoyi-vue-pro 的部署、容器化、CI/CD、监控。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| Docker 基础 / Dockerfile / Compose | [_common/09-containerization/](../../_common/09-containerization/) | [01-ruoyi-deploy.md](./01-ruoyi-deploy.md)；其余 Java Docker 文待补 |
| Nginx 反向代理 / HTTPS | [_common/10-network-proxy/](../../_common/10-network-proxy/) | [02-gateway.md](./02-gateway.md)；Nginx/HTTPS 项目文待补 |
| CI/CD / GitHub Actions / GitLab CI / Jenkins | [_common/11-cicd/](../../_common/11-cicd/) | 项目 CI 实战文待补 |
| 蓝绿 / 灰度部署 | [_common/12-deploy-strategies/](../../_common/12-deploy-strategies/) | 项目部署策略文待补 |
| 监控 / Prometheus / 日志 / 追踪 | [_common/19-observability/](../../_common/19-observability/) | 项目监控章节待补 |
| Kubernetes | [_common/16-kubernetes/](../../_common/16-kubernetes/) | 项目 K8s 文待补 |
| JVM 调优 | [01-java-fundamentals 阶段 GC/调优文档](../01-java-fundamentals/) | 项目性能章节待补 |

## 模块 10.1 构建与打包

- [ ] [1.1 Maven 多模块构建](./03-maven-build.md)
- [ ] [1.2 Spring Boot 打包：jar / war](./04-spring-boot-jar.md)
- [ ] [1.3 配置文件外置](./05-external-config.md)
- [ ] [1.4 Profile 多环境构建](./06-profile-build.md)

## 模块 10.2 Docker 容器化

- [ ] Java 应用的 Docker 镜像（公共见 [_common/09-containerization/01-concepts](../../_common/09-containerization/01-concepts.md)、[02-dockerfile](../../_common/09-containerization/02-dockerfile.md)；项目文待补）
- [ ] 多阶段构建（公共见 [_common/09-containerization/03-multi-stage](../../_common/09-containerization/03-multi-stage.md)；项目文待补）
- [ ] Dockerfile 优化：JVM 镜像（公共见 [_common/09-containerization/](../../_common/09-containerization/)；项目文待补）
- [ ] docker-compose 部署（公共见 [_common/09-containerization/04-compose](../../_common/09-containerization/04-compose.md)；项目文待补）
- [ ] [2.5 ruoyi 的部署脚本](./01-ruoyi-deploy.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [07-*-build-deploy: 构建打包与部署脚本](./07-*-build-deploy.md)
  - 覆盖：03-maven-build.md, 04-spring-boot-jar.md, 05-external-config.md, 06-profile-build.md, 01-ruoyi-deploy.md


## 模块 10.3 反向代理与网关

- [ ] Nginx 反向代理（公共见 [_common/10-network-proxy/02-reverse-proxy](../../_common/10-network-proxy/02-reverse-proxy.md)；项目文待补）
- [ ] HTTPS 配置（公共见 [_common/10-network-proxy/03-https](../../_common/10-network-proxy/03-https.md)；项目文待补）
- [ ] 负载均衡策略（公共见 [_common/10-network-proxy/](../../_common/10-network-proxy/)；项目文待补）
- [ ] [3.4 Spring Cloud Gateway（yudao-cloud）](./02-gateway.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [08-*-gateway: 网关与反向代理视角](./08-*-gateway.md)
  - 覆盖：02-gateway.md


## 模块 10.4 CI/CD

- [ ] GitHub Actions（公共见 [_common/11-cicd/02-github-actions](../../_common/11-cicd/02-github-actions.md)；项目文待补）
- [ ] GitLab CI（公共见 [_common/11-cicd/03-gitlab-ci](../../_common/11-cicd/03-gitlab-ci.md)；项目文待补）
- [ ] Jenkins 流水线（公共见 [_common/11-cicd/04-jenkins](../../_common/11-cicd/04-jenkins.md)；项目文待补）
- [ ] 蓝绿 / 灰度发布（公共见 [_common/12-deploy-strategies/](../../_common/12-deploy-strategies/)；项目文待补）

## 模块 10.5 监控与告警

- [ ] Spring Boot Actuator / 应用指标（公共见 [_common/19-observability/06-app-metrics](../../_common/19-observability/06-app-metrics.md)；项目文待补）
- [ ] Spring Boot Admin（待补）
- [ ] Prometheus + Grafana（公共见 [_common/19-observability/04-prometheus](../../_common/19-observability/04-prometheus.md)、[05-grafana](../../_common/19-observability/05-grafana.md)；项目文待补）
- [ ] 结构化日志 / ELK 思路（公共见 [_common/19-observability/01-log-levels](../../_common/19-observability/01-log-levels.md)、[02-structured-logging](../../_common/19-observability/02-structured-logging.md)；项目文待补）
- [ ] 链路追踪（公共见 [_common/19-observability/07-tracing-concepts](../../_common/19-observability/07-tracing-concepts.md)、[08-opentelemetry](../../_common/19-observability/08-opentelemetry.md)；项目文待补）
- [ ] Sentry 错误监控（公共见 [_common/19-observability/10-sentry](../../_common/19-observability/10-sentry.md)；项目文待补）

## 模块 10.6 性能调优

- [ ] JVM 调优：GC 参数（见 [01-java-fundamentals](../01-java-fundamentals/)；项目文待补）
- [ ] Arthas 线上诊断（待补）
- [ ] 慢 SQL 分析（可对照 03/04 阶段 MyBatis 慢 SQL；项目文待补）
- [ ] 压测：JMeter / Gatling（公共见 [_common/18-testing/05-performance-test](../../_common/18-testing/05-performance-test.md)、[06-stress-test](../../_common/18-testing/06-stress-test.md)；项目文待补）

## 🎯 ruoyi-vue-pro 仓库对应位置

- 部署脚本：`/Users/xu/code/github/ruoyi-vue-pro/script/`
- Docker 镜像：搜索 `Dockerfile`
- CI 配置：`.github/workflows/`（如果有）
- 监控：参考 `yudao-framework/yudao-spring-boot-starter-monitor/`
