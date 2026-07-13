# 1.4.2 REST API 设计规范与最佳实践

> 掌握 REST 风格 API 的设计原则，能读懂和设计 dify 的所有接口。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 REST 的六大约束
- 掌握 RESTful 资源命名规范
- 设计符合 REST 的 API（路径、HTTP 方法、状态码）
- 识别 dify 中 REST 设计的优点与不足

## 📚 前置知识

- 01-fundamentals/19-http-protocol.md
- 基础 Web 概念

## 1. 核心概念

### 1.1 REST 是什么？

REST（Representational State Transfer）是 Roy Fielding 在 2000 年博士论文中提出的**架构风格**，强调：

| 约束 | 含义 |
|---|---|
| **客户端-服务器** | 前后端分离 |
| **无状态** | 每个请求独立，服务器不保存客户端状态 |
| **可缓存** | 响应可标记可缓存性 |
| **统一接口** | URI 标识资源，HTTP 方法操作资源 |
| **分层系统** | 客户端不感知是否直连服务器（可有代理/CDN） |
| **按需代码** | 可选，支持下发代码（如 JavaScript） |

### 1.2 资源（Resource）命名

REST 的核心是**资源**，用 URI 表示：

```
✅ 良好命名（名词复数）
GET    /apps              列出所有应用
GET    /apps/{id}         获取单个应用
POST   /apps              创建应用
PUT    /apps/{id}         替换应用
PATCH  /apps/{id}         部分更新应用
DELETE /apps/{id}         删除应用

❌ 不良命名（动词、动作）
GET    /getApps
POST   /createApp
POST   /deleteApp
```

**嵌套资源**：

```
GET    /apps/{id}/workflows          列出某应用下的工作流
POST   /apps/{id}/workflows          在某应用下创建工作流
GET    /apps/{id}/workflows/{wid}    获取特定工作流
```

### 1.3 HTTP 方法的语义

| 方法 | 语义 | 幂等 | 安全 | 示例 |
|---|---|---|---|---|
| GET | 查询 | ✓ | ✓ | `GET /apps/123` |
| POST | 创建 | ✗ | ✗ | `POST /apps` |
| PUT | 全量替换 | ✓ | ✗ | `PUT /apps/123` |
| PATCH | 部分更新 | ✗ | ✗ | `PATCH /apps/123` |
| DELETE | 删除 | ✓ | ✗ | `DELETE /apps/123` |

**幂等性**：`PUT /apps/123` 调用 N 次与调用 1 次效果相同（资源被替换成同一内容）。
**安全性**：GET 不会修改服务器状态。

### 1.4 响应设计

**成功的响应**：

```json
// GET /apps/123
{
  "id": "123",
  "name": "Chatbot",
  "mode": "chat"
}

// POST /apps (创建)
HTTP/1.1 201 Created
Location: /apps/123
{
  "id": "123",
  "name": "My App"
}
```

**列表响应（带分页）**：

```json
{
  "data": [...],
  "has_more": true,
  "limit": 20,
  "total": 100,
  "page": 1
}
```

**错误响应**：

```json
{
  "code": "app_not_found",
  "message": "App 123 does not exist",
  "status": 404
}
```

### 1.5 API 版本管理

三种主流方式：

```
# 1. URL 路径版本（推荐）
GET /v1/apps
GET /v2/apps

# 2. Header 版本
GET /apps
Accept: application/vnd.dify.v2+json

# 3. 查询参数（不推荐）
GET /apps?version=2
```

### 1.6 过滤、排序、分页

```
# 过滤
GET /apps?mode=chat&status=active

# 排序
GET /apps?sort=-created_at    # - 表示降序

# 分页
GET /apps?page=1&limit=20            # 偏移分页
GET /apps?limit=20&cursor=eyJpZCI6... # 游标分页（推荐）
```

## 2. 代码示例

### 2.1 完整 REST API 设计

```
# 应用管理
GET    /v1/apps                       列出应用
POST   /v1/apps                       创建应用
GET    /v1/apps/{app_id}              获取应用详情
PUT    /v1/apps/{app_id}              替换应用
PATCH  /v1/apps/{app_id}              更新应用
DELETE /v1/apps/{app_id}              删除应用

# 工作流管理（嵌套资源）
GET    /v1/apps/{app_id}/workflows
POST   /v1/apps/{app_id}/workflows
GET    /v1/apps/{app_id}/workflows/{wid}
DELETE /v1/apps/{app_id}/workflows/{wid}

# 工作流执行（动作）
POST   /v1/apps/{app_id}/workflows/{wid}/run    执行
POST   /v1/apps/{app_id}/workflows/{wid}/stop   停止

# 对话（嵌套资源 + 动作）
GET    /v1/apps/{app_id}/conversations
POST   /v1/apps/{app_id}/chat-messages           发送消息
```

### 2.2 Pydantic 定义 REST 请求/响应模型

