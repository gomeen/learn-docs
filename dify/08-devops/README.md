# 08 - DevOps 与部署

> 后端系统必须能稳定部署运行。本分类涵盖容器化、编排、CI/CD。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定内容 |
|------|---------|--------------|
| Docker 基础 / Dockerfile / Compose | [_common/09-containerization/](../../_common/09-containerization/) | 01-dify-docker.md（dify 全家桶） |
| K8s / Helm | [_common/16-kubernetes/](../../_common/16-kubernetes/) | 概念已抽公共；项目以 compose 为主 |
| Nginx 反向代理 / HTTPS | [_common/10-network-proxy/](../../_common/10-network-proxy/) | 14-17 章节（dify 实战） |
| CI/CD 概念 / GitHub Actions / GitLab CI | [_common/11-cicd/](../../_common/11-cicd/) | 18-21 章节（dify 实战） |
| 蓝绿 / 灰度部署 | [_common/12-deploy-strategies/](../../_common/12-deploy-strategies/) | 22-deployment-strategies.md |
| Terraform / Ansible | [_common/11-cicd/](../../_common/11-cicd/) | 24-25 章节（IaC） |

## 前置依赖

- Linux/Shell：[`_common/13-linux-shell`](../../_common/13-linux-shell/)

## 模块 8.1 Docker 容器化

- [ ] Docker 通用：[`_common/09-containerization`](../../_common/09-containerization/)
- [ ] [1.7 dify 的 Docker Compose 全家桶分析](./01-dify-docker.md)

## 模块 8.2 Kubernetes 编排

- [ ] [2.1 K8s 核心概念：Pod / Deployment / Service](../../_common/16-kubernetes/01-k8s-concepts.md)
- [ ] [2.2 K8s 工作负载：Deployment / StatefulSet / DaemonSet](../../_common/16-kubernetes/02-k8s-workloads.md)
- [ ] [2.3 K8s 网络：Service / Ingress / NetworkPolicy](../../_common/16-kubernetes/03-k8s-network.md)
- [ ] [2.4 ConfigMap 与 Secret](../../_common/16-kubernetes/04-k8s-configmap.md)
- [ ] [2.5 K8s 持久化存储：PV / PVC](../../_common/16-kubernetes/05-k8s-storage.md)
- [ ] [2.6 Helm Chart 入门](../../_common/16-kubernetes/06-helm.md)

## 模块 8.3 反向代理与负载均衡

- [ ] Nginx / HTTPS 通用：[`_common/10-network-proxy`](../../_common/10-network-proxy/)

## 模块 8.4 CI/CD 持续集成与部署

- [ ] CI/CD 通用：[`_common/11-cicd`](../../_common/11-cicd/)
- [ ] 部署策略通用：[`_common/12-deploy-strategies`](../../_common/12-deploy-strategies/)
- [ ] [4.6 dify 的 CI/CD 配置分析](./02-cicd-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [03-*-docker-cicd: dify Docker 与 CI/CD](./03-*-docker-cicd.md)
  - 覆盖：01-dify-docker.md, 02-cicd-in-dify.md


## 🎯 dify 仓库对应位置

- Docker 配置：`/Users/xu/code/github/dify/docker/`
- docker-compose：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
- Dockerfile：`/Users/xu/code/github/dify/docker/api/Dockerfile`
- CI 工作流：`/Users/xu/code/github/dify/.github/workflows/`
- 部署文档：`/Users/xu/code/github/dify/deploy/`
