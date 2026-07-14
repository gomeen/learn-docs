# 7.3.3 文件存储：本地/S3/MinIO/阿里云/腾讯云/七牛云

> 理解 ruoyi 的文件存储抽象，支持 7+ 种存储后端。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 文件存储的抽象设计
- 理解 FileClient 接口和多种实现
- 学会配置 S3 / MinIO / 阿里云 OSS 等
- 能扩展新的存储后端

## 📚 前置知识

- Spring Boot 基础
- 对象存储（S3、MinIO、OSS）基础
- 策略模式 / 多态

## 1. 核心概念

### 1.1 抽象 FileClient 接口

ruoyi 定义了统一的文件存储接口：

```java
public interface FileClient {
    String upload(byte[] content, String path, String mimeType);
    void delete(String url) throws Exception;
    byte[] getContent(String url) throws Exception;
}
```

### 1.2 多种实现

| 实现类 | 后端 | 配置前缀 |
|--------|------|----------|
| `LocalFileClient` | 本地服务器 | `file.local` |
| `S3FileClient` | AWS S3 | `file.s3` |
| `MinIOFileClient` | MinIO | `file.s3` (S3 协议) |
| `AliyunOSSFileClient` | 阿里云 OSS | `file.aliyun` |
| `TxCOSFileClient` | 腾讯云 COS | `file.tencent` |
| `QiniuKodoFileClient` | 七牛云 Kodo | `file.qiniu` |

### 1.3 FileConfig 配置

```sql
CREATE TABLE infra_file_config (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255),           -- 配置名
    storage VARCHAR(32),         -- 存储类型：local/s3/aliyun/...
    config VARCHAR(4096),        -- JSON 配置
    master BOOLEAN,              -- 是否主配置
    status TINYINT               -- 状态
);
```

**示例**：
```json
{
  "storage": "aliyun",
  "endpoint": "oss-cn-hangzhou.aliyuncs.com",
  "bucket": "my-bucket",
  "accessKey": "...",
  "secretKey": "..."
}
```

## 2. 代码示例

### 2.1 上传文件

```java
@PostMapping("/upload")
@Operation(summary = "上传文件")
public CommonResult<String> uploadFile(@RequestParam("file") MultipartFile file) {
    String url = fileService.uploadFile(file);
    return success(url);
}

public String uploadFile(MultipartFile file) {
    // 1. 校验文件
    validFile(file);
    // 2. 上传到当前主配置
    FileClient client = fileClientFactory.getMasterClient();
    String path = generatePath(file.getOriginalFilename());
    return client.upload(file.getBytes(), path, file.getContentType());
}
```

### 2.2 S3 配置示例

```yaml
yudao:
  file:
    s3:
      endpoint: https://s3.amazonaws.com
      region: us-east-1
      access-key: AKIA...
      secret-key: xxx
      bucket: my-bucket
```

### 2.3 MinIO 配置示例

```yaml
yudao:
  file:
    s3:
      endpoint: http://192.168.1.100:9000
      region: us-east-1
      access-key: minioadmin
      secret-key: minioadmin
      bucket: my-bucket
      path-style-access: true
```

## 3. ruoyi 仓库源码解读

### 3.1 FileController 上传接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/file/FileController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 文件存储")
@RestController
@RequestMapping("/infra/file")
@Validated
public class FileController {

    @Resource
    private FileService fileService;

    @PostMapping("/upload")
    @Operation(summary = "上传文件")
    public CommonResult<String> uploadFile(@RequestParam("file") MultipartFile file) {
        return success(fileService.uploadFile(file));
    }

    @DeleteMapping("/delete")
    public CommonResult<Boolean> deleteFile(@RequestParam("id") Long id) {
        fileService.deleteFile(id);
        return success(true);
    }

    @GetMapping("/get")
    public CommonResult<FileRespVO> getFile(@RequestParam("id") Long id) {
        return success(FileConvert.INSTANCE.convert(fileService.getFile(id)));
    }

    @GetMapping("/page")
    public CommonResult<PageResult<FileRespVO>> getFilePage(@Valid FilePageReqVO pageVO) {
        return success(fileService.getFilePage(pageVO));
    }
}
```

### 3.2 FileClient 抽象

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/framework/file/core/client/`

```java
public interface FileClient {
    /**
     * 上传文件
     */
    String upload(byte[] content, String path, String mimeType);

    /**
     * 删除文件
     */
    void delete(String url) throws Exception;

    /**
     * 获得文件内容
     */
    byte[] getContent(String url) throws Exception;
}
```

### 3.3 FileClientFactory 工厂

```java
public class FileClientFactoryImpl implements FileClientFactory {

    /**
     * 各种 FileClient 实现
     */
    private final Map<Long, FileClient> clients = new HashMap<>();

    public FileClient getFileClient(Long configId) {
        return clients.get(configId);
    }

    public FileClient getMasterClient() {
        // 返回 master = true 的客户端
    }

    public void createOrUpdateFileClient(FileConfigDO config) {
        // 根据 storage 类型创建对应实现
        FileClient client = createClient(config);
        clients.put(config.getId(), client);
    }
}
```

## 4. 关键要点总结

- ruoyi 用接口 + 多实现 + 工厂模式管理多种存储
- 存储后端可动态切换（数据库配置）
- 支持本地、S3、MinIO、阿里云、腾讯云、七牛云
- 通过 `FileClientFactory` 获取对应的客户端
- 文件访问 URL 是公开的，无需鉴权

## 5. 练习题

### 练习 1：基础（必做）

打开 `FileConfigController.java`，列出所有存储配置管理的接口。

### 练习 2：进阶

阅读 `S3FileClient` 实现，理解如何基于 AWS SDK 实现文件上传。

### 练习 3：挑战（选做）

如果要支持"分布式文件系统"（如 FastDFS、HDFS），需要做哪些工作？列出具体步骤和需要修改的类。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/file/FileController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/framework/file/core/client/FileClient.java`
- AWS S3 SDK：https://docs.aws.amazon.com/sdk-for-java/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
