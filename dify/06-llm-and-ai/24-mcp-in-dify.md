# 6.24 dify 与 MCP 的集成

> 深入理解 dify 在两个方向上对 MCP 的集成：①作为 MCP Client 调用外部 MCP Server 的工具；②作为 MCP Server 把 Dify App 暴露出去。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出 dify MCP 集成的两条路径（Client / Server）及对应代码模块
- 理解 `MCPToolProviderController` 如何把远程 MCP 工具包装成 dify 内部 Tool
- 理解 `MCPTool._invoke` 如何把 MCP 协议结果翻译成 `ToolInvokeMessage`
- 理解 dify App 如何被外部 Claude / Cursor 客户端通过 MCP 协议访问

## 📚 前置知识

- dify Tool Provider 体系（参见 `../01-fundamentals/` 系列）
- 阅读 6.20-6.23 MCP 系列文档
- Python 异步编程（参见 `../01-fundamentals/12-async-asyncio.md`）

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

## 3. dify 仓库源码解读

### 3.1 MCPToolProviderController 工具注册

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/mcp_tool/provider.py`
**核心代码**（行 145-164）：

```python
def get_tools(self) -> list[MCPTool]:
    """
    get all tools
    """
    return [
        MCPTool(
            entity=tool_entity,
            runtime=ToolRuntime(tenant_id=self.tenant_id),
            tenant_id=self.tenant_id,
            icon=self.entity.identity.icon,
            server_url=self.server_url,
            provider_id=self.provider_id,
            headers=self.headers,
            timeout=self.timeout,
            sse_read_timeout=self.sse_read_timeout,
            identity_mode=self.identity_mode,
        )
        for tool_entity in self.entity.tools
    ]
```

**解读**：
- 第 149-163 行：每个 MCP 工具都被包装成 `MCPTool` 实例，**持有** server_url 和 headers——调用时才打开网络连接
- 第 152 行：`ToolRuntime(tenant_id=...)` 创建 dify 内部运行时上下文（用于计费、审计）
- **整体设计意图**：`MCPTool` 是"惰性"的——只在被调用时才发请求，平时只是数据载体。这样可以让 dify 在 UI 列出所有工具而不需要预连接所有 MCP Server。

### 3.2 协议版本协商与结构化输出

**文件位置**：`/Users/xu/code/github/dify/api/core/mcp/server/streamable_http.py`
**核心代码**（行 19-46）：

```python
# Structured tool output (outputSchema + structuredContent) was introduced in MCP 2025-06-18.
STRUCTURED_OUTPUT_MIN_VERSION = "2025-06-18"


def _supports_structured_output(protocol_version: str) -> bool:
    """Return True when the negotiated protocol version supports structured tool output.

    MCP protocol versions are YYYY-MM-DD strings, so lexical comparison equals chronological.
    """
    return protocol_version >= STRUCTURED_OUTPUT_MIN_VERSION


def negotiate_protocol_version(header_value: str | None, is_initialize: bool) -> str | None:
    """Resolve the negotiated protocol version for an incoming MCP request.
    """
    if is_initialize:
        return mcp_types.DEFAULT_NEGOTIATED_VERSION
    # Treat an absent or empty header as "not specified" -> default version.
    if not header_value:
        return mcp_types.DEFAULT_NEGOTIATED_VERSION
    if header_value not in mcp_types.SERVER_SUPPORTED_PROTOCOL_VERSIONS:
        return None
    return header_value
```

**解读**：
- 第 19 行：硬编码版本常量——因为协议版本是日期字符串（"YYYY-MM-DD"），用字符串比较即可判断先后
- 第 26 行：字符串比较替代 `datetime` 解析，避免不必要的复杂度（注释里解释了原因）
- 第 39-40 行：`initialize` 请求不走 header 校验，因为版本协商在 JSON-RPC body 里
- 第 44-45 行：返回 `None` 让上层回 JSON-RPC `INVALID_REQUEST` 错误
- **整体设计意图**：dify 作为 Server 时，必须能处理"老客户端送老版本"和"新客户端送新版本"两种情况——这套函数是协议兼容性的核心

## 4. 关键要点总结

- dify 是双向 MCP 集成：作为 Client 调用外部工具，作为 Server 把 App 暴露给外部
- `MCPToolProviderController` 把远程工具列表转 dify Tool Provider，让 UI 无缝集成
- `MCPTool` 是惰性工具实例——只在调用时才打开 MCP 连接
- `FORWARDED_IDENTITY_HEADER = "X-Dify-SSO-Token"` 用自定义 header 避免和 provider 级 Authorization 冲突
- 协议版本通过字符串比较（"YYYY-MM-DD" 是可排序的）实现向后兼容
- OAuth 重试在 `MCPAuthError` 异常对象里传递 metadata hints（RFC 9728）

## 5. 练习题

### 练习 1：基础（必做）

阅读 `/Users/xu/code/github/dify/api/core/mcp/types.py` 第 26-32 行，画出三个协议版本（`LATEST_PROTOCOL_VERSION` / `SERVER_LATEST_PROTOCOL_VERSION` / `DEFAULT_NEGOTIATED_VERSION`）的关系图，并解释为什么 dify Client 和 Server 各有一个 `LATEST` 常量。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/tools/mcp_tool/tool.py` 第 67-110 行 `_invoke` 方法，画出"MCP `CallToolResult.content` → dify `ToolInvokeMessage`"的类型映射表。包括：
- `TextContent` → ？
- `ImageContent` → ？
- `AudioContent` → ？
- `EmbeddedResource`（TextResourceContents）→ ？
- `EmbeddedResource`（BlobResourceContents）→ ？
- `result.structuredContent` → ？

### 练习 3：挑战（选做）

实现一个 `MCPUsageTracker`，包装 `MCPClientWithAuthRetry`，统计每个 MCP Server 的：
1. 调用次数、成功率、平均延迟
2. 消耗的 token（从 `result.meta` 里提取，参见 `tool.py` 第 153-240 行）
3. 错误分布（按 `MCPAuthError` / `MCPConnectionError` 等分类）

要求：使用 dify 的 `extensions.ext_redis` 把统计数据写入 Redis，每分钟聚合一次并暴露给 Prometheus。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/tools/mcp_tool/provider.py`
- `/Users/xu/code/github/dify/api/core/tools/mcp_tool/tool.py`
- `/Users/xu/code/github/dify/api/core/mcp/server/streamable_http.py`
- `/Users/xu/code/github/dify/api/core/mcp/types.py`
- `/Users/xu/code/github/dify/api/core/mcp/auth_client.py`
- `/Users/xu/code/github/dify/api/core/mcp/auth/auth_flow.py`
- MCP 官方规范：https://modelcontextprotocol.io/specification/2025-06-18
- dify MCP 集成文档（社区）：https://docs.dify.ai/guides/tools/mcp

---

**文档版本**：v1.0
**最后更新**：2026-07-13