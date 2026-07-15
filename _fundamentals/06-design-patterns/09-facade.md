# 2.4 外观模式（Facade）

> 外观模式为复杂子系统提供一个统一的高层接口，简化客户端使用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解外观模式的核心（统一入口）
- 区分外观模式与适配器模式
- 在 dify/ruoyi 中识别外观应用
- 知道何时该用外观

## 📚 前置知识

- 02-factory-method.md
- 模块化设计

## 1. 核心概念

### 1.1 外观模式的核心思想

把多个子系统的复杂调用**封装**为一个统一的高级接口，让客户端更简单。

### 1.2 外观 vs 适配器

| 维度 | 外观 | [适配器](./06-adapter.md) |
|------|------|--------|
| 目的 | **简化调用** | 接口转换 |
| 数量 | 1 个高层接口 | 通常多个 |
| 侧重点 | 客户端易用性 | 系统兼容性 |

### 1.3 适用场景

- 系统有多个复杂模块，客户端需要了解很多细节
- 需要分层设计（外观作为层间接口）
- 简化第三方库的调用

## 2. 代码示例

### 2.1 经典外观模式

```python
class CPU:
    def freeze(self): pass
    def jump(self, position): pass
    def execute(self): pass

class Memory:
    def load(self, position, data): pass

class Disk:
    def read(self, sector, size): pass

class ComputerFacade:
    """电脑启动外观——对外只暴露 start()"""
    def __init__(self):
        self.cpu = CPU()
        self.memory = Memory()
        self.disk = Disk()

    def start(self):
        """一键启动——封装 CPU/Memory/Disk 复杂调用"""
        self.cpu.freeze()
        self.memory.load(0, self.disk.read(0, 1024))
        self.cpu.jump(0)
        self.cpu.execute()


# 客户端：只需调 start()
computer = ComputerFacade()
computer.start()
```

### 2.2 数据库访问外观（仓储模式）

```python
class UserRepository:
    """用户仓储——数据库访问外观"""

    def __init__(self, db_session):
        self.db = db_session

    def find_by_id(self, user_id: int) -> dict | None:
        """封装 SQL 查询——客户端无感知"""
        return self.db.query("SELECT * FROM users WHERE id = ?", user_id)

    def find_active_users(self) -> list[dict]:
        return self.db.query("SELECT * FROM users WHERE status = 'active'")

    def create(self, user_data: dict) -> int:
        # 1. 验证
        self._validate(user_data)
        # 2. 加密密码
        user_data["password"] = hash_password(user_data["password"])
        # 3. 插入
        return self.db.insert("users", user_data)
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 WorkflowService（工作流外观）

**文件位置**：`/Users/xu/code/github/dify/api/services/workflow_service.py`
**核心代码**（行 1-50）：

```python
from extensions.ext_database import db
from models.workflow import Workflow

class WorkflowService:
    """工作流服务——外观模式，统一暴露给 controller"""

    def run_workflow(self, workflow_id: str, inputs: dict, user: dict) -> dict:
        """运行工作流——封装多个子系统调用"""
        # 1. 加载工作流（数据库）
        workflow = self._load_workflow(workflow_id)

        # 2. 准备上下文（变量、记忆等）
        context = self._prepare_context(workflow, user)

        # 3. 执行节点（LLM、知识库、工具等）
        result = self._execute_nodes(workflow, inputs, context)

        # 4. 保存结果
        self._save_result(workflow_id, result)
        return result

    def _load_workflow(self, workflow_id: str) -> Workflow:
        return db.session.query(Workflow).filter_by(id=workflow_id).first()

    def _prepare_context(self, workflow, user):
        # 调用多个内部子系统
        ...
```

**解读**：
- `WorkflowService` 把"加载-准备-执行-保存"封装为 `run_workflow()` 一个方法
- Controller 调用 `run_workflow()` 即可，无需了解内部细节
- **整体设计**：用外观模式封装工作流执行的所有子系统

### 3.2 ruoyi 的 AdminService（业务外观）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/user/AdminUserServiceImpl.java`
**核心代码**：

```java
@Service
public class AdminUserServiceImpl implements AdminUserService {
    @Resource
    private AdminUserMapper userMapper;
    @Resource
 private DeptService deptService;
    @Resource
 private RoleService roleService;

    @Override
    @Transactional
    public Long createUser(UserSaveReqVO reqVO) {
        // 1. 校验部门（部门服务）
        deptService.validateDeptList(reqVO.getDeptIds());

        // 2. 校验角色（角色服务）
        roleService.validateRoleList(reqVO.getRoleIds());

        // 3. 插入用户
        AdminUserDO user = ...;
        userMapper.insert(user);

        // 4. 插入用户角色关联
        userRoleMapper.insert(...);

        return user.getId();
    }
}
```

**解读**：
- `AdminUserService` 是外观——封装用户、部门、角色 3 个子系统的协同
- Controller 调用 `createUser()` 一个方法，内部协调多个 Service
- **整体设计**：用 Service 层作为外观，简化 Controller 调用

## 4. 关键要点总结

- 外观 = 统一的高层接口，封装子系统复杂性
- 优点：客户端简单、解耦
- 缺点：违反开闭原则（新增功能要改外观）
- dify 的 `WorkflowService`、ruoyi 的 `*ServiceImpl` 都是外观
- 与适配器区别：外观简化调用，适配器转换接口

## 5. 练习题

### 练习 1：基础
设计一个 `OrderFacade`，封装"下单"涉及的所有子系统（库存、支付、物流、通知）。

### 练习 2：进阶
阅读 dify 的 `WorkflowService`，画出它封装的子系统调用关系。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/workflow_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 《设计模式》第 4 章：外观模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13