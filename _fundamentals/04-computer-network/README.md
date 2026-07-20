# 04 - 计算机网络

> 理解网络才能理解 Web 应用的通信原理：TCP/HTTP/HTTPS 是后端面试必考。

## 模块 4.1 网络分层

- [ ] [1.1 OSI 七层模型](./01-osi.md)
- [ ] [1.2 TCP/IP 四层模型](./02-tcp-ip.md)
- [ ] [1.3 数据包传输过程](./03-packet-flow.md)

## 模块 4.2 应用层协议

- [ ] [2.1 HTTP/1.0 / 1.1 / 2.0 / 3.0 演进](./04-http-versions.md)
- [ ] [2.2 HTTP 完整流程（DNS → TCP → HTTP）](./05-http-flow.md)
- [ ] [2.3 HTTP 状态码完整解析](./06-http-status.md)
- [ ] [2.4 HTTP Header 详解：Cache-Control / CORS / Cookie](./07-http-header.md)
- [ ] [2.5 HTTPS 握手：TLS 1.2 / 1.3](./08-https.md)
- [ ] [2.6 WebSocket 协议](./09-websocket.md)
- [ ] [2.7 DNS 解析过程](./10-dns.md)

## 模块 4.3 传输层

- [ ] [3.1 TCP 三次握手 / 四次挥手](./11-tcp-handshake.md)
- [ ] [3.2 TCP 滑动窗口与拥塞控制](./12-tcp-flow-control.md)
- [ ] [3.3 TCP 粘包与拆包](./13-tcp-sticky.md)
- [ ] [3.4 UDP 协议](./14-udp.md)
- [ ] [3.5 TCP vs UDP 对比](./15-tcp-vs-udp.md)

## 模块 4.4 网络层

- [ ] [4.1 IP 地址与子网掩码](./16-ip-subnet.md)
- [ ] [4.2 IPv4 vs IPv6](./17-ipv4-ipv6.md)
- [ ] [4.3 路由原理：静态路由 / 动态路由](./18-routing.md)
- [ ] [4.4 NAT 与内网穿透](./19-nat.md)

## 模块 4.5 网络安全

- [ ] [5.1 常见网络攻击：CSRF / XSS / SSRF / MITM](./20-network-attacks.md)
- [ ] [5.2 防火墙与 ACL](./21-firewall.md)
- [ ] [5.3 VPN 与代理](./22-vpn-proxy.md)

## 🎯 实战关联

- **Web 开发**：HTTP 协议 → Flask / Spring MVC
- **性能优化**：TCP 调优 / HTTP/2 多路复用
- **安全**：HTTPS / CSRF Token
- **微服务**：服务间通信（HTTP / gRPC）

## 📐 与 `_common` 的分工

| 本目录（Mastery） | 工程公共 [`../../_common/14-api-protocols/`](../../_common/14-api-protocols/) |
|-------------------|-----------------------------------------------------------------------------|
| TCP/HTTP 协议语义、版本演进、Header/状态码详解、HTTPS 握手、WebSocket 协议 | REST 设计、SSE、gRPC 选型；HTTP 工程速查 |

学习顺序建议：先本目录 4.2 应用层协议 → 再 `_common/14` 做接口设计。
