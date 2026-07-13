# 6.21 MCP Server 开发（Python）

> 学习如何用 Python 实现一个 MCP Server（暴露 Tools / Resources / Prompts），并理解 dify 中"把 Dify App 暴露为 MCP Server"的实现思路。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `mcp` Python SDK 快速搭建一个 MCP Server
- 区分 stdio / SSE / Streamable HTTP 三种传输的启动方式
- 实现带参数 schema、错误处理、异步逻辑的 Tool
- 理解 dify 中 `api/core/mcp/server/streamable_http.py` 如何把 Dify App 暴露为 MCP Server

## 📚 前置知识

- Python 异步编程（参见 `../01-fundamentals/12-async-asyncio.md`）
- Pydantic 模型基础
- 阅读 6.20 MCP 协议概述（`./20-mcp-overview.md`）

## 1. 核心概念

### 1.1 MCP Server 的两种开发视角

| 视角 | 工具 | 适用 |
| --- | --- | --- |
| **作为工具提供方** | `mcp.server.fastmcp.FastMCP` | 把已有 Python 函数/服务包装成 MCP 工具 |
| **作为应用暴露方** | 自己实现 JSON-RPC handler | dify 的方案——把 Dify App 当成"工具集"对外暴露 |

### 1.2 FastMCP vs 低层 SDK

```mermaid
flowchart TB
    subgraph SDK层次
        A[fastmcp.FastMCP] --> B[mcp.server.Server]
        B --> C[mcp.shared.session.BaseSession]
        C --> D[JSON-RPC over stdio/SSE/HTTP]
    end
```

- **FastMCP**：装饰器风格，3 行代码起一个 server
- **Server**：低层 API，需要手动注册 `list_tools` / `call_tool` handler
- **BaseSession**：负责 JSON-RPC 收发、请求 ID 关联、并发控制

dify 用的是**低层 API**（自己写 handler），因为要把 Dify App 的工作流动态映射成工具。

### 1.3 dify 作为 MCP Server 的实现要点

dify 的 `/api/core/mcp/server/streamable_http.py` 把每个 Dify App 当成"一个 MCP Server"：

1. 把 App 的"用户输入字段（user_input_form）"转成 Tools 的 `inputSchema`
2. 接收到 `tools/call` 请求后调用 `AppGenerateService` 异步执行 App
3. 把执行结果包装成 `CallToolResult`（TextContent / ImageContent / EmbeddedResource）
4. 支持流式进度通知（progress notification）

```python
# 来自 api/core/mcp/server/streamable_http.py 第 18-19 行
STRUCTURED_OUTPUT_MIN_VERSION = "2025-06-18"

def _supports_structured_output(protocol_version: str) -> bool:
    """协议版本 ≥ 2025-06-18 才支持 structuredContent 输出"""
    return protocol_version >= STRUCTURED_OUTPUT_MIN_VERSION
```

## 2. 代码示例

### 2.1 用 FastMCP 暴露多个工具

```python
# 文件：weather_server.py
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("weather-server", version="1.0.0")

@mcp.tool()
async def get_weather(city: str, unit: str = "celsius") -> dict:
    """查询指定城市的天气"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://wttr.in/{city}?format=j1")
        data = resp.json()
    current = data["current_condition"][0]
    return {
        "city": city,
        "temperature_C": current["temp_C"],
        "humidity": current["humidity"],
        "description": current["weatherDesc"][0]["value"],
    }

@mcp.resource("config://rate-limit")
def rate_limit() -> str:
    """暴露只读配置"""
    return "100 req/min"

if __name__ == "__main__":
    # 默认 stdio；想用 HTTP 改为：
    # mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
    mcp.run()
```

**说明**：
- `async def` 函数自动被识别为异步工具
- 类型注解（`city: str`）自动生成 JSON Schema
- `mcp.resource()` 暴露只读数据，客户端通过 `resources/read` 读取

### 2.2 用低层 API 实现一个 Server

```python
# 文件：lowlevel_server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

app = Server("lowlevel-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="echo",
            description="回显输入",
            inputSchema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "echo":
        return [TextContent(type="text", text=arguments["text"])]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

asyncio.run(main())
```

**说明**：
- `Server` 是低层 API，所有 handler 都是 `async def` 函数
- `stdio_server()` 是个 async context manager，把 stdin/stdout 包装成 read/write stream
- `app.run()` 启动 JSON-RPC 收发循环

### 2.3 常见错误：handler 没抛标准异常

```python
# ❌ 错误：抛普通 Exception，客户端收到不明确的错误
@app.call_tool()
async def call_tool(name, arguments):
    raise RuntimeError("tool failed")

# ✅ 正确：抛 McpError，客户端收到结构化错误码
from mcp import McpError
from mcp.types import ErrorData

@app.call_tool()
async def call_tool(name, arguments):
    raise McpError(ErrorData(code=-32603, message="tool failed"))
```

## 3. dify 仓库源码解读

### 3.1 dify App 转 MCP Server 的请求分发

