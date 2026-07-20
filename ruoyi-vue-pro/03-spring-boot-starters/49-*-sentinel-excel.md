# 小验证：Sentinel / Excel / WebSocket / IP / 测试

> 覆盖：
- [Sentinel](./44-sentinel.md)
- [Excel](./45-excel.md)
- [WebSocket](./46-websocket.md)
- [IP 解析](./47-ip.md)
- [单测增强](./48-test.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

挑 1～2 个可运行改动，其余做代码定位，覆盖防护、导入导出与实时通道。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` 完成 **必做 + 任选一**：

**必做**
1. **Excel**：用 EasyExcel/项目封装导出一张简单字典或 demo 列表，浏览器/接口下载成功，文件可打开且列正确。
2. 定位 IP 解析或地区工具类的使用点（如登录日志），说明数据来源。

**任选一**
3. **WebSocket**：定位集群方案（Redis Pub/Sub）相关类，描述多节点消息如何扇出。
4. **Sentinel**：找到限流/熔断相关配置或注解接入点，说明与业务接口的绑定方式。
5. **单测**：写或改造一个 `@SpringBootTest` / 切片测试，加载某个 AutoConfiguration 或 Service。

## 提示

- Excel 导出注意权限与数据量。
- WebSocket 验证可用浏览器控制台。
- Sentinel 依赖可能按 profile 关闭，允许代码级完成。

## 验收标准

- [ ] Excel 导出文件可打开且列正确
- [ ] IP 相关代码路径已记录
- [ ] 任选项有代码路径 + 运行或阅读证据
- [ ] 能列出本模块至少 3 个 starter 的职责一句话
- [ ] 无把大文件/密钥提交进仓库

## 延伸（选做）

- 给导出加动态列或下拉字典转换。
- 写一个 WebSocket 推送 demo（单机即可）。
