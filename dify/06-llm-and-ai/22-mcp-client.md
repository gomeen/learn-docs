# 6.22 MCP Client 集成

> 学习如何用 Python 集成 MCP Client，理解 dify 中 `MCPClient` / `MCPClientWithAuthRetry` 的设计，掌握 OAuth 401 自动重试机制。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 Python MCP SDK 写一个 Client 连接远程 MCP Server
- 理解 dify `MCPClient` 上下文管理器模式和 SSE/Streamable HTTP 自动选择
- 理解 OAuth 401 时的自动 token 刷新重试机制
- 掌握 `tools/list` 和 `tools/call` 的请求/响应结构

## 📚 前置知识

- Python 异步编程（详见 [async/asyncio](../01-fundamentals/12-async-asyncio.md)）
- OAuth 2.0 基础（access token / refresh token；详见 [OAuth 2.0](../../_common/07-authentication/05-oauth2.md)、[Token 刷新](../../_common/07-authentication/04-token-refresh.md)）
- MCP 协议与 Server（详见 [MCP 概述](./20-mcp-overview.md)、[MCP Server](./21-mcp-server.md)）

## 1. 核心概念

### 1.1 MCP Client 的生命周期

```mermaid
sequenceDiagram
    participant App as Host App
    participant Client as MCPClient
    participant Transport
    participant Server as MCP Server

    App->>Client: with MCPClient(url) as c
    Client->>Transport: open stream
    Transport->>Server: POST initialize
    Server-->>Transport: capabilities
    Client->>Server: notifications/initialized
    Note over Client,Server: connected
    App->>Client: c.list_tools()
    Client->>Server: tools/list
    Server-->>Client: tools[]
    App->>Client: c.invoke_tool("add", {a:1,b:2})
    Client->>Server: tools/call
    Server-->>Client: CallToolResult
    App->>Client: exit context
    Client->>Transport: close
```

### 1.2 dify 的双层 Client 设计

dify 把 Client 拆成两层：

| 类 | 文件 | 职责 |
| --- | --- | --- |
| `MCPClient` | `api/core/mcp/mcp_client.py` | 基础连接、`list_tools` / `invoke_tool` |
| `MCPClientWithAuthRetry` | `api/core/mcp/auth_client.py` | 继承 `MCPClient`，拦截 `MCPAuthError`，刷新 token 后重试 |

这种"装饰器式继承"让 OAuth 重试逻辑独立可测，基础 Client 不依赖数据库。

### 1.3 SSRF 防护

MCP 客户端要请求外部 URL，存在 SSRF（服务端请求伪造）风险。dify 在 `api/core/mcp/utils.py` 用 `create_ssrf_proxy_mcp_http_client` 包装 httpx 客户端，让所有出站请求经过 SSRF 代理：

```python
# 来自 api/core/mcp/client/streamable_client.py 第 34 行
from core.mcp.utils import create_ssrf_proxy_mcp_http_client, ssrf_proxy_sse_connect
```

## 2. 代码示例

### 2.1 用官方 SDK 写 MCP Client

```python
# 文件：simple_client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 用 stdio 启动 "python weather_server.py" 作为子进程
    params = StdioServerParameters(command="python", args=["weather_server.py"])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # 1) 握手

            tools = await session.list_tools()  # 2) 列工具
            print("Available tools:", [t.name for t in tools.tools])

            # 3) 调工具
            result = await session.call_tool(
                "get_weather",
                {"city": "Tokyo"},
            )
            for content in result.content:
                print(content.text)

asyncio.run(main())
```

**说明**：
- `stdio_client` 启动子进程并接管其 stdin/stdout
- `ClientSession` 负责 JSON-RPC 收发，必须先 `initialize()`
- `list_tools()` 和 `call_tool()` 是高频 API

### 2.2 用 dify 风格的 MCPClient

```python
# 文件：dify_style_client.py
import asyncio
from core.mcp.mcp_client import MCPClient  # 实际路径省略

async def main():
    headers = {"Authorization": "Bearer xxx"}
    # URL 以 /mcp 结尾走 Streamable HTTP，以 /sse 结尾走 SSE
    with MCPClient(
        server_url="https://example.com/mcp",
        headers=headers,
        timeout=30.0,
        sse_read_timeout=60.0,
    ) as client:
        tools = client.list_tools()
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")
        result = client.invoke_tool("get_weather", {"city": "Tokyo"})
        for content in result.content:
            if hasattr(content, "text"):
                print(content.text)

asyncio.run(main())
```

**说明**：
- `MCPClient` 实现了 `__enter__` / `__exit__`，可以用 `with` 语句
- `list_tools()` 返回 `list[Tool]`（dify 的 MCP 类型，不是官方 SDK 的）
- URL 末尾的 `/mcp` / `/sse` 决定传输方式（参见 `mcp_client.py` 第 67-72 行的逻辑）

### 2.3 常见错误：忘记调 initialize

```python
# ❌ 错误：直接调 list_tools，会抛 "Session not initialized"
async with ClientSession(read, write) as session:
    tools = await session.list_tools()  # RuntimeError

# ✅ 正确：先握手
async with ClientSession(read, write) as session:
    await session.initialize()
    tools = await session.list_tools()
```

## 3. dify 仓库源码解读

### 3.1 MCPClient 连接建立与 fallback

**文件位置**：`/Users/xu/code/github/dify/api/core/mcp/mcp_client.py`
**核心代码**（行 58-79）：

