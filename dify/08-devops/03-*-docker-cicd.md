# 小验证：dify Docker 与 CI/CD

> 覆盖：
> - [01-dify-docker](./01-dify-docker.md)
> - [02-cicd-in-dify](./02-cicd-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

能把栈拉起来并理解 CI 门禁，是改 monorepo 的前提。验证：读 compose 与 workflows，完成一次「配置级」小改。

## 需求

1. 阅读 `docker/docker-compose.yaml`（及 overlay），`NOTES.md` 列出 api/worker/web/db/redis 等关键服务与依赖关系。
2. 阅读 `.github/workflows/` 中测试/lint 相关 workflow，记录：触发条件、关键 job 名。
3. 小改动选一（本地分支）：
   - 为 compose 增加更清楚的注释或 dev 用 profile 说明，或
   - 在 CI 文档/脚本处修正一处过时命令（需核实），或
   - 添加一个 **不默认开启** 的 healthcheck 注释示例。
4. 写出你本机「最小启动命令」与「跑 api 单测」的命令清单。

## 提示

- `/Users/xu/code/github/dify/docker/`
- `/Users/xu/code/github/dify/.github/workflows/`
- 不要把宿主机密钥写进 compose 提交

## 验收标准

- [ ] 服务依赖关系图/列表完整
- [ ] CI 触发与 job 记录准确
- [ ] 有可回滚的小改动或明确的「只读审计」产出
- [ ] 命令清单可被第三人复用

## 延伸（选做）

对比生产 compose 与 dev 覆盖文件的差异。
