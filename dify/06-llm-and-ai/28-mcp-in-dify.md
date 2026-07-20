# 6.24 dify 与 MCP 的集成

> 深入理解 dify 在两个方向上对 MCP 的集成：①作为 MCP Client 调用外部 MCP Server 的工具；②作为 MCP Server 把 Dify App 暴露出去。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出 dify MCP 集成的两条路径（Client / Server）及对应代码模块
- 理解 `MCPToolProviderController` 如何把远程 MCP 工具包装成 dify 内部 Tool
- 理解 `MCPTool._invoke` 如何把 MCP 协议结果翻译成 `ToolInvokeMessage`
- 理解 dify App 如何被外部 Claude / Cursor 客户端通过 MCP 协议访问

## 📚 前置知识

- MCP 系列（详见 [MCP 概述](./24-mcp-overview.md)、[MCP Server](./25-mcp-server.md)、[MCP Client](./26-mcp-client.md)、[MCP vs Function Calling](./27-mcp-vs-function-calling.md)）
- Function Calling / 工具路由（详见 [Function Calling](./17-function-calling.md)、[多工具路由](./19-multi-tool-routing.md)）
- Python 异步编程（详见 [async/asyncio](../01-fundamentals/14-async-asyncio.md)）

## 1. 核心概念

### 1.1 双向集成架构

dify 同时是 **MCP Client** 和 **MCP Server**：

```mermaid
flowchart TB
    subgraph 作为 Client
        A1[dify Agent/Workflow] --> A2[MCPToolProviderController]
        A2 --> A3[MCPClient]
        A3 --> A4[外部 MCP Server<br>GitHub/Slack/...]
    end

    subgraph 作为 Server
        B1[外部 MCP Client<br>Claude/Cursor] --> B2[/api/mcp endpoint]
        B2 --> B3[handle_mcp_request]
        B3 --> B4[dify App 工作流]
    end
```

**作为 Client**（`api/core/tools/mcp_tool/`）：
- 用户在 dify UI 添加一个 MCP Server URL
- dify 拉取工具列表，包装成 `MCPToolProviderController`
- Agent 节点和工具节点可以像用内置工具一样调用

**作为 Server**（`api/core/mcp/server/streamable_http.py`）：
- 用户在 dify App 设置里开启"作为 MCP 服务暴露"
- 外部 Claude Desktop / Cursor 通过 Streamable HTTP 连接 dify
- dify 把 App 的"用户输入字段"暴露成工具参数

### 1.2 核心代码模块

| 模块 | 职责 |
| --- | --- |
| `api/core/mcp/mcp_client.py` | 通用 MCP 客户端（连接、传输选择） |
| `api/core/mcp/auth_client.py` | 带 OAuth 重试的客户端 |
| `api/core/tools/mcp_tool/provider.py` | 把远程 MCP 工具转 dify Tool Provider |
| `api/core/tools/mcp_tool/tool.py` | 把 MCP 工具调用结果转 dify ToolInvokeMessage |
| `api/core/mcp/server/streamable_http.py` | dify 作为 MCP Server 的入口 |
| `api/core/mcp/auth/auth_flow.py` | OAuth 授权流程 |

### 1.3 身份转发（Identity Forwarding）

dify Enterprise 版支持把"最终用户身份"转发给 MCP Server：
- 用户在 dify Webapp 调用工作流
- 工作流调用 MCP 工具（如"查我的 GitHub Issue"）
- dify 把 end_user 的 access token 通过 `X-Dify-SSO-Token` header 转发给 GitHub MCP Server
- GitHub MCP Server 用这个 token 访问"该用户"的 GitHub 数据

```python
# 来自 api/core/tools/mcp_tool/tool.py 第 32-35 行
# Custom header used to carry the forwarded SSO access token.
# 选用 X-Dify-SSO-Token 而不是 Authorization，避免和 provider 级 OAuth 冲突。
FORWARDED_IDENTITY_HEADER = "X-Dify-SSO-Token"
```

