# 小验证：Celery 架构到 Beat

> 覆盖：
> - [14-celery-architecture](./05-celery-architecture.md)
> - [15-celery-tasks](./06-celery-tasks.md)
> - [16-celery-invoke](./07-celery-invoke.md)
> - [17-celery-routing](./08-celery-routing.md)
> - [18-celery-beat](./09-celery-beat.md)
>
> 预计：30～50 分钟 · 读仓库 + 笔记

## 背景

异步工作流、文档索引等多依赖 Celery。本组先摸清 app 配置、任务定义、调用方式与路由/Beat，不强制改幂等与重试（见 [16-*-celery-reliability-events](./16-*-celery-reliability-events.md)）。

## 需求

1. 在仓库定位：Celery app 配置、一个真实 `@shared_task`（或项目等价装饰器）、其 `delay`/`apply_async` 调用点；写入 `NOTES.md` 调用链（≥3 路径）。
2. 记录该任务所在队列/路由线索（若有 `queue=` 或 route 配置则抄关键配置；没有则写「默认队列」）。
3. 从 Beat/定时配置中找 **1 个** 周期任务（或明确「本环境未启用的配置项」），记：任务名 → 周期线索。
4. 用文字说明：至少一次「什么情况该进队列而不是在 request 线程硬做」。

## 提示

- `api/extensions/ext_celery.py`、`api/celery_entrypoint.py`、`api/tasks/`
- `api/services/async_workflow_service.py`
- 不必起完整 worker 也能完成路径阅读

## 验收标准

- [ ] NOTES 任务定义与调用点路径正确
- [ ] 队列/路由或默认策略有记录
- [ ] Beat/定时至少有 1 条线索或「未启用」说明
- [ ] 说清为何长任务不进 Web 进程同步执行

## 延伸（选做）

列一张「任务名 → 周期 → 风险」小表（读配置即可，3 行以上）。
