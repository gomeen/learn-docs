# 06 - 加密（应用向）

> 后端业务中的加密**选型与落地**入口。算法与握手的 **Mastery 在学科基础层**，本分类避免与之重复展开。

## 📐 分层

| 内容 | 归属 |
|------|------|
| 哈希 / 对称 / 非对称 / 签名 **原理**、TLS 握手 | [`../../_fundamentals/07-encoding-and-crypto/`](../../_fundamentals/07-encoding-and-crypto/) |
| 字符编码、序列化 | 同上 |
| 业务侧怎么选算法、密钥放哪、和认证如何配合 | **本分类**（可 Minimal 复述 + 链原理） |

## 知识点

> 下列文档偏工程入口；深入机制请先读 fundamentals 对应篇。

- [ ] [6.1 对称加密应用：AES 等](./01-symmetric.md) · 原理详见 [fundamentals 对称加密](../../_fundamentals/07-encoding-and-crypto/09-symmetric.md)
- [ ] [6.2 非对称加密应用：RSA / ECC](./02-asymmetric.md) · 原理详见 [fundamentals 非对称加密](../../_fundamentals/07-encoding-and-crypto/10-asymmetric.md)
- [ ] [6.3 哈希与口令：MD5 / SHA / bcrypt](./03-hash.md) · 原理详见 [fundamentals 哈希](../../_fundamentals/07-encoding-and-crypto/08-hash.md)
- [ ] [6.4 数字签名与证书（应用）](./04-digital-signature.md) · 原理详见 [fundamentals 签名](../../_fundamentals/07-encoding-and-crypto/11-digital-signature.md)
- [ ] [6.5 密钥管理：Vault / KMS / 环境变量](./05-key-management.md) · 亦见 [fundamentals 密钥管理](../../_fundamentals/07-encoding-and-crypto/15-key-management.md)

## 🔗 相关

- 认证（JWT / OAuth）：[`../07-authentication/`](../07-authentication/)
- Web 安全：[`../05-web-security/`](../05-web-security/)

## 🔗 项目特定实现

- **dify（Python）**：见 [`../../dify/05-auth-and-security/`](../../dify/05-auth-and-security/) 安全分类
- **ruoyi（Java）**：见 [`../../ruoyi-vue-pro/06-security/`](../../ruoyi-vue-pro/06-security/)
