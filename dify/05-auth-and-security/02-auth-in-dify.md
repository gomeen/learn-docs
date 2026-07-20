# 5.2.5 dify 的多租户认证流程分析

> 端到端梳理 dify 的认证流程：从登录到鉴权到租户注入，看懂完整调用链。

## 🎯 学习目标

完成本文档后，你将能够：
- 完整画出 dify 一次"受保护接口"调用的全链路
- 理解 `login_required` + `current_account_with_tenant` 的协同关系
- 理解每个装饰器在链中的位置与职责
- 能定位认证失败时的排查路径

## 📚 前置知识

- Session / Cookie 与 Token 刷新（详见 [Session 与 Cookie](../../_common/07-authentication/02-session-cookie.md)、[Token 刷新](../../_common/07-authentication/04-token-refresh.md)）
- RBAC（详见 [RBAC](../../_common/08-authorization/01-rbac.md)）
- 租户隔离（详见 [资源所有权与租户隔离](./01-resource-ownership.md)）
- 装饰器语法（详见 [装饰器](../01-fundamentals/11-decorator.md)）

## 1. 核心概念

### 1.1 一次"受保护接口"调用的全链路

```
客户端                                dify 后端
  │                                        │
  │ 1. POST /apps/abc/api-keys             │
  │    Cookie: access_token=xxx            │
  │    X-CSRF-Token: yyy                   │
  │ ───────────────────────────────────→   │
  │                                        │
  │                          ┌─ 装饰器链开始 ─┐
  │                          │ setup_required │
  │                          │ login_required │
  │                          │ account_init_  │
  │                          │   required     │
  │                          │ with_current_  │
  │                          │   tenant_id    │
  │                          │ rbac_perm_     │
  │                          │   required     │
  │                          └───────────────┘
  │                                        │
  │                          # login_required 内部
  │                          1. 校验 access_token
  │                          2. 校验 csrf_token (X-CSRF-Token == Cookie csrf_token)
  │                          3. 加载 user → g._login_user
  │                                        │
  │                          # with_current_tenant_id
  │                          4. 取 user.current_tenant_id
  │                                        │
  │                          # rbac_permission_required
  │                          5. 检查 user 是否 owner？
  │                             否则查 RBACService
  │                                        │
  │                          # 业务代码
  │                          6. _create_api_key(tenant_id)
  │                                        │
  │ ←─── 201 + {"token": "app-..."} ───────│
```

> 📌 **Sighting**：CSRF 同步令牌 / 双重 Cookie 原理见 [CSRF](../../_common/05-web-security/04-csrf.md)；本篇只展示 dify 在登录装饰器里如何校验。

### 1.2 装饰器分层模型

dify 的认证装饰器分为几层，从外到内依次：

| 层级 | 装饰器 | 作用 |
|------|--------|------|
| 1 | `setup_required` | 检查 dify 是否已完成初始化 |
| 2 | `login_required` | 验证 Token、加载用户、检查 CSRF |
| 3 | `account_initialization_required` | 用户是否完成首次设置 |
| 4 | `with_current_user` / `with_current_tenant_id` | 注入 user / tenant_id 到 kwargs |
| 5 | `rbac_permission_required` | RBAC 检查 |
| 6 | `edit_permission_required` | 编辑权限检查 |

### 1.3 上下文获取：`current_account_with_tenant`

```python
# libs/login.py
def current_account_with_tenant() -> tuple[Account, str]:
    user = _resolve_current_user()  # 从 flask.g._login_user 取
    assert user.current_tenant_id is not None
    return user, user.current_tenant_id
```

这是认证的核心抓手：**从当前请求上下文取出"账号 + 租户 ID"**。

## 2. 代码示例

### 2.1 完整装饰器链示例

```python
from flask import Blueprint
from libs.login import login_required, current_account_with_tenant

bp = Blueprint("demo", __name__)

@bp.post("/apps/<app_id>/secret-action")
@setup_required
@login_required
@account_initialization_required
@with_current_tenant_id
@rbac_permission_required(RBACResourceScope.APP, RBACPermission.APP_DELETE)
def secret_action(app_id: str, current_tenant_id: str):
    # 此时 current_tenant_id 已被装饰器注入到 kwargs
    # RBAC 已通过检查
    user, tenant_id = current_account_with_tenant()
    # 业务逻辑...
    return {"ok": True}
```

### 2.2 认证失败的常见状态码

| 失败原因 | 状态码 | dify 异常 |
|---------|--------|-----------|
| 系统未初始化 | 401 | `NotSetupError` |
| Token 无效/过期 | 401 | `Unauthorized` |
| CSRF 不匹配 | 401 | `check_csrf_token` 失败 |
| 账号未初始化 | 401 | `AccountNotInitializedError` |
| 资源不存在/跨租户 | 404 | `NotFound` |
| 权限不足 | 403 | `Forbidden` |
| 系统功能未启用 | 400 | `NotAllowedCreateWorkspace` |

## 3. 关键要点总结

- dify 的认证流程是**装饰器链** + **上下文注入**的组合
- 装饰器顺序很重要：先 `setup_required` → `login_required` → `rbac_permission_required` → 业务
- `current_account_with_tenant()` 是认证上下文的**唯一官方获取入口**
- `login_required` 内部已经把 CSRF 校验做了，开发者无需重复
- 失败时返回 401（未登录）/ 403（权限）/ 404（跨租户或不存在）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