```python
def _initialize(
    self,
):
    """Initialize the client with fallback to SSE if streamable connection fails"""
    connection_methods: dict[str, Callable[..., AbstractContextManager[Any]]] = {
        "mcp": streamablehttp_client,
        "sse": sse_client,
    }

    parsed_url = urlparse(self.server_url)
    path = parsed_url.path or ""
    method_name = path.rstrip("/").split("/")[-1] if path else ""
    if method_name in connection_methods:
        client_factory = connection_methods[method_name]
        self.connect_server(client_factory, method_name)
    else:
        try:
            logger.debug("Not supported method %s found in URL path, trying default 'sse' method.", method_name)
            self.connect_server(sse_client, "sse")
        except (MCPConnectionError, ValueError):
            logger.debug("MCP connection failed with 'sse', falling back to 'mcp' method.")
            self.connect_server(streamablehttp_client, "mcp")
```

**解读**：
- 第 62-65 行：dict 充当"传输方式 → 工厂函数"的查找表
- 第 67-69 行：从 URL path 末尾提取"方法名"，例如 `https://x.com/foo/mcp` → `mcp`
- 第 70-72 行：URL 后缀明确指定时直接用
- 第 74-79 行：URL 没指定时先试 SSE（旧协议），失败再 fallback 到 Streamable HTTP（新协议）
- **整体设计意图**：兼容老 MCP Server（只支持 SSE）和新 Server（Streamable HTTP），自动适配无需用户配置

### 3.2 OAuth 401 自动重试

**文件位置**：`/Users/xu/code/github/dify/api/core/mcp/auth_client.py`
**核心代码**（行 67-92）：

```python
def _handle_auth_error(self, error: MCPAuthError) -> None:
    """
    Handle authentication error by refreshing tokens.

    This method creates a short-lived database session only when authentication
    retry is needed, minimizing database connection hold time.
    """
    if self.forward_identity_active:
        raise error
    if not self.provider_entity:
        raise error
    if self._has_retried:
        raise error

    self._has_retried = True

    try:
        # Create a temporary session only for auth retry
        # This session is short-lived and only exists during the auth operation

        from services.tools.mcp_tools_manage_service import MCPToolManageService

        with Session(db.engine) as session, session.begin():
            mcp_service = MCPToolManageService(session=session)

            # Perform authentication using the service's auth method
            # Extract OAuth metadata hints from the error
            mcp_service.auth_with_actions(
                self.provider_entity,
                self.authorization_code,
                resource_metadata_url=error.resource_metadata_url,
                scope_hint=error.scope_hint,
            )
```

**解读**：
- 第 80-81 行：如果当前是"用户身份转发"模式（forward identity），不重试——因为 forwarded identity 是 user 自己的，不能自动刷新
- 第 84-85 行：没有 `provider_entity`（缺 OAuth 配置）也不重试
- 第 86-87 行：`_has_retried` 标志位防止无限重试循环（最多重试 1 次）
- 第 95-96 行：用 `with Session(db.engine) as session, session.begin()` 短事务——只在需要重试时才占数据库连接，避免长连接
- 第 100-105 行：调用 `auth_with_actions` 把异常里解析出来的 `resource_metadata_url` 和 `scope_hint` 传给 OAuth 服务
- **整体设计意图**：把 OAuth 重试做成"惰性的"——只有真出错才连数据库，正常请求零开销

## 4. 关键要点总结

- MCP Client 用 `async with` 管理连接生命周期，必须先 `initialize()`
- URL 末尾的 `/mcp` / `/sse` 是传输方式约定（也可省略，自动 fallback）
- dify 的 `MCPClient` 是同步上下文管理器（`with` 而非 `async with`），内部把 stream 包装成 async
- OAuth 401 重试通过异常对象传递 metadata hints（resource_metadata / scope），遵循 RFC 9728
- `MCPClientWithAuthRetry` 用"装饰器式继承"扩展基础 Client，重试只在真出错时占数据库连接

## 5. 练习题

### 练习 1：基础（必做）

写一个 async 函数 `fetch_tools(url: str, headers: dict) -> list[Tool]`，用官方 MCP SDK 连接一个 SSE MCP Server，返回工具列表。捕获 `MCPAuthError` 并打印友好提示。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/mcp/mcp_client.py` 第 33-43 行的 header 占位符替换逻辑。如果 dify 接收到上游 HTTP header `X-Tenant-Id: t_123`，而 MCP provider 配置的 header 是 `{{request.headers.X-Tenant-Id}}`，最终发往 MCP Server 的 header 是什么？

### 练习 3：挑战（选做）

修改 `MCPClientWithAuthRetry._handle_auth_error`，让它支持"连续 401 重试 N 次"而不是只重试 1 次。要求：
1. 每次重试前先关闭旧连接（`self._exit_stack.close()`）
2. 每次重试后等一个递增的 backoff（1s, 2s, 4s, ...）
3. 用 `asyncio` 实现（注意现有代码是同步的，需要重构）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/mcp/mcp_client.py`
- `/Users/xu/code/github/dify/api/core/mcp/auth_client.py`
- `/Users/xu/code/github/dify/api/core/mcp/error.py`
- `/Users/xu/code/github/dify/api/core/mcp/utils.py`
- MCP Python SDK Client 文档：https://github.com/modelcontextprotocol/python-sdk/tree/main/src/mcp/client
- RFC 9728 OAuth Resource Server Metadata：https://datatracker.ietf.org/doc/html/rfc9728

---

**文档版本**：v1.0
**最后更新**：2026-07-13