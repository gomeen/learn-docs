# 小验证：Pydantic v2 与 DTO

> 覆盖：
> - [09-pydantic-basics](./12-pydantic-basics.md)
> - [10-pydantic-validators](./13-pydantic-validators.md)
> - [11-pydantic-dto](./14-pydantic-dto.md)
> - [12-pydantic-config](./15-pydantic-config.md)
> - [13-pydantic-in-dify](./16-pydantic-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

Pydantic 是 dify 请求/领域模型的主力。验证：定义带校验的 DTO，并接到一个本地或仓库内的解析点。

## 需求

二选一（推荐 B）：

**A. 本地**：写 `dto_lab.py`，用 Pydantic v2 定义 `CreateWebhookPayload`（url、events: list[str]、secret 可选），`field_validator` 校验 url 必须 http(s)；`model_validator` 要求 events 非空；`ConfigDict(extra='forbid')`。

**B. dify 仓库**：找到一处已有 Pydantic 模型（workflow entities 或 controller 入参），**新增一个可选字段**（带默认值，避免破坏调用方），并加一个合理 validator；在注释中说明为何默认值安全。

## 提示

- 仓库锚点：`/Users/xu/code/github/dify/api/core/workflow/entities/`
- `Field` / `field_validator` / `model_validator` / `ConfigDict`
- 改仓库时优先「可选 + 默认」，降低影响面

## 验收标准

- [ ] 合法数据通过，非法数据抛 `ValidationError`（贴出 1 段错误摘要）
- [ ] `extra='forbid'` 或项目等效策略生效（若选 A）
- [ ] 若选 B：默认值不改变旧行为；有类型标注与简短注释
- [ ] 无密钥写入代码库

## 延伸（选做）

为 DTO 增加 `model_dump(by_alias=True)` 的 API 层别名示例。
