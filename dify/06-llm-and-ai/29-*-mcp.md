# 小验证：MCP 协议与 dify 集成

> 覆盖：
> - [20-mcp-overview](./24-mcp-overview.md)
> - [21-mcp-server](./25-mcp-server.md)
> - [22-mcp-client](./26-mcp-client.md)
> - [23-mcp-vs-function-calling](./27-mcp-vs-function-calling.md)
> - [24-mcp-in-dify](./28-mcp-in-dify.md)
>
> 预计：45～90 分钟 · 本地练习或改 dify 仓库

## 背景

MCP 用标准协议暴露工具/资源。验证：说清与 function calling 差异，并定位 dify 集成点或实现最小 server 骨架。

## 需求

1. `NOTES.md` 对比表：MCP vs 传统 Function Calling（传输、发现、鉴权、多主机）。
2. 本地最小 MCP server 骨架（stdio 或伪接口）：列出 tools、执行 1 个 echo 工具（可用官方 SDK 或手写消息循环简化版）。
3. 在 dify 仓库搜索 MCP 相关模块，记录客户端集成入口文件。

## 提示

- 仓库内搜 `mcp` 目录/配置
- 官方 SDK 可选；重点是消息角色与工具登记

## 验收标准

- [ ] 对比表 ≥5 行有效差异
- [ ] echo 工具可本地调用成功（脚本或集成测试）
- [ ] 写出 dify 侧入口路径
- [ ] 无把生产密钥写进 MCP 配置示例

## 延伸（选做）

为 server 增加一个只读 resource（如 `config://version`）。
