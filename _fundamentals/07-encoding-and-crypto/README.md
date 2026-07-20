# 07 - 编码与加密

> 编码（字符集）与加密（密码学）是后端开发必备知识。

## 模块 7.1 字符编码

- [ ] [1.1 ASCII / Latin-1 / Unicode / UTF-8](./01-encoding.md)
- [ ] [1.2 常见编码：GBK / GB2312 / Big5](./02-chinese-encoding.md)
- [ ] [1.3 Base64 编码](./03-base64.md)
- [ ] [1.4 URL 编码（Percent Encoding）](./04-url-encoding.md)
- [ ] [1.5 字符编码常见问题（乱码、emoji）](./05-encoding-issues.md)

## 模块 7.2 序列化

- [ ] [2.1 JSON / YAML / XML / Protobuf](./06-serialization.md)
- [ ] [2.2 MessagePack / BSON / Avro](./07-binary-serialization.md)

## 模块 7.3 加密基础

- [ ] [3.1 哈希算法：MD5 / SHA-1 / SHA-256 / bcrypt](./08-hash.md)
- [ ] [3.2 对称加密：AES / DES / 3DES / SM4](./09-symmetric.md)
- [ ] [3.3 非对称加密：RSA / ECC / SM2](./10-asymmetric.md)
- [ ] [3.4 数字签名与数字证书](./11-digital-signature.md)
- [ ] [3.5 SSL/TLS 握手详解](./12-tls.md)

## 模块 7.4 实战应用

- [ ] [4.1 密码存储：bcrypt / argon2](./13-password-storage.md)
- [ ] [4.2 API 签名：HMAC / Sign](./14-api-signature.md)
- [ ] [4.3 密钥管理：Vault / KMS](./15-key-management.md)
- [ ] [4.4 国产密码算法：SM 系列](./16-sm-crypto.md)

## 🎯 与后端开发的关联

- **JWT**：Base64 + HMAC 签名
- **HTTPS**：TLS + 非对称加密
- **密码存储**：永远不要存明文，必须哈希
- **API 防篡改**：HMAC 签名

## 📐 与 `_common` 的分工

| 本目录（Mastery） | 工程公共 [`../../_common/06-encryption/`](../../_common/06-encryption/) |
|-------------------|------------------------------------------------------------------------|
| 编码、序列化、哈希/对称/非对称/签名/TLS **机制** | 业务选型、密钥管理落地入口（链回本目录原理） |

认证协议（JWT/OAuth）见 [`../../_common/07-authentication/`](../../_common/07-authentication/)。
