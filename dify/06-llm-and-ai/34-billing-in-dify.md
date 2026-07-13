# 6.5 dify 的账单系统分析

> 从 API 适配、类型校验、配额事务、订阅缓存和容错边界分析 dify 的 `BillingService`。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述 dify API 与外部 Billing 服务的职责边界
- 理解 `BillingInfo`、`SubscriptionPlan` 和 quota 结果类型
- 解释连接池、重试、响应校验与缓存的设计目的
- 为自建 Billing API 设计兼容契约和失败策略

## 📚 前置知识

- [Token 用量统计与计费](./30-token-tracking.md)
- [限流、配额管理与用户余额](./33-rate-limit-quota.md)
- HTTP 客户端、TypedDict、Pydantic `TypeAdapter` 和 Redis 基础

## 1. 核心概念

### 1.1 `BillingService` 是外部服务适配器

在当前源码中，`BillingService` 不是完整支付引擎。它负责从环境变量读取 Billing API 地址和密钥，向外部服务发送请求，并把 JSON 校验成稳定的内部类型。

```text
Controller / Service
        ↓
BillingService（防腐层）
  ├── 订阅信息与支付链接
  ├── 功能 quota 与余额
  ├── 账号/教育/通知相关 Billing API
  ├── HTTP 重试和错误翻译
  └── Redis 订阅计划缓存
        ↓
外部 Billing API（账本与订阅真相源）
```

支付处理、账本原子性和订阅状态计算主要属于外部服务。不能从这个适配文件推断自部署版一定存在本地扣费表或异步 token 上报。

### 1.2 两类额度契约

`BillingInfo` 描述套餐能力，如成员数、App 数、文档上传和功能开关；quota 接口描述某个 `feature_key` 的实时预留、结算、释放与余额。二者粒度不同：前者适合展示和能力门控，后者适合高并发任务计量。

TypedDict 负责静态可读性，`TypeAdapter.validate_python()` 在运行时校验并按非严格模式兼容外部服务可能返回的数字字符串。

### 1.3 容错与一致性边界

- 连接池减少重复 TCP/TLS 建连。
- Tenacity 只对 `httpx.RequestError` 重试，并限制总重试时长。
- HTTP 状态码被翻译为面向调用方的异常。
- 套餐批量查询可使用 Redis TTL 缓存；源码明确指出需要高一致性时应绕过缓存。
- quota reserve/commit/release 的原子性由外部 Billing 服务保证，API 侧负责携带幂等标识并校验结果。

重试 POST 时，外部端点必须利用 `request_id` 或 `reservation_id` 保证幂等，否则网络超时后的自动重试可能重复执行。

## 2. 代码示例

### 2.1 用 TypedDict 与 TypeAdapter 校验外部响应

```python
# 文件：billing_contract.py
from typing import TypedDict

from pydantic import TypeAdapter, ValidationError


class Balance(TypedDict):
    available: int
    reserved: int
    quota: int
    usage: int


balance_adapter = TypeAdapter(Balance)


def parse_balance(payload: object) -> Balance:
    balance = balance_adapter.validate_python(payload)
    if balance["available"] < 0 or balance["reserved"] < 0:
        raise ValueError("Billing 返回了负数余额")
    return balance


try:
    print(parse_balance({"available": "90", "reserved": 5, "quota": 100, "usage": 5}))
except (ValidationError, ValueError) as exc:
    print("invalid billing response:", exc)
```

**说明**：非严格校验可把数字字符串转成整数；领域不变量仍要单独验证，类型正确不代表业务状态一定正确。

### 2.2 执行带额度预留的任务

```python
# 文件：metered_operation.py
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Reservation:
    reservation_id: str


def execute_with_quota(
    reserve: Callable[[str, int], Reservation],
    commit: Callable[[str, int], None],
    release: Callable[[str], None],
    request_id: str,
    operation: Callable[[], tuple[str, int]],
) -> str:
    reservation = reserve(request_id, 1_000)
    try:
        result, actual = operation()
        commit(reservation.reservation_id, actual)
        return result
    except Exception:
        release(reservation.reservation_id)
        raise
```

**说明**：示例展示调用方编排；生产环境还要处理 commit 成功但响应丢失的“不确定结果”，此时应查询 reservation 状态而不是直接 release。

## 3. dify 仓库源码解读

### 3.1 核心响应契约

**文件位置**：`/Users/xu/code/github/dify/api/services/billing_service.py`  
**核心代码**（行 28-57）：

```python
class SubscriptionPlan(TypedDict):
    """Tenant subscriptionplan information."""

    plan: str
    expiration_date: int


class QuotaReserveResult(TypedDict):
    reservation_id: str
    available: int
    reserved: int


class QuotaCommitResult(TypedDict):
    available: int
    reserved: int
    refunded: int


class QuotaReleaseResult(TypedDict):
    available: int
    reserved: int
    released: int


class QuotaBalanceResult(TypedDict):
    available: int
    reserved: int
    quota: int
    usage: int
```

**解读**：订阅计划只保留套餐与过期时间；quota 结果则围绕实时状态设计。commit 返回 `refunded`，release 返回 `released`，使调用方能够观测预留与实际结算差异。

### 3.2 HTTP 重试与错误翻译

**文件位置**：同上  
**核心代码**（行 410-429）：

```python
    @retry(
        wait=wait_fixed(2),
        stop=stop_before_delay(10),
        retry=retry_if_exception_type(httpx.RequestError),
        reraise=True,
    )
    def _send_request(
        cls,
        method: Literal["GET", "POST", "DELETE", "PUT"],
        endpoint: str,
        json=None,
        params=None,
        base_url: str | None = None,
    ):
        headers = {"Content-Type": "application/json", "Billing-Api-Secret-Key": cls.secret_key}

        url = f"{base_url or cls.base_url}{endpoint}"
        response = _http_client.request(method, url, json=json, params=params, headers=headers, follow_redirects=True)
        if method == "GET" and response.status_code != httpx.codes.OK:
            raise ValueError("Unable to retrieve billing information. Please try again later or contact support.")
```

**解读**：固定等待 2 秒，总重试窗口小于 10 秒，只重试网络请求异常；已收到的非 200 响应由后续分支直接翻译，不会被该装饰器自动重试。认证密钥放在专用请求头中。

## 4. 关键要点总结

- `BillingService` 是外部 Billing API 的适配层，不是本地支付与账本实现。
- `BillingInfo` 负责套餐能力，quota 结果负责实时额度事务。
- TypedDict 提供静态契约，TypeAdapter 提供运行时校验和兼容转换。
- 连接池、有限网络重试与 Redis TTL 缓存分别优化连接、可用性和读取性能。
- POST 重试依赖服务端幂等性；高一致性场景必须绕过套餐缓存或主动失效。

## 5. 练习题

### 练习 1：基础（必做）

为 `Balance` 解析器增加不变量检查：四个值非负，并验证 `available + reserved + usage == quota`。

**参考答案**：完成类型校验后再计算等式；若外部契约允许透支或额外 bucket，应调整而不是强套该公式。

### 练习 2：进阶

用 FastAPI 实现兼容的 mock Billing API，包含 `/quota/reserve`、`/quota/commit`、`/quota/release` 和 `/quota/balance`，并以 `request_id` 保证 reserve 幂等。

### 练习 3：挑战（选做）

设计 Billing 适配器的故障演练：覆盖 Redis 不可用、Billing 超时、commit 响应丢失、缓存套餐过期和响应字段类型变化，定义每种情况是 fail-open 还是 fail-closed。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/billing_service.py`
- `/Users/xu/code/github/dify/api/libs/helper.py`
- Pydantic TypeAdapter：https://docs.pydantic.dev/latest/concepts/type_adapter/
- Tenacity：https://tenacity.readthedocs.io/
- httpx：https://www.python-httpx.org/

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
