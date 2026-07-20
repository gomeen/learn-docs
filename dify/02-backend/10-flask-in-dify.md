# 2.2.7 dify 的 Controller 层设计模式

> 总结 dify Controller 层的设计模式，能独立写一个符合 dify 规范的 Resource。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 dify Controller 层的完整装饰器栈
- 理解 `ExternalApi`、`Namespace`、`Resource` 三层抽象的协作
- 按 API_SCHEMA_GUIDE 规范定义 Pydantic Payload / Query / Response
- 独立实现一个符合 dify 规范的 controller

## 📚 前置知识

- [Flask 基础](./03-flask-basics.md) 至 [自定义错误处理](./09-flask-error-handling.md)（Flask 全套）
- [Flask-RESTX](./06-flask-restx.md)
- [Pydantic 基础](./12-pydantic-basics.md) 至 [Pydantic 配置](./15-pydantic-config.md)（Pydantic 系列）

## 1. 核心概念

### 1.1 dify Controller 的标准模板

```python
@ns.route("/path")
class MyResource(Resource):
    @ns.doc("operation_name")
    @ns.expect(ns.models[RequestPayload.__name__])
    @ns.response(200, "Success", ns.models[ResponseModel.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    @rbac_permission_required(...)
    @get_app_model(mode=None)
    def get(self, current_user: Account, current_tenant_id: str, app_model: App):
        """Docstring"""
        payload = RequestPayload.model_validate(ns.payload or {})
        # ... 业务逻辑
        return dump_response(ResponseModel, result)
```

### 1.2 装饰器顺序的重要性

多层 `@decorator` 叠加时，**从下往上**包一层（原理详见 [装饰器](../01-fundamentals/11-decorator.md)）：

```python
# 装饰器从下往上执行
@A  # 最先执行
@B  # 其次
@C  # 最后（最外层）
def view(): ...
```

**dify 的标准顺序**（从上到下）：

```python
@ns.doc(...)              # 1. Swagger 文档
@ns.expect(...)           # 2. 请求体文档
@ns.response(...)         # 3. 响应文档
@setup_required           # 4. 系统初始化检查
@login_required           # 5. 登录检查
@account_initialization_required  # 6. 账号初始化检查
@enterprise_license_required      # 7. 企业 license 检查
@with_current_user        # 8. 注入 current_user
@with_current_tenant_id   # 9. 注入 current_tenant_id
@rbac_permission_required(...)  # 10. RBAC 权限
@get_app_model(mode=None) # 11. 加载 app_model
def get(...):
```

### 1.3 三层架构：ExternalApi → Namespace → Resource

```
ExternalApi（dify 自定义 Api）
└── Namespace（路由分组）
    └── Resource（端点类）
        └── Method（get/post/put/delete）
            └── Decorators（横切关注点）
```

## 2. 代码示例

### 2.1 完整的 dify 风格 Resource

```python
# === 1. 定义 Pydantic 模型（按规范命名） ===

class ArticleCreatePayload(BaseModel):
    """POST /articles 请求体"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    tags: list[str] | None = None


class ArticleListQuery(BaseModel):
    """GET /articles 查询参数"""
    page: int = Field(default=1, ge=1, le=99999)
    limit: int = Field(default=20, ge=1, le=100)
    tag: str | None = None


class ArticleResponse(BaseModel):
    """文章详情响应"""
    id: str
    title: str
    content: str
    author_id: str
    created_at: datetime


class ArticleListResponse(BaseModel):
    """文章列表响应（分页）"""
    data: list[ArticleResponse]
    total: int
    page: int
    limit: int


# === 2. 注册到 Swagger ===

register_schema_models(console_ns, ArticleCreatePayload, ArticleListQuery)
register_response_schema_models(console_ns, ArticleResponse, ArticleListResponse)


# === 3. 实现 Resource ===

@console_ns.route("/articles")
class ArticleListApi(Resource):
    @console_ns.doc("list_articles")
    @console_ns.doc(description="List all articles")
    @console_ns.doc(params=query_params_from_model(ArticleListQuery))
    @console_ns.response(200, "Success", console_ns.models[ArticleListResponse.__name__])
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        """List articles"""
        args = ArticleListQuery.model_validate(request.args.to_dict(flat=True))
        # ... 查询逻辑
        return dump_response(ArticleListResponse, {
            "data": [...],
            "total": 100,
            "page": args.page,
            "limit": args.limit,
        })

    @console_ns.doc("create_article")
    @console_ns.expect(console_ns.models[ArticleCreatePayload.__name__])
    @console_ns.response(201, "Created", console_ns.models[ArticleResponse.__name__])
    @console_ns.response(403, "Insufficient permissions")
    @setup_required
    @login_required
    @account_initialization_required
    @rbac_permission_required(RBACResourceScope.ARTICLE, RBACPermission.ARTICLE_CREATE)
    def post(self):
        """Create article"""
        payload = ArticleCreatePayload.model_validate(console_ns.payload or {})
        # ... 创建逻辑
        return dump_response(ArticleResponse, article), 201
```

### 2.2 Resource with URL 参数

```python
@console_ns.route("/articles/<uuid:article_id>")
class ArticleDetailApi(Resource):
    @console_ns.doc("get_article")
    @console_ns.response(200, "Success", console_ns.models[ArticleResponse.__name__])
    @console_ns.response(404, "Article not found")
    @setup_required
    @login_required
    @account_initialization_required
    @with_current_user
    def get(self, article_id: str, current_user: Account):
        """Get article detail"""
        article_service = ArticleService()
        article = article_service.get_article(article_id, current_user.current_tenant_id)
        if not article:
            raise ArticleNotFoundError()
        return dump_response(ArticleResponse, article)
```

### 2.3 常见错误：装饰器顺序错误

```python
# ❌ 错误：login_required 在 get_app_model 之前
@login_required
@get_app_model(mode=None)  # 装饰器执行顺序：先 get_app_model，但那时 user 还未注入
def get(self, app_model: App, current_user: Account):
    pass

# ✅ 正确：先注入 user，再注入 app_model
@with_current_user
@with_current_tenant_id
@get_app_model(mode=None)
def get(self, current_tenant_id: str, current_user: Account, app_model: App):
    pass
```

## 3. 关键要点总结

- dify Controller 严格按 **API_SCHEMA_GUIDE** 规范
- 命名约定：`XxxPayload` / `XxxQuery` / `XxxResponse`
- 装饰器顺序固定：Swagger → 系统级 → 上下文注入 → RBAC → 模型加载
- 用 Pydantic 校验（`console_ns.payload` 或 `request.args.to_dict()`）
- 用 `dump_response()` 把 ORM 转 Pydantic Response
- RBAC 权限用枚举（`RBACPermission.APP_EDIT`）而非字符串
- URL 参数用类型转换（`<uuid:app_id>`、`<int:user_id>`）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
