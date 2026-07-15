# 11.6.4 多租户切换

> 掌握 ruoyi 的多租户（Multi-Tenant）实现：SaaS 模式下不同企业数据隔离。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解多租户的概念和数据隔离策略
- 掌握 ruoyi 前端的租户切换实现
- 理解请求头中的 tenant-id 传递机制
- 在 ruoyi 中处理租户相关的业务逻辑

## 📚 前置知识

- Pinia（详见 [Pinia](./06-pinia.md)）
- Axios（详见 [Axios](./19-axios.md)）
- 多租户模型（详见 [多租户](../../_common/08-authorization/05-multi-tenant.md)）

## 1. 核心概念

### 1.1 什么是多租户？

多租户（Multi-Tenancy）= **一套系统服务多个客户（租户）**，每个租户的数据互相隔离。

典型场景：
- SaaS 平台（一个系统卖给多个企业）
- 多公司/多部门共享一套后端

### 1.2 三种数据隔离策略

| 策略 | 实现 | 优缺点 |
|------|------|--------|
| **独立数据库** | 每个租户一个 schema | 隔离好、迁移方便、成本高 |
| **共享数据库 + 独立 Schema** | 每个租户一个 schema | 平衡方案 |
| **共享数据库 + tenant_id 字段** | 所有表加 tenant_id 列 | 成本最低、应用层过滤 |

**ruoyi 采用第三种**：所有表加 `tenant_id` 字段，应用层根据 `tenant_id` 过滤数据。

### 1.3 租户切换的数据流

```
用户登录
 ↓
后端返回用户所属租户列表
 [
   { id: 1, name: '芋道公司' },
   { id: 2, name: '测试租户' }
 ]
 ↓
前端存到 useTenantStore.tenantList
 ↓
用户在顶部下拉切换租户
 ↓
更新 useTenantStore.currentTenantId
 ↓
所有请求 header 加 tenant-id: 1
 ↓
后端 MyBatis 拦截器自动加 WHERE tenant_id = ? 条件
```

### 1.4 后端自动 SQL 拦截（关键）

ruoyi 后端通过 MyBatis 拦截器自动给 SQL 加 `tenant_id` 条件：

```java
// TenantDatabaseInterceptor.java（约定）
public class TenantDatabaseInterceptor implements InnerInterceptor {
    @Override
    public void beforeQuery(Executor executor, MappedStatement ms, Object parameter, RowBounds rowBounds, ResultHandler resultHandler, BoundSql boundSql) {
        // 自动在 SQL 末尾加 WHERE tenant_id = ?
        // 所有 SELECT / UPDATE / DELETE 自动过滤
    }
}
```

**前端完全不用关心 SQL**，只需在请求头加 `tenant-id`。

## 2. 代码示例

### 2.1 租户 Store

```ts
// store/modules/tenant.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getTenantListApi } from '@/api/system/tenant'

export const useTenantStore = defineStore('tenant', () => {
  const tenantList = ref<TenantVO[]>([])
  const currentTenantId = ref<number>()

  async function loadTenantList() {
    tenantList.value = await getTenantListApi()
    currentTenantId.value = tenantList.value[0]?.id
  }

  function switchTenant(id: number) {
    currentTenantId.value = id
    // 重新加载菜单、权限
    // location.reload() 或重新调 userStore.fetchUserInfo()
  }

  return { tenantList, currentTenantId, loadTenantList, switchTenant }
})
```

### 2.2 Axios 拦截器注入 tenant-id

```ts
// config/axios.ts
request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  const tenantStore = useTenantStore()

  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  if (tenantStore.currentTenantId) {
    config.headers['tenant-id'] = tenantStore.currentTenantId
  }

  return config
})
```

### 2.3 顶部租户切换组件

```vue
<!-- layout/components/TenantSelect.vue -->
<script setup lang="ts">
import { useTenantStore } from '@/store/modules/tenant'

const tenantStore = useTenantStore()

async function onChange(id: number) {
  await tenantStore.switchTenant(id)
  // 切换后刷新页面，重新加载菜单
  location.reload()
}
</script>

<template>
  <el-select
    :model-value="tenantStore.currentTenantId"
    @change="onChange"
    placeholder="切换租户"
    class="!w-180px"
  >
    <el-option
      v-for="t in tenantStore.tenantList"
      :key="t.id"
      :label="t.name"
      :value="t.id"
    />
  </el-select>
</template>
```

