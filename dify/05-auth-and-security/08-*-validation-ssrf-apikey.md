# 小验证：输入校验 · SSRF · API Key

> 覆盖：
> - [19-input-validation](./05-input-validation.md)
> - [20-ssrf-in-dify](./03-ssrf-in-dify.md)
> - [28-api-key](./06-api-key.md)
> - [29-api-key-in-dify](./07-api-key-in-dify.md)
>
> 预计：60～90 分钟 · 本地练习或改 dify 仓库

## 背景

SSRF 与 API Key 是 dify 作为「会代用户出站请求」的平台必须收紧的点。验证：定位 ssrf_proxy 与 API Key 校验，完成一项硬化或复现实验。

## 需求

1. 阅读 `api/core/helper/ssrf_proxy.py`（路径以仓库为准），在 `NOTES.md` 总结：拦截了什么、如何配置白名单/代理。
2. 本地写 5 个 URL 用例（metadata IP、localhost、正常 https、带重定向的恶意目标等），标注哪些应被拦（不必真打内网）。
3. 定位 API Key 创建与校验代码，说明存储是否哈希、权限范围字段在哪。
4. 小改动（选一）：为某用户输入增加长度/格式校验；或为 API Key 相关错误信息去掉敏感细节；或补充测试断言「私钥不落日志」。

## 提示

- SSRF：`api/core/helper/ssrf_proxy.py`
- API Key：`api/services/api_key_service.py` 及 controllers
- 输入校验与 Pydantic/RESTX 层结合

## 验收标准

- [ ] SSRF 机制总结可读，含文件锚点
- [ ] 5 个 URL 用例有期望结果
- [ ] API Key 存储与校验路径清楚
- [ ] 至少 1 个安全向小改动或测试描述落地

## 延伸（选做）

研究 open redirect / 文件 URL 是否也走同一防护层。
