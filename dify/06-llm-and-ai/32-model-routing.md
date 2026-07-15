# 6.3 模型路由与降级策略

> 根据任务、成本和健康状态选择模型，并理解 dify 的默认模型与多凭据轮询机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分模型路由、负载均衡、重试和降级
- 设计可控的 fallback 错误分类与停止条件
- 实现基于任务复杂度和预算的路由器
- 看懂 dify 的凭据轮询、冷却与默认模型回退

## 📚 前置知识

- [dify 的模型适配层](./28-model-runtime.md)
- [Token 用量统计与计费](./30-token-tracking.md)
- [工具错误处理](./17-tool-error-handling.md)
- Redis 与异常分类（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)、[异常](../01-fundamentals/06-python-exceptions.md)）

## 1. 核心概念

### 1.1 四种机制不要混淆

| 机制 | 决策对象 | 典型目标 |
| --- | --- | --- |
| 路由 | 不同模型/Provider | 质量、成本、合规、延迟 |
| 负载均衡 | 同模型的多个凭据/端点 | 分摊流量、提高可用性 |
| 重试 | 同一路径再次请求 | 恢复瞬时故障 |
| 降级 | 主路径失败后换备选 | 保住核心能力 |

路由发生在调用前，依据任务特征选择“最合适”的模型；降级发生在调用失败或预算不足后。二者可以组合，但不能对所有异常无条件 fallback。

### 1.2 哪些错误可以降级

- **适合**：限流（详见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md) 与本模块 [限流与配额](./33-rate-limit-quota.md)）、连接超时、服务暂不可用、某个凭据健康状态异常。
- **谨慎**：鉴权错误。切换到另一个已配置凭据可能有效，但应报警。
- **不适合**：Prompt 非法、上下文超限、内容安全拒绝、业务取消。换模型可能重复失败、增加费用或绕过策略。

每次尝试需要独立超时，总调用还要有全局 deadline；否则三层 fallback 可能把用户等待时间放大三倍。

### 1.3 路由信号与可观测性

常见信号包括任务类型、输入长度、是否需要视觉/工具/结构化输出、租户策略、地区、预算、历史延迟和健康状态。路由结果应记录：候选集、选择原因、每次尝试、错误类别、冷却时间、最终模型、费用和延迟。

缓存路由决策时，键必须包含影响结果的策略版本与租户范围；否则策略更新后仍可能使用旧决策。

## 2. 代码示例

### 2.1 基于能力和预算的确定性路由

```python
# 文件：model_router.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    name: str
    supports_vision: bool
    quality: int
    input_cost: float


def route(*, needs_vision: bool, complexity: int, max_input_cost: float) -> Candidate:
    candidates = [
        Candidate("small", False, 1, 0.20),
        Candidate("balanced", True, 2, 1.00),
        Candidate("reasoning", True, 3, 5.00),
    ]
    eligible = [
        item
        for item in candidates
        if item.input_cost <= max_input_cost
        and (not needs_vision or item.supports_vision)
        and item.quality >= complexity
    ]
    if not eligible:
        raise RuntimeError("没有满足能力与预算的模型")
    return min(eligible, key=lambda item: item.input_cost)


print(route(needs_vision=True, complexity=2, max_input_cost=2.0))
```

**说明**：先做硬约束过滤，再在合格候选中优化成本。不要让便宜但不支持所需能力的模型进入候选集。

### 2.2 只对可恢复错误执行 fallback

```python
# 文件：fallback_chain.py
from collections.abc import Callable


class RetryableModelError(Exception):
    pass


class InvalidPromptError(Exception):
    pass


def invoke_with_fallback(
    prompt: str,
    candidates: list[tuple[str, Callable[[str], str]]],
) -> tuple[str, str]:
    failures: list[str] = []
    for name, invoke in candidates:
        try:
            return name, invoke(prompt)
        except RetryableModelError as exc:
            failures.append(f"{name}: {exc}")
            continue
        except InvalidPromptError:
            raise
    raise RetryableModelError("; ".join(failures))


def unavailable(_: str) -> str:
    raise RetryableModelError("temporary unavailable")


name, answer = invoke_with_fallback("hello", [("primary", unavailable), ("backup", str.upper)])
print(name, answer)
```

**说明**：非法输入直接失败，不换模型重复花费；只有明确可恢复错误才进入下一个候选。

## 3. dify 仓库源码解读

### 3.1 多凭据轮询与冷却

**文件位置**：`/Users/xu/code/github/dify/api/core/model_manager.py`  
**核心代码**（行 389-417）：

```python
        last_exception: Union[InvokeRateLimitError, InvokeAuthorizationError, InvokeConnectionError, None] = None
        while True:
            lb_config = self.load_balancing_manager.fetch_next()
            if not lb_config:
                if not last_exception:
                    raise ProviderTokenNotInitError("Model credentials is not initialized.")
                else:
                    raise last_exception

            # Additional policy compliance check as fallback (in case fetch_next didn't catch it)
            try:
                from core.helper.credential_utils import runtime_check_credential_policy_compliance

                if lb_config.credential_id:
                    runtime_check_credential_policy_compliance(
                        credential_id=lb_config.credential_id,
                        provider=self.provider,
                        credential_type=PluginCredentialType.MODEL,
                    )
            except Exception as e:
                logger.warning(
                    "Load balancing config %s failed policy compliance check in round-robin: %s", lb_config.id, str(e)
                )
                self.load_balancing_manager.cooldown(lb_config, expire=60)
                continue

            try:
                kwargs["credentials"] = lb_config.credentials
                return function(*args, **kwargs)
```

**解读**：循环读取下一个凭据，候选耗尽后抛出最后一个可恢复异常。凭据还要经过策略合规检查，不合规则进入冷却而不是继续调用；通过检查后才替换本次调用的凭据。

### 3.2 按错误类型设置冷却

**文件位置**：同上  
**核心代码**（行 418-429）：

```python
            except InvokeRateLimitError as e:
                # expire in 60 seconds
                self.load_balancing_manager.cooldown(lb_config, expire=60)
                last_exception = e
                continue
            except (InvokeAuthorizationError, InvokeConnectionError) as e:
                # expire in 10 seconds
                self.load_balancing_manager.cooldown(lb_config, expire=10)
                last_exception = e
                continue
            except Exception as e:
                raise e
```

**解读**：限流冷却 60 秒，授权或连接错误冷却 10 秒；其他异常立即上抛。这体现了“按错误分类降级”，避免对业务错误无限轮询。

## 4. 关键要点总结

- 路由选模型，负载均衡选同模型端点，重试重复路径，降级换备选。
- 先用能力、合规和预算做硬过滤，再优化成本或延迟。
- 只对明确可恢复错误 fallback，并设置单次超时、全局 deadline 和最大尝试数。
- dify 的 `ModelInstance` 可在多个凭据间轮询，并用 Redis 冷却故障配置。
- 每次路由与降级都要记录原因、尝试链、最终模型、费用和延迟。

## 5. 练习题

### 练习 1：基础（必做）

给路由示例加入 `supports_tools`，确保需要工具调用时不会选择不支持工具的候选。

**参考答案**：把它作为硬约束参与 `eligible` 过滤，不要只用质量分数间接判断。

### 练习 2：进阶

为 fallback 示例增加指数退避、随机抖动和 5 秒全局 deadline，并编写测试证明非法 Prompt 不会重试。

### 练习 3：挑战（选做）

结合 dify `LBModelManager.fetch_next()` 与建议问题模型的默认回退，设计“同模型多凭据 → 同级备选模型 → 小模型降级”的三级策略，并定义每级允许的异常集合。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/model_manager.py`
- `/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`
- `/Users/xu/code/github/dify/api/core/provider_manager.py`
- [限流、配额管理与用户余额](./33-rate-limit-quota.md)

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
