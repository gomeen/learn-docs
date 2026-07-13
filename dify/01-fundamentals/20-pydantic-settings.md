# 1.2.4 `pydantic-settings`：类型安全的配置管理

> 掌握 `pydantic-settings` 库，用类型注解定义配置，自动从环境变量、.env 文件、远程配置中心加载。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `pydantic-settings` 与 `BaseSettings` 的关系
- 用类型注解定义配置项，自动获得类型转换与校验
- 配置多源加载优先级（环境变量 > .env > TOML > 默认值）
- 看懂 dify 中 `DifyConfig` 的设计

## 📚 前置知识

- 01-fundamentals/13-env-vars.md
- 01-fundamentals/12-config-file-format.md
- Pydantic 基础（`BaseModel`）

## 1. 核心概念

### 1.1 为什么用 `pydantic-settings`？

手写环境变量读取有大量样板代码：

```python
# ❌ 手写
host = os.getenv("DB_HOST", "localhost")
port = int(os.getenv("DB_PORT", "5432"))
debug = os.getenv("DEBUG", "false").lower() == "true"
```

`pydantic-settings` 让配置**声明式**：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    debug: bool = False

settings = Settings()
# 自动从环境变量、.env 加载
# 自动类型转换与校验
```

### 1.2 `BaseSettings` 的字段类型与校验

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    # 必填
    secret_key: str = Field(..., min_length=16)

    # 带范围校验
    port: int = Field(default=8000, ge=1, le=65535)

    # 枚举
    log_level: Literal["DEBUG", "INFO", "WARNING"] = "INFO"

    # 列表（逗号分隔）
    allowed_hosts: list[str] = ["localhost"]

    # 嵌套模型
    database: DatabaseSettings
```

### 1.3 多源加载与优先级

`pydantic-settings` 按以下顺序加载（高优先级覆盖低优先级）：

```
1. 命令行参数（如果启用）
2. 环境变量
3. .env 文件
4. secrets 目录（Docker secrets）
5. 自定义 SettingsSource（如 TOML、远程配置中心）
6. 字段默认值
```

### 1.4 自定义配置源：TOML / Apollo / Nacos

dify 的 `DifyConfig` 用 `TomlConfigSettingsSource` 从 TOML 加载，并支持 Apollo、Nacos 远程配置中心：

```python
from pydantic_settings import BaseSettings, TomlConfigSettingsSource

class DifyConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        toml_file="pyproject.toml",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),  # 自定义 TOML 源
            file_secret_settings,
        )
```

## 2. 代码示例

### 2.1 基础配置类

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 数据库
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")

    # 应用
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    allowed_hosts: list[str] = Field(default=["*"], alias="ALLOWED_HOSTS")

settings = Settings()
print(settings.db_host)        # 从 DB_HOST 环境变量加载
print(settings.allowed_hosts)  # 自动解析逗号分隔字符串为 list
```

### 2.2 嵌套配置与分组

```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""

class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0

class Settings(BaseSettings):
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    debug: bool = False

# 通过 DB__HOST 嵌套覆盖
# os.environ["DATABASE__HOST"] = "prod-db"
# os.environ["DATABASE__PORT"] = "5433"
```

### 2.3 常见错误：忘记 `case_sensitive=False`

```bash
# 环境变量名是大写
export db_host=localhost

