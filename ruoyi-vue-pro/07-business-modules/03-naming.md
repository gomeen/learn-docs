# 7.1.3 Controller / Service / DAO 命名规范

> 掌握 ruoyi 强约定的命名规范，能在 IDE 中快速搜索和理解代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 中 Controller / Service / Mapper 的命名规范
- 理解对象命名的强约定（DO / VO / DTO）
- 学会在 `convert` 包中定义转换器
- 通过命名快速判断类的职责

## 📚 前置知识

- Java 命名规范
- 模块结构 / 分层（详见 [模块结构](./01-module-structure.md)、[MVC 分层](./02-mvc-layers.md)）

## 1. 核心概念

### 1.1 ruoyi 的命名铁律

通过 `package-info.java` 写明的命名规范：

```
1. Controller URL：以 /admin-api/ 开头
2. DataObject：以 DO 结尾
3. VO：请求用 ReqVO 结尾，响应用 RespVO 结尾
4. Convert：以 Convert 结尾
5. Service 接口：以 Service 结尾
6. Service 实现：以 ServiceImpl 结尾
7. Mapper：以 Mapper 结尾
8. 枚举：以 Enum 结尾
9. 异常：以 Exception 结尾
```

### 1.2 各层类的命名示例

| 层级 | 命名示例 | 含义 |
|------|----------|------|
| Controller | `UserController` | 用户 HTTP 接口 |
| Service 接口 | `AdminUserService` | 用户服务接口 |
| Service 实现 | `AdminUserServiceImpl` | 用户服务实现 |
| Mapper | `AdminUserMapper` | 用户数据访问 |
| DO | `AdminUserDO` | 用户数据库对象 |
| 请求 VO | `UserSaveReqVO` | 用户保存请求 |
| 响应 VO | `UserRespVO` | 用户响应 |
| 转换器 | `UserConvert` | 对象转换 |
| 枚举 | `SexEnum` | 性别枚举 |
| 异常 | `UserNotFoundException` | 用户未找到 |

### 1.3 DO / VO / DTO 的区别

```
DO（Data Object）       → 数据库表映射
VO（View Object）       → 视图对象（HTTP 请求/响应）
DTO（Data Transfer）    → 内部数据传输
BO（Business Object）   → 业务对象（聚合多个 DO）
```

**举例**：用户详情页要展示"用户 + 角色 + 部门"
- `AdminUserDO`（用户表）
- `RoleDO`（角色表）
- `DeptDO`（部门表）
- 转换为 `UserRespVO`（包含 username、deptName、roleNames）

## 2. 代码示例

### 2.1 完整的命名示例（以用户模块为例）

```
yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/
├── controller/admin/user/
│   ├── UserController.java
│   └── vo/
│       ├── UserSaveReqVO.java       // 创建/修改请求
│       ├── UserRespVO.java          // 详情响应
│       ├── UserPageReqVO.java       // 分页查询请求
│       └── UserSimpleRespVO.java    // 精简响应（下拉用）
├── service/user/
│   ├── AdminUserService.java        // 接口
│   └── AdminUserServiceImpl.java    // 实现
├── convert/user/
│   └── UserConvert.java             // 对象转换
├── dal/
│   ├── dataobject/user/
│   │   └── AdminUserDO.java
│   └── mysql/user/
│       └── AdminUserMapper.java
└── enums/common/
    └── SexEnum.java
```

### 2.2 ReqVO 的典型结构

```java
@Schema(description = "管理后台 - 用户创建/修改 Request VO")
@Data
public class UserSaveReqVO {

    @Schema(description = "用户编号", example = "1024")
    private Long id;

    @Schema(description = "用户账号", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "用户账号不能为空")
    private String username;

    @Schema(description = "用户昵称", requiredMode = Schema.RequiredMode.REQUIRED)
    private String nickname;

    @Schema(description = "手机号码")
    private String mobile;

    @Schema(description = "部门编号", requiredMode = Schema.RequiredMode.REQUIRED)
    private List<Long> deptIds;
}
```

## 3. ruoyi 仓库源码解读

### 3.1 UserController 的命名规范

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`

**核心代码**（行 41-50）：

```java
@Tag(name = "管理后台 - 用户")
@RestController
@RequestMapping("/admin-api/system/user")  // /admin-api 前缀
@Validated
public class UserController {

    @Resource
    private AdminUserService userService;  // Service 接口
    @Resource
    private DeptService deptService;
    // ...
}
```

**解读**：
- 第 2 行：`@RestController` 标记为 REST 控制器
- 第 3 行：`/admin-api/system/user` 路由以 `/admin-api` 开头
- 第 7-8 行：依赖接口 `AdminUserService`（不是实现类）

### 3.2 VO 文件的命名

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/vo/user/`

**核心代码**（查看文件列表）：

```
vo/user/
├── UserSaveReqVO.java         # 创建/修改用户请求
├── UserRespVO.java            # 用户详情响应
├── UserPageReqVO.java         # 用户分页请求
├── UserUpdatePasswordReqVO.java
├── UserUpdateStatusReqVO.java
├── UserImportExcelVO.java
├── UserImportRespVO.java
└── UserSimpleRespVO.java      # 用户精简响应（下拉用）
```

**解读**：
- 所有请求以 `ReqVO` 结尾
- 所有响应以 `RespVO` 结尾
- `Simple`：精简版（用于下拉框、列表项）
- 命名非常语义化，能从文件名看出用途

### 3.3 AdminUserService 接口与实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/`

**核心代码**（查看文件结构）：

```
service/user/
├── AdminUserService.java          # 接口：IUserService
└── AdminUserServiceImpl.java      # 实现：UserServiceImpl
```

**接口代码**：

```java
public interface AdminUserService {
    Long createUser(UserSaveReqVO reqVO);
    void updateUser(UserSaveReqVO reqVO);
    void deleteUser(Long id);
    void deleteUserList(List<Long> ids);
    void updateUserPassword(Long id, String password);
    void updateUserStatus(Long id, Integer status);
    AdminUserDO getUser(Long id);
    List<AdminUserDO> getUserList(Collection<Long> ids);
    PageResult<AdminUserDO> getUserPage(UserPageReqVO reqVO);
    List<AdminUserDO> getUserListByNickname(String nickname);
    // ...
}
```

**实现类**：

```java
@Service
@Validated
public class AdminUserServiceImpl implements AdminUserService {
    // 实现所有方法
}
```

**解读**：
- **接口**：`AdminUserService`（不是 `IUserService`，不用 `I` 前缀）
- **实现**：`AdminUserServiceImpl`（`Impl` 后缀）
- Controller 注入接口，不注入实现类（依赖倒置）

## 4. 关键要点总结

- ruoyi 通过 `package-info.java` 写下命名铁律
- Controller 路由以 `/admin-api/` 开头
- DO / ReqVO / RespVO / Convert 都有强约定后缀
- Service 接口和实现分离（接口用 `Service`，实现用 `ServiceImpl`）
- 通过命名就能猜出类的职责

## 5. 练习题

### 练习 1：基础（必做）

打开 `yudao-module-mall/yudao-module-product/`，列出 `controller/admin/`、`service/`、`dal/dataobject/` 三个目录下的文件，理解命名规范。

### 练习 2：进阶

阅读 `package-info.java`（在 `yudao-module-mall` 下），总结 mall 模块的命名规范和注意事项。

### 练习 3：挑战（选做）

思考：为什么 ruoyi 的 Service 接口名称是 `AdminUserService`（带 `Admin` 前缀），而有些项目使用 `IUserService`（带 `I` 前缀）？哪种更好？说出理由。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/package-info.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserService.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