## 2. 代码示例

### 2.1 在 dify UI 添加一个 MCP Server（伪代码流程）

```python
# 文件：add_mcp_server_flow.py
# 伪代码展示 dify Web 后端处理"添加 MCP Server"请求的完整链路

# 1. 用户在 UI 填表单：
#    name: "GitHub"
#    server_url: "https://api.githubcopilot.com/mcp/"
#    headers: {"Authorization": "Bearer ghp_xxx"}
#    identity_mode: OFF

# 2. Web 后端调用 controller
from controllers.console.app.mcp_server import MCPServerController

controller = MCPServerController()
server = controller.create(
    tenant_id="t_123",
    name="GitHub",
    server_url="https://api.githubcopilot.com/mcp/",
    headers={"Authorization": "Bearer ghp_xxx"},
)

# 3. dify 立即建立连接、拉取工具列表
from core.tools.mcp_tool.provider import MCPToolProviderController
provider = MCPToolProviderController.from_db(server)
tools = provider.get_tools()  # list[MCPTool]
print(f"加载了 {len(tools)} 个工具: {[t.entity.identity.name for t in tools]}")

# 4. 在 Agent 节点中，用户可以像用内置工具一样调用
#    工具节点配置：选择 "GitHub" provider → 选择 "create_issue" tool
#    参数：{"title": "Bug", "body": "..."}
```

### 2.2 调用 MCP 工具（dify 内部代码视角）

```python
# 文件：call_mcp_tool_internal.py
# 这是 dify Agent 节点实际调用 MCP 工具的代码路径

from core.tools.mcp_tool.tool import MCPTool
from core.mcp.auth_client import MCPClientWithAuthRetry

tool: MCPTool = ...  # 通过 provider.get_tool("create_issue") 拿到

# 关键代码在 tool.py 的 invoke_remote_mcp_tool 中：
tool_parameters = {"title": "Bug", "body": "details"}
user_id = "u_123"

# 短事务：拿 credentials 后立即关 session，避免长连接
with Session(db.engine, expire_on_commit=False) as session:
    provider_entity = mcp_service.get_provider_entity(provider_id, tenant_id, by_server_id=True)
    server_url = provider_entity.decrypt_server_url()
    headers = provider_entity.decrypt_headers()

# 再开网络连接，调用 MCP Server
try:
    with MCPClientWithAuthRetry(
        server_url=server_url,
        headers=headers,
        timeout=30.0,
        provider_entity=provider_entity,
    ) as mcp_client:
        result = mcp_client.invoke_tool(
            tool_name="create_issue",
            tool_args=tool_parameters,
        )
except MCPConnectionError as e:
    raise ToolInvokeError(f"Failed to connect to MCP server: {e}")
```

### 2.3 常见错误：以为 dify 只是 MCP Client

```python
# ❌ 错误理解：dify 只是调用 MCP Server
# 其实 dify 也能作为 MCP Server，让外部 Claude Desktop 接入

# ✅ 正确理解：
# - dify 可以加 MCP Server URL 当工具（Client 角色）
# - dify App 也可以暴露成 MCP Server（Server 角色）
# 在 App 设置里切换"MCP Server"开关即可
```

## 3. 关键要点总结

- dify 是双向 MCP 集成：作为 Client 调用外部工具，作为 Server 把 App 暴露给外部
- `MCPToolProviderController` 把远程工具列表转 dify Tool Provider，让 UI 无缝集成
- `MCPTool` 是惰性工具实例——只在调用时才打开 MCP 连接
- `FORWARDED_IDENTITY_HEADER = "X-Dify-SSO-Token"` 用自定义 header 避免和 provider 级 Authorization 冲突
- 协议版本通过字符串比较（"YYYY-MM-DD" 是可排序的）实现向后兼容
- OAuth 重试在 `MCPAuthError` 异常对象里传递 metadata hints（RFC 9728）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