### 2.4 后端响应自动注入租户上下文（Java）

```java
// ruoyi 后端约定
public class TenantContext {
    private static final ThreadLocal<Long> CURRENT_TENANT = new ThreadLocal<>();

    public static void setTenantId(Long tenantId) { CURRENT_TENANT.set(tenantId); }
    public static Long getTenantId() { return CURRENT_TENANT.get(); }
    public static void clear() { CURRENT_TENANT.remove(); }
}

// 拦截器从 header 读 tenant-id，存到 ThreadLocal
public class TenantInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String tenantId = request.getHeader("tenant-id");
        if (tenantId != null) {
            TenantContext.setTenantId(Long.parseLong(tenantId));
        }
        return true;
    }
}

// MyBatis 拦截器根据 ThreadLocal 自动加 SQL 条件
```

### 2.5 常见错误：忘记清 ThreadLocal

```java
// ❌ 错误：租户 ID 没清，复用到下一个请求
public boolean preHandle(...) {
    TenantContext.setTenantId(tenantId);  // 一直累积
    return true;
}

// ✅ 正确：afterCompletion 清空
public void afterCompletion(...) {
    TenantContext.clear();
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 后端 SQL 自动加租户条件

ruoyi 后端通过 `TenantDatabaseInterceptor` 自动给**所有表**的 SQL 加 `WHERE tenant_id = ?`：

```sql
-- 前端请求：SELECT * FROM mes_wm_sn WHERE sn_code LIKE 'xxx%'
-- 后端实际执行：
SELECT * FROM mes_wm_sn WHERE sn_code LIKE 'xxx%' AND tenant_id = 1
```

**前端完全无感知**。

### 3.2 前端租户切换组件约定

虽然本仓库的 vue3 子项目是独立仓库，但根据公开约定，**顶部布局**包含租户切换器：

```vue
<!-- layout/components/LayoutHeader.vue -->
<template>
  <div class="layout-header">
    <TenantSelect v-if="showTenant" />  <!-- 多租户模式下显示 -->
    <UserDropdown />
  </div>
</template>
```

### 3.3 与本仓库代码的关联

本仓库 `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/src/api/mes/wm/sn/index.ts` 中的 API 定义都默认带 tenant-id 隔离：

```ts
// MES SN 码 API
export const WmSnApi = {
  // 查询 SN 码分页（自动带 tenant-id）
  getSnPage: async (params: any) => {
    return await request.get({ url: '/mes/wm/sn/page', params })
  }
}
```

前端代码**完全不变**，只是 axios 拦截器自动在 header 加 `tenant-id`。

### 3.4 切换租户的影响范围

切换租户时，前端必须清空以下状态：
1. **菜单数据**（不同租户菜单可能不同）
2. **权限数据**（不同租户权限不同）
3. **字典缓存**（不同租户字典值可能不同）
4. **当前页面**（列表/详情页内容都不一样）

所以 ruoyi 通常用 `location.reload()` 简单粗暴地刷新整个页面。

## 4. 关键要点总结

- 多租户 = 一套系统服务多个客户，数据互相隔离
- ruoyi 用 **tenant_id 列** 做应用层过滤（成本最低）
- 切换租户 = 请求 header 加 `tenant-id`，后端 MyBatis 拦截器自动加 SQL 条件
- 前端 Store：useTenantStore 存 `tenantList` + `currentTenantId`
- 切换后**刷新整个页面**（location.reload）
- 后端用 ThreadLocal 存 tenant-id，避免线程安全问题

## 5. 练习题

### 练习 1：基础（必做）

实现 useTenantStore：包含 `tenantList`、`currentTenantId`、`loadTenantList`、`switchTenant` 四个方法。

### 练习 2：进阶

在 axios 拦截器中自动注入 `tenant-id` 请求头，切换租户后所有请求自动带新租户 ID。

### 练习 3：挑战（选做）

实现"切换租户时保留当前页面"：
- 切换租户前缓存当前路由
- 切换后重新加载菜单和权限
- 自动跳转到对应租户下相同路径的页面

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-ui/yudao-ui-admin-vue3/`
- ruoyi 多租户文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13