# 4.6 dify 的 CI/CD 配置分析（`.github/workflows/`）

> 深入解读 dify 仓库的完整 CI/CD 配置，理解开源项目如何搭建多工作流协作。

## 🎯 学习目标

完成本文档后，你将能够：
- 读懂 dify 仓库所有 GitHub Actions 工作流的职责
- 理解 `main-ci.yml` 用 `check-changes` 智能分派任务的设计
- 知道 dify 部署到不同环境的策略（dev / saas / enterprise）

## 📚 前置知识

- CI/CD 概念与流水线（详见 [CI/CD 概念](../../_common/11-cicd/01-concepts.md)）
- GitHub Actions 工作流机制（详见 [GitHub Actions 实战](../../_common/11-cicd/02-github-actions.md)）
- 部署策略：蓝绿 / 金丝雀 / 滚动（详见 [蓝绿部署](../../_common/12-deploy-strategies/01-blue-green.md)、[灰度发布](../../_common/12-deploy-strategies/02-canary.md)、[滚动发布](../../_common/12-deploy-strategies/03-rolling-and-ab.md)）

## 1. 核心概念

### 1.1 dify 工作流全景

dify 维护 20+ 个 GitHub Actions 工作流，按职责分为 4 类：

| 类别 | 文件 | 职责 |
|------|------|------|
| **核心 CI** | `main-ci.yml` | PR 触发的智能分派测试 |
| **专项测试** | `api-tests.yml` / `cli-tests.yml` / `vdb-tests.yml` / `db-migration-test.yml` | 各类测试 |
| **构建** | `docker-build.yml` / `build-push.yml` | Docker 镜像构建和推送（Dockerfile 详见 [Dockerfile 编写](../../_common/09-containerization/02-dockerfile.md)） |
| **部署** | `deploy-dev.yml` / `deploy-saas.yml` / `deploy-enterprise.yml` | 多环境部署 |
| **自动化** | `style.yml` / `autofix.yml` / `labeler.yml` / `translate-i18n-claude.yml` | 代码质量自动化 |
| **运维** | `stale.yml` / `post-merge.yml` / `hotfix-cherry-pick.yml` | 仓库运维 |

### 1.2 触发器分类

- **pull_request**：PR 创建/更新时
- **push**：直接 push 到 main
- **workflow_run**：另一个工作流完成后
- **schedule**：定时任务（如 `stale.yml`）
- **workflow_dispatch**：手动触发

### 1.3 关键设计模式

dify 用了多个企业级 CI 模式：

1. **路径过滤**（paths-filter）：只跑相关测试
2. **复用工作流**（workflow_call）：共享测试步骤
3. **Depot 加速构建**：4 倍速 Docker 构建
4. **多环境部署**：dev / saas / enterprise 独立
5. **自动修复**（autofix）：black/isort 自动提交
6. **i18n 自动化**（claude 翻译）：自动同步多语言

## 2. 代码示例

### 2.1 智能分派测试（paths-filter）

```yaml
check-changes:
  runs-on: depot-ubuntu-24.04
  outputs:
    api-changed: ${{ steps.changes.outputs.api }}
    web-changed: ${{ steps.changes.outputs.web }}
  steps:
    - uses: dorny/paths-filter@v4
      id: changes
      with:
        filters: |
          api:
            - 'api/**'
          web:
            - 'web/**'
```

后续 job 用 `if: needs.check-changes.outputs.api-changed == 'true'` 判断是否运行。

### 2.2 复用工作流（workflow_call）

```yaml
# api-tests.yml 顶部
on:
  workflow_call:                # 关键：可被其他 workflow 调用
```

```yaml
# 在 main-ci.yml 中调用
api-tests:
  uses: ./.github/workflows/api-tests.yml
  with:
    python-version: "3.12"
  secrets: inherit
```

### 2.3 跨工作流触发（workflow_run）

```yaml
on:
  workflow_run:
    workflows: ["Build and Push API & Web"]   # 等待此 workflow 完成
    types: [completed]
```

## 3. 关键要点总结

- dify 维护 20+ 工作流，按职责分类清晰
- **`main-ci.yml` 用 paths-filter 智能分派**，只跑相关测试
- **复用工作流**（workflow_call）让测试步骤可在多处调用
- **Post-merge** 把昂贵测试延后到合并后，PR 阶段不跑
- **多环境部署**：dev / saas / enterprise 独立
- **Depot** 加速 Docker 构建（10-40x）
- **手动审批**用 SSH 远程执行部署脚本

---

**文档版本**：v1.0
**最后更新**：2026-07-13