# ❌ 默认 case_sensitive=True，会读不到
# ✅ 设置 case_sensitive=False 自动转大写匹配
```

## 3. dify 仓库源码解读

### 3.1 dify 的 `DifyConfig` 多源配置

**文件位置**：`/Users/xu/code/github/dify/api/configs/app_config.py`
**核心代码**（行 60-95）：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

from configs.deploy import DeploymentConfig
from configs.enterprise import EnterpriseFeatureConfig, EnterpriseTelemetryConfig
from configs.extra import ExtraServiceConfig
from configs.feature import FeatureConfig
from configs.middleware import MiddlewareConfig
from configs.observability import ObservabilityConfig
from configs.packaging import PackagingInfo
from configs.remote_settings_sources import RemoteSettingsSourceConfig

class DifyConfig(
    PackagingInfo,                  # 包信息
    DeploymentConfig,               # 部署配置
    FeatureConfig,                  # 功能开关
    MiddlewareConfig,               # 中间件配置
    ExtraServiceConfig,             # 额外服务配置
    ObservabilityConfig,            # 可观测性配置
    RemoteSettingsSourceConfig,     # 远程配置源
    EnterpriseFeatureConfig,        # 企业版功能
    EnterpriseTelemetryConfig,      # 企业版遥测
):
    """dify 全局配置：通过 Mixin 模式组合多个 Config 子类。"""
    model_config = SettingsConfigDict(extra="ignore")
```

**解读**：
- 第 15-28 行：通过**多继承 Mixin** 把 9 个子配置组合成单一 `DifyConfig`——每个 Mixin 是一组相关字段
- 第 30 行：`extra="ignore"` 忽略未定义的字段，防止新增环境变量导致启动失败
- **关键设计**：领域分组（数据库、缓存、特性开关…）让每个 Mixin 独立维护

### 3.2 自定义远程配置源

**文件位置**：`/Users/xu/code/github/dify/api/configs/app_config.py`
**核心代码**（行 24-57）：

```python
class RemoteSettingsSourceFactory(PydanticBaseSettingsSource):
    """自定义远程配置源：Apollo / Nacos。"""

    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)

    @override
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        raise NotImplementedError

    @override
    def __call__(self) -> dict[str, Any]:
        current_state = self.current_state
        remote_source_name = current_state.get("REMOTE_SETTINGS_SOURCE_NAME")
        if not remote_source_name:
            return {}

        remote_source: RemoteSettingsSource | None = None
        match remote_source_name:
            case RemoteSettingsSourceName.APOLLO:
                remote_source = ApolloSettingsSource(current_state)
            case RemoteSettingsSourceName.NACOS:
                remote_source = NacosSettingsSource(current_state)
            case _:
                logger.warning("Unsupported remote source: %s", remote_source_name)
                return {}
        ...
```

**解读**：
- 第 8 行：实现 `PydanticBaseSettingsSource` 协议，加入到 pydantic-settings 的加载链
- 第 16-18 行：根据 `REMOTE_SETTINGS_SOURCE_NAME` 切换远程源
- 第 19-26 行：match-case 选择 Apollo 或 Nacos 实现
- **关键设计**：企业级 dify 部署可以通过 Apollo/Nacos 集中管理配置，无需重启即可生效

## 4. 关键要点总结

- `pydantic-settings` 是 Pydantic 的扩展，继承 `BaseSettings` 自动加载环境变量
- 字段类型注解自动驱动类型转换（`str` → `int` / `bool` / `list`）
- `Field(...)` 标记必填字段，`Field(default=X, ge=Y)` 提供校验
- 嵌套配置通过 `__`（双下划线）路径覆盖：`DB__HOST=prod`
- 多源加载优先级：CLI > 环境变量 > .env > secrets > 自定义源 > 默认值
- dify 用 Mixin 模式组合 9 个子配置，支持 TOML/Apollo/Nacos 多源

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `Settings` 类，包含 `db_host`、`db_port`（int）、`debug`（bool）、`secret_key`（必填），从环境变量加载。

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/configs/app_config.py`，列出 `DifyConfig` 继承的所有 Mixin，理解每个 Mixin 负责哪类配置。

### 练习 3：挑战（选做）

实现一个 `YAMLConfigSettingsSource`，让 `pydantic-settings` 能从 YAML 文件加载配置（dify 暂未实现，可以贡献）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/configs/app_config.py`
- `/Users/xu/code/github/dify/api/configs/feature/__init__.py`
- pydantic-settings 文档：https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Apollo 配置中心：https://www.apolloconfig.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13