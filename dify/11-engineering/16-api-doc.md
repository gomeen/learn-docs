# 11.16 API 文档：OpenAPI / Swagger

> 理解如何用 OpenAPI 描述 HTTP API，并通过 Flask-RESTX 与 Pydantic 让验证、序列化和 Swagger 文档共享同一份契约。

## 🎯 学习目标

完成本文档后，你将能够：

- 区分 OpenAPI 规范与 Swagger 工具生态
- 读懂 OpenAPI 中 paths、operations、parameters、requestBody 和 responses
- 解释 Pydantic 模型如何参与请求验证与 OpenAPI Schema 生成
- 理解 dify 采用的 Flask-RESTX + Pydantic 协作方式
- 按 dify 规范命名 Payload、Query、Response 和分页包装模型
- 运行 dify 的测试与生成命令，验证 Swagger JSON 是否符合预期

## 📚 前置知识

- HTTP 方法、状态码、Header、Query String 和 JSON
- Python 类、类型注解与装饰器
- YAML 或 JSON 基础语法
- Pydantic `BaseModel` 的基本用法
- Flask 路由与 REST API 的基本概念

## 🧭 核心概念

### OpenAPI 是什么

OpenAPI Specification，简称 OAS，是一种与语言无关的 HTTP API 描述规范。
它用 YAML 或 JSON 表达机器可读的 API 契约，例如：

- 服务地址和版本信息
- URL 路径与 HTTP 方法
- Path、Query、Header 参数
- 请求体的媒体类型与结构
- 成功和失败响应
- 可复用的数据 Schema
- 认证方式与安全要求

因为描述是结构化的，同一份 OpenAPI 文档可以驱动文档页面、客户端生成、Mock Server、契约测试和网关配置。
OpenAPI 不执行接口，它描述接口“应该是什么”。

### Swagger 是什么

Swagger 最初是 API 描述规范及配套工具的名称；规范后来发展为 OpenAPI Specification。
今天工程语境中的 Swagger 通常指围绕 OpenAPI 的工具生态，例如：

- **Swagger UI**：把 OpenAPI 渲染成可交互网页
- **Swagger Editor**：编辑和校验 OpenAPI 文档
- **Swagger Codegen**：从契约生成客户端或服务端骨架

可以用一句话区分：**OpenAPI 是规范，Swagger 是实现和使用该规范的一组工具。**
“查看 Swagger”常常意味着打开 Swagger UI，但底层数据仍是 OpenAPI JSON 或 YAML。

### API 文档为什么应当机器可读

纯文字文档容易出现三个问题：字段说明与实现分离、示例无法自动验证、客户端重复手写类型。
机器可读契约可以让工具参与一致性检查：

```text
类型模型 ──> OpenAPI 文档 ──> Swagger UI
   │              │               │
   ├─运行时验证    ├─契约测试       └─人工调试
   └─响应序列化    └─客户端生成
```

理想状态是运行时验证和文档生成共享模型。
如果控制器用一套规则验证、Swagger 用另一套字段字典描述，两者迟早会发生漂移。

### OpenAPI 文档的基本结构

#### openapi 与 info

`openapi` 声明规范版本；`info` 描述 API 标题、业务版本和说明。
注意 API 的业务版本不等于 OpenAPI 规范版本。

#### servers

`servers` 列出调用基地址，可分别描述本地、测试和生产环境。
不要把敏感凭据写入 URL。

#### paths 与 operation

`paths` 以 URL 为键，每个 HTTP 方法对应一次 operation。
operation 通常包含 `summary`、`operationId`、参数、请求体和响应。
稳定且唯一的 `operationId` 对客户端代码生成尤其重要。

#### parameters 与 requestBody

`parameters` 描述位于 path、query、header 或 cookie 的参数。
JSON 请求体通过 `requestBody` 描述，而不是普通 query parameter。
GET 查询条件应标记为 `in: query`，不应被错误文档化为请求体。

#### responses

每个 operation 都必须声明 responses。
除成功响应外，成熟契约还应记录认证失败、资源不存在和验证失败等错误形状。

#### components.schemas

可复用对象放在 `components.schemas`，再通过 `$ref` 引用。
这样可以减少重复，并让请求、响应和客户端共享稳定类型名称。

### Pydantic 如何生成 JSON Schema

Pydantic 模型把 Python 类型、字段约束和描述组织成结构化模型。
调用 `model_json_schema()` 可以得到 JSON Schema；框架或适配层再把它注册进 OpenAPI components。

例如，类型注解可以表达：

- `str`、`int`、`bool` 等基本类型
- `str | None` 等可选值
- `Field(ge=1, le=100)` 等边界
- `Field(description="...")` 等文档说明
- 嵌套 `BaseModel` 与集合类型

“Pydantic 自动生成 OpenAPI”并不意味着 Pydantic 单独生成完整 paths。
更准确地说：Pydantic 生成字段 Schema，Web 框架负责把路由、方法、状态码和模型组装成 OpenAPI 文档。