**文件位置**：`/Users/xu/code/github/dify/api/core/mcp/server/streamable_http.py`
**核心代码**（行 30-46）：

```python
def negotiate_protocol_version(header_value: str | None, is_initialize: bool) -> str | None:
    """Resolve the negotiated protocol version for an incoming MCP request.

    The version is taken from the MCP-Protocol-Version header on post-initialize requests.
    Returns the version to use for behavior gating, or None when the client sent an explicit
    but unsupported header (the caller should reply with a JSON-RPC INVALID_REQUEST error).
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
- 第 39-40 行：`initialize` 请求不走 header 校验——版本协商是在 JSON-RPC body 里完成的
- 第 42-43 行：缺 header 时用 `DEFAULT_NEGOTIATED_VERSION`，避免老的客户端（不送 header）被拒
- 第 44-45 行：客户端送了不认识的版本号，返回 `None` 让上层回 `INVALID_REQUEST` 错误
- **整体设计意图**：在"严格遵守规范"和"兼容老客户端"之间做平衡——header 是 hint，body 才是 authoritative

### 3.2 ToolProviderEntity 转 MCP Tool

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/mcp_tool/provider.py`
**核心代码**（行 67-89）：

```python
remote_mcp_tools = [RemoteMCPTool(**tool) for tool in entity.tools]

tools = [
    ToolEntity(
        identity=ToolIdentity(
            author="Anonymous",  # Tool level author is not stored
            name=remote_mcp_tool.name,
            label=I18nObject(en_US=remote_mcp_tool.name, zh_Hans=remote_mcp_tool.name),
            provider=entity.provider_id,
            icon=entity.icon if isinstance(entity.icon, str) else "",
        ),
        parameters=ToolTransformService.convert_mcp_schema_to_parameter(remote_mcp_tool.inputSchema),
        description=ToolDescription(
            human=I18nObject(
                en_US=remote_mcp_tool.description or "", zh_Hans=remote_mcp_tool.description or ""
            ),
            llm=remote_mcp_tool.description or "",
        ),
        output_schema=remote_mcp_tool.outputSchema or {},
        has_runtime_parameters=len(remote_mcp_tool.inputSchema) > 0,
    )
    for remote_mcp_tool in remote_mcp_tools
]
```

**解读**：
- 第 67 行：把远端 MCP 工具反序列化成 Pydantic 模型
- 第 78 行：调用 `ToolTransformService.convert_mcp_schema_to_parameter`——这是 dify 自定义的转换器，把 JSON Schema 转成 dify 内部的 `ToolParameter` 结构
- 第 80-83 行：把 MCP 的 `description` 同时填进"人类可读描述"和"给 LLM 看的描述"两个字段
- 第 86 行：`has_runtime_parameters=True` 表示这个工具有入参，dify UI 才会渲染参数输入表单
- **整体设计意图**：这一段是把"远端 MCP Server 的工具元数据"映射到"dify Tool Provider 的内部模型"，让上层 Agent/Workflow 可以像调用内置工具一样调用 MCP 工具

## 4. 关键要点总结

- 用 `FastMCP` 装饰器风格开发最快；用 `Server` 低层 API 更灵活
- 工具函数可以是 `async def` 也可是普通函数，type hint 自动转 JSON Schema
- 资源（Resources）只读，由 `mcp.resource()` 装饰；提示（Prompts）由 `mcp.prompt()` 装饰
- 启动方式决定传输：`mcp.run()` 默认 stdio，加参数可改 SSE/HTTP
- dify 把 Dify App 暴露成 MCP Server，通过 `streamable_http.py` 把 App 输入字段映射成 Tool 入参
- 协议版本协商在 initialize 请求的 body 里，header 只是 hint

## 5. 练习题

### 练习 1：基础（必做）

用 FastMCP 写一个 `math_server.py`，至少实现 3 个工具（`add` / `subtract` / `multiply`），并在 README 里写明如何用 stdio 启动、如何用 Claude Desktop 接入。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/mcp/server/streamable_http.py` 第 60-100 行的 `handle_mcp_request`，画出"method → handler"的路由表（如 `tools/list` 走哪个分支，`tools/call` 走哪个分支）。

### 练习 3：挑战（选做）

把练习 1 的 math_server 改成 Streamable HTTP 传输（监听 `127.0.0.1:8765`），然后用 `httpx` 写一个客户端：发送 `initialize` 握手、再发 `tools/list`、最后发 `tools/call`。要求处理 SSE 响应流。提示：可以用 `httpx_sse` 库。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/mcp/server/streamable_http.py`
- `/Users/xu/code/github/dify/api/core/tools/mcp_tool/provider.py`
- `/Users/xu/code/github/dify/api/core/mcp/types.py`
- Python MCP SDK：https://github.com/modelcontextprotocol/python-sdk
- MCP Server 示例集合：https://github.com/modelcontextprotocol/servers
- FastMCP 文档：https://github.com/modelcontextprotocol/python-sdk/tree/main/src/mcp/server/fastmcp

---

**文档版本**：v1.0
**最后更新**：2026-07-13