```python
from pydantic import BaseModel, Field
from typing import Literal

class CreateAppRequest(BaseModel):
    """POST /v1/apps 请求体。"""
    name: str = Field(..., min_length=1, max_length=255)
    mode: Literal["chat", "completion", "workflow"]
    description: str = ""

class AppResponse(BaseModel):
    """单个应用的响应。"""
    id: str
    name: str
    mode: str
    description: str
    created_at: int  # Unix timestamp

class AppListResponse(BaseModel):
    """GET /v1/apps 响应（含分页）。"""
    data: list[AppResponse]
    has_more: bool
    limit: int
    total: int
    page: int
```

### 2.3 常见错误：动词出现在 URI

```python
# ❌ 错误：把动词放在 URI
@router.post("/createApp")
@router.get("/getAppList")
@router.post("/deleteApp/{id}")

# ✅ 正确：用 HTTP 方法表达动作，URI 只放资源
@router.post("/apps")                       # 创建
@router.get("/apps")                        # 列表
@router.delete("/apps/{id}")                # 删除
```

## 3. dify 仓库源码解读

### 3.1 dify 应用 API 的 REST 设计

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/app/app.py`
**核心代码**（行 1-40）：

```python
from flask_restx import Namespace, Resource

app_ns = Namespace("apps", description="App management APIs")


@app_ns.route("")
class AppListApi(Resource):
    """应用列表。"""
    def get(self):
        """列出当前租户的所有应用。"""
        ...

    def post(self):
        """创建新应用。"""
        ...


@app_ns.route("/<uuid:app_id>")
class AppApi(Resource):
    """单个应用。"""
    def get(self, app_id):
        """获取应用详情。"""
        ...

    def put(self, app_id):
        """更新应用。"""
        ...

    def delete(self, app_id):
        """删除应用。"""
        ...
```

**解读**：
- 第 11、21 行：路径参数用 `<uuid:app_id>` 声明类型，自动校验 UUID
- 第 14、25 行：同一 Resource 类对应同一 URI，HTTP 方法区分动作
- 第 16、27、29 行：方法名直接对应 HTTP 方法
- **关键设计**：dify 用 Flask-RESTX 把同一资源的多个方法集中在一个类里，提高可读性

### 3.2 dify 工作流执行的 REST 设计

**文件位置**：`/Users/xu/code/github/dify/api/controllers/service_api/app/workflow.py`
**核心代码**（行 1-35）：

```python
from flask_restx import Namespace, Resource

workflow_ns = Namespace("workflows", description="Workflow execution")


@workflow_ns.route("/run")
class WorkflowRunApi(Resource):
    """执行工作流。"""

    def post(self):
        """执行工作流（异步，返回 run_id）。

        请求体：
        {
            "inputs": {"query": "hello"},
            "user": "user-001",
            "response_mode": "streaming"  # or "blocking"
        }

        返回：
        - blocking 模式：完整结果
        - streaming 模式：SSE 流
        """
        ...


@workflow_ns.route("/<string:workflow_run_id>/stop")
class WorkflowStopApi(Resource):
    """停止工作流执行。"""

    def post(self, workflow_run_id):
        """停止正在运行的工作流。"""
        ...
```

**解读**：
- 第 12 行：`POST /workflows/run`——动作（run）放在子路径，因为它是"动作"而非资源
- 第 30 行：`POST /workflows/{id}/stop`——同样用子路径表达"停止"动作
- **关键设计**：REST 不强制所有 URI 都是名词，对**无法用 CRUD 表达的动作**（如 run、stop）允许用子路径

## 4. 关键要点总结

- REST 核心：**资源用 URI 标识，操作通过 HTTP 方法表达**
- URI 用**复数名词**：`/apps` 而不是 `/app`
- HTTP 方法语义：GET 查、POST 创、PUT 替、PATCH 改、DELETE 删
- 用 `Location` 头返回新建资源的 URI
- 分页推荐用游标（`cursor`）而非偏移（`page`），大数据量更稳定
- 错误响应统一格式（`code`/`message`/`status`）
- dify 用 Flask-RESTX，把同类资源的多个 HTTP 方法组织在同一 Resource 类

## 5. 练习题

### 练习 1：基础（必做）

设计一套"用户管理"的 REST API：
- 列出用户、获取用户、创建用户、更新用户、删除用户
- 每个端点写出 HTTP 方法 + 路径

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/controllers/console/app/app.py`，找出所有路由，按"资源"分组，画出 dify 应用模块的 API 树。

### 练习 3：挑战（选做）

为 dify 设计"知识库（Dataset）"的 REST API：
- 列出知识库、创建知识库、添加文档、删除文档
- 文档查询（支持向量搜索）
- 写出 OpenAPI 规范（YAML 格式）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/app/app.py`
- `/Users/xu/code/github/dify/api/controllers/service_api/app/workflow.py`
- REST 论文：https://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm
- Microsoft REST API 指南：https://github.com/microsoft/api-guidelines

---

**文档版本**：v1.0
**最后更新**：2026-07-13