### dify 的 Flask-RESTX + Pydantic 模式

dify 后端控制器同时使用 Flask-RESTX 与 Pydantic：

- Flask-RESTX 管理 Namespace、Resource、路由装饰器和 Swagger 注册
- Pydantic 定义请求体、查询参数与响应 DTO
- `register_schema_models(...)` 把 Pydantic Schema 注册到 Namespace
- `query_params_from_model(...)` 把 Query 模型转换为 Swagger query 参数
- `register_response_schema_models(...)` 注册响应模型
- `dump_response(...)` 显式验证并序列化响应

这种组合兼顾现有 Flask-RESTX 路由体系与 Pydantic v2 的强类型能力。
核心原则是：**运行时验证和 Swagger 文档连接到同一个 Pydantic 模型。**

### 请求体模型：Payload

非 GET 请求体模型使用 `Payload` 后缀。
典型流程是：定义模型、注册模型、用 `@ns.expect(...)` 生成文档，再用 `model_validate(...)` 验证实际 payload。

不要仅依靠 Swagger 声明输入；控制器必须执行运行时验证。
否则文档写着必填字段，真实接口却可能接受任意数据。

### 查询模型：Query

GET 查询参数模型使用 `Query` 后缀。
通过 `@ns.doc(params=query_params_from_model(QueryModel))` 文档化，再对 `request.args` 执行 `model_validate(...)`。

不能使用 `@ns.expect(...)` 表达 GET query，因为 Flask-RESTX 会把它解释为 request body。
这会生成错误契约，并进一步污染客户端代码生成结果。

### 响应模型：Response

响应 DTO 使用 `Response` 后缀并继承 `ResponseModel`。
响应不仅要写进 `@ns.response(...)` 文档，还要通过 `dump_response(...)` 显式序列化。
这能统一处理对象属性、别名、计算字段和 `datetime` JSON 化。

列表与分页包装分别使用 `ListResponse` 或 `PaginationResponse` 后缀，避免调用者猜测外层字段。

### Schema 是接口契约，不只是展示材料

好的 API 文档应当能回答：

- 字段是否必填，是否可为空？
- 数字、字符串和集合有哪些约束？
- 成功与失败分别返回什么？
- 对外字段名是否与内部属性名不同？
- 分页、排序和过滤参数怎样组合？

因此，改 Schema 与改业务代码一样需要测试。
只确认 Swagger UI “能打开”远远不够，还要检查生成 JSON 中参数位置、请求体和响应引用。

## 💻 代码示例

### 最小 OpenAPI YAML

下面是一个独立、可保存为文件并交给 Swagger UI 的最小契约。

**示例文件**：`examples/openapi/task-api.yaml`  
**示例行号**：第 1-45 行

```yaml
openapi: 3.0.3
info:
  title: Task API
  version: 1.0.0
  description: A minimal API for creating and reading tasks.
servers:
  - url: http://localhost:8000
paths:
  /tasks/{taskId}:
    get:
      summary: Get one task
      operationId: getTask
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Task found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '404':
          description: Task not found
  /tasks:
    post:
      summary: Create a task
      operationId: createTask
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTask'
      responses:
        '201':
          description: Task created
components:
  schemas:
    CreateTask:
      type: object
      required: [title]
      properties:
        title:
          type: string
          minLength: 1
    Task:
      allOf:
        - $ref: '#/components/schemas/CreateTask'
        - type: object
          required: [id, completed]
          properties:
            id: { type: string }
            completed: { type: boolean }
```

**说明**：

- `taskId` 同时声明为 path 参数和 required，这是路径参数的必要约束
- POST 使用 `requestBody`，而不是把 JSON 字段写成 query 参数
- `CreateTask` 被请求和响应复用，`Task` 通过 `allOf` 增加服务端字段
- 示例只声明核心响应；生产接口还应补全错误响应的 JSON Schema

### 从 Pydantic 模型观察 JSON Schema

这个独立示例展示 Pydantic 的职责边界：它生成数据 Schema，不负责定义 HTTP 路径。

**示例文件**：`examples/openapi/pydantic_schema.py`  
**示例行号**：第 1-21 行

```python
import json

from pydantic import BaseModel, Field


class CreateTaskPayload(BaseModel):
    title: str = Field(min_length=1, description="Task title")
    priority: int = Field(default=3, ge=1, le=5)


class TaskResponse(BaseModel):
    id: str
    title: str
    priority: int
    completed: bool = False


def main() -> None:
    schema = CreateTaskPayload.model_json_schema()
    print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
```

**说明**：`min_length`、`ge`、`le` 和 `description` 都会进入生成的 JSON Schema；框架再将该结果挂到对应 API operation 上。

## 🔍 dify 仓库源码解读

### Schema 命名约定

**文件位置**：`/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`  
**核心代码**（第 13-25 行）：

```markdown
- Do not use `@ns.expect(...)` for GET query parameters. Flask-RESTX documents that as a request body.

## Naming

- Request body models: use a `Payload` suffix.
  - Example: `WorkflowRunPayload`, `DatasourceVariablesPayload`.
- Query parameter models: use a `Query` suffix.
  - Example: `WorkflowRunListQuery`, `MessageListQuery`.
- Response models: use a `Response` suffix and inherit from `ResponseModel`.
  - Example: `WorkflowRunDetailResponse`, `WorkflowRunNodeExecutionListResponse`.
- Use `ListResponse` or `PaginationResponse` for wrapper responses.
  - Example: `WorkflowRunNodeExecutionListResponse`, `WorkflowRunPaginationResponse`.
- Keep these models near the controller when they are endpoint-specific. Move them to `fields/*_fields.py` only when shared by multiple controllers.
```

**解读**：

- 第 13 行先指出 GET 参数最危险的文档错误：`@ns.expect` 会生成请求体
- 第 17-23 行用后缀编码模型角色，看到类名即可判断它属于请求体、查询还是响应
- `ListResponse` 与 `PaginationResponse` 区分简单集合和带页信息的包装结构
- 第 25 行给出就近放置原则：端点专用模型靠近控制器，共享模型才移动到 `fields/`
- 命名不只改善阅读，也直接影响 Swagger components 名称和生成客户端中的类型名

### 验证 Swagger 的命令与检查项

**文件位置**：`/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`  
**核心代码**（第 195-210 行）：

````markdown
## Verifying Swagger

For schema and documentation changes, run focused tests and generate Swagger JSON:

```bash
uv run --project . pytest tests/unit_tests/controllers/common/test_schema.py
uv run --project . pytest tests/unit_tests/commands/test_generate_swagger_specs.py tests/unit_tests/controllers/test_swagger.py
uv run --project . dev/generate_swagger_specs.py --output-dir /tmp/dify-openapi-check
```

Inspect affected endpoints with `jq`. Check that:

- GET parameters are `in: query`.
- Request bodies appear only where the endpoint has a body.
- Responses reference the expected `*Response` schema.
````

**解读**：

- 第 201 行先验证 Schema 转换辅助逻辑，反馈范围最小
- 第 202 行验证生成命令和整体 Swagger 契约，防止局部修改破坏全局输出
- 第 203 行把生成物输出到临时目录，便于与基线比较而不污染仓库
- 第 206-210 行要求检查语义，而不只是检查命令退出码
- 这套流程体现 API 文档是可测试构建产物，而不是发布前人工补写的附件

## ✅ 关键要点总结

- OpenAPI 是机器可读的 API 规范，Swagger 是相关工具生态
- Pydantic 根据类型和约束生成 JSON Schema，框架负责组装完整 OpenAPI
- dify 以 Flask-RESTX 管理路由和文档注册，以 Pydantic 管理强类型 DTO
- Payload、Query、Response 后缀让模型角色和生成类型保持清晰
- GET query 不能使用 `@ns.expect(...)`，否则会被描述成请求体
- 修改 API Schema 后必须运行测试、生成 Swagger JSON 并检查参数与响应语义

## 🧪 练习题

### 练习：基础（必做）

扩展最小 OpenAPI YAML，为 `GET /tasks` 增加：

- `completed` 布尔查询参数
- `limit` 参数，范围为 1-100，默认 20
- 返回 `TaskListResponse`，包含 `data` 和 `hasMore`

使用 Swagger Editor 检查语法，并解释为什么这两个参数不能放在 `requestBody`。

### 练习：进阶

使用 Pydantic 定义 `TaskListQuery`、`TaskResponse` 和 `TaskPaginationResponse`。
要求给分页字段添加范围和描述，然后打印每个模型的 `model_json_schema()`，观察 required 和 default 如何变化。

### 练习：挑战（选做）

阅读 `/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md` 的 Request Bodies、Query Parameters 和 Responses 三节。
选择一个 dify 控制器，画出以下链路：

```text
HTTP 输入 -> Pydantic 验证 -> Service -> ResponseModel -> dump_response -> JSON
```

再生成 Swagger JSON，用 `jq` 检查该端点的参数位置、请求体和响应 `$ref`。

## 📖 参考资料

- `/Users/xu/code/github/dify/api/controllers/API_SCHEMA_GUIDE.md`
- `/Users/xu/code/github/dify/api/README.md`
- `/Users/xu/code/github/dify/api/controllers/common/schema.py`
- OpenAPI Specification：https://spec.openapis.org/oas/latest.html
- Swagger Documentation：https://swagger.io/docs/
- Pydantic JSON Schema：https://docs.pydantic.dev/latest/concepts/json_schema/
- Flask-RESTX Swagger Documentation：https://flask-restx.readthedocs.io/en/latest/swagger.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
