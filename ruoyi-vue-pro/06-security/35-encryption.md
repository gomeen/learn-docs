# 35 加密：国密 SM4 / AES

> 详解常见加密算法：对称加密（AES/SM4）、非对称加密（RSA）、哈希（SHA）。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分对称加密、非对称加密、哈希
- 理解 AES 和国密 SM4 的应用场景
- 知道 ruoyi 的加密实践（密码用 BCrypt）
- 能为新项目选择合适的加密方案

## 📚 前置知识

- 05-password-encoder.md
- 密码学基础

## 1. 核心概念

### 1.1 三类加密算法

| 类型 | 用途 | 速度 | 例子 |
|------|------|------|------|
| **对称加密** | 数据加密传输 | 快 | AES、SM4、DES |
| **非对称加密** | 密钥交换、数字签名 | 慢 | RSA、SM2、ECC |
| **哈希** | 数据完整性 | 极快 | SHA-256、SM3、MD5 |

### 1.2 对称加密 vs 非对称加密

**对称加密（AES）**：
```
加密：明文 + 密钥 → 密文
解密：密文 + 密钥 → 明文
特点：加解密用同一个密钥，速度快
```

**非对称加密（RSA）**：
```
加密：明文 + 公钥 → 密文
解密：密文 + 私钥 → 明文
特点：公钥公开，私钥保密，安全性高
```

### 1.3 国密算法

中国国家密码局制定的商用密码标准：
- **SM1**：对称加密（硬件实现，不公开）
- **SM2**：非对称加密（基于 ECC）
- **SM3**：哈希（输出 256 位）
- **SM4**：对称加密（128 位密钥）

**国密应用场景**：
- 政府、金融、军工项目
- 国产化替代（替代 RSA、AES）
- 性能接近 AES

### 1.4 ruoyi 的加密实践

ruoyi 的加密方案：
- **密码**：BCrypt（自适应哈希）
- **Token**：UUID + Redis（不加密）
- **密码字段（DB 存储）**：BCrypt 哈希
- **配置文件（数据库密码）**：可配置 AES 加密

## 2. 代码示例

### 2.1 AES 加密（Java）

```java
// 文件：AesUtil.java
public class AesUtil {

    private static final String KEY = "1234567890123456";  // 16 字节
    private static final String ALGORITHM = "AES/CBC/PKCS5Padding";

    public static String encrypt(String plainText) throws Exception {
        SecretKeySpec keySpec = new SecretKeySpec(KEY.getBytes(), "AES");
        Cipher cipher = Cipher.getInstance(ALGORITHM);
        cipher.init(Cipher.ENCRYPT_MODE, keySpec, new IvParameterSpec(KEY.getBytes()));
        byte[] encrypted = cipher.doFinal(plainText.getBytes());
        return Base64.getEncoder().encodeToString(encrypted);
    }

    public static String decrypt(String cipherText) throws Exception {
        SecretKeySpec keySpec = new SecretKeySpec(KEY.getBytes(), "AES");
        Cipher cipher = Cipher.getInstance(ALGORITHM);
        cipher.init(Cipher.DECRYPT_MODE, keySpec, new IvParameterSpec(KEY.getBytes()));
        byte[] decrypted = cipher.doFinal(Base64.getDecoder().decode(cipherText));
        return new String(decrypted);
    }
}
```

### 2.2 SM4 加密（BouncyCastle）

```java
// 文件：Sm4Util.java
public class Sm4Util {

    private static final String ALGORITHM = "SM4/CBC/PKCS5Padding";

    static {
        // 注册 BouncyCastle
        Security.addProvider(new BouncyCastleProvider());
    }

    public static String encrypt(String plainText, String keyHex) throws Exception {
        Key key = new SecretKeySpec(Hex.decode(keyHex), "SM4");
        Cipher cipher = Cipher.getInstance(ALGORITHM);
        cipher.init(Cipher.ENCRYPT_MODE, key, new IvParameterSpec(new byte[16]));
        byte[] encrypted = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
        return Hex.toHexString(encrypted);
    }
}
```

### 2.3 配置文件加密（ruoyi 的做法）

```yaml
# application.yml
spring:
  datasource:
    password: ENC(AbCdEf123456=)  # 加密后
```

**配置类**：
```java
@Bean
public ConfigDataEnvironmentPostProcessor configDataEnvironmentPostProcessor() {
    return new ConfigDataEnvironmentPostProcessor();
}

// 自定义解密器
public class EncryptablePropertyResolver {
    public String resolve(String value) {
        if (value.startsWith("ENC(") && value.endsWith(")")) {
            String cipher = value.substring(4, value.length() - 1);
            return AesUtil.decrypt(cipher);
        }
        return value;
    }
}
```

## 3. 关键要点总结

- 三类加密：对称（AES/SM4）、非对称（RSA/SM2）、哈希（SHA/SM3）
- **密码必须用 BCrypt**（自适应哈希 + 盐）
- **Token 不需要加密**（UUID 已经够安全）
- 国密用于政府、金融、军工等合规场景
- 配置文件密码用 AES 加密（`ENC()` 前缀）

## 4. 参考资料

- 国密标准：https://www.gmbz.org.cn/
- BouncyCastle：https://www.bouncycastle.org/
- AES 加密模式：https://en.wikipedia.org/wiki/Block_cipher_mode_of_operation

---

**文档版本**：v1.0
**最后更新**：2026-07-13
