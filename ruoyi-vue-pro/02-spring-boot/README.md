# 02 - Spring Boot 核心

> Spring Boot 是 ruoyi-vue-pro 的核心框架。理解 IoC、AOP、AutoConfiguration 是阅读源码的基础。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 模块 2.1 Spring 核心概念

- [ ] [1.1 IoC 容器与依赖注入](./01-ioc.md)
- [ ] [1.2 Bean 生命周期与作用域](./02-bean-lifecycle.md)
- [ ] [1.3 AOP 面向切面编程](./03-aop.md)
- [ ] [1.4 Spring 事务管理](./04-transaction.md)
- [ ] [1.5 Spring 事件机制：ApplicationEvent](./05-event.md)
- [ ] [1.6 Spring Profile 多环境配置](./06-profile.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [07-*-ioc-aop: IoC / AOP / 事务 / 事件 / Profile](./07-*-ioc-aop.md)
  - 覆盖：01-ioc.md, 02-bean-lifecycle.md, 03-aop.md, 04-transaction.md, 05-event.md, 06-profile.md


## 模块 2.2 Spring Boot 基础

- [ ] [2.1 Spring Boot 启动流程](./08-startup.md)
- [ ] [2.2 自动配置原理：@SpringBootApplication](./09-auto-config.md)
- [ ] [2.3 自定义 Starter](./10-custom-starter.md)
- [ ] [2.4 配置文件：application.yml 多环境](./11-config.md)
- [ ] [2.5 Actuator 监控端点](./12-actuator.md)
- [ ] [2.6 Spring Boot 启动加载器](./13-bootstrap.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [14-*-auto-config: 启动 / 自动配置 / Starter / 配置 / Actuator](./14-*-auto-config.md)
  - 覆盖：08-startup.md, 09-auto-config.md, 10-custom-starter.md, 11-config.md, 12-actuator.md, 13-bootstrap.md


## 模块 2.3 Spring MVC

- [ ] [3.1 @Controller / @RestController](./15-controller.md)
- [ ] [3.2 请求映射：@RequestMapping / @GetMapping](./16-request-mapping.md)
- [ ] [3.3 参数绑定：@RequestParam / @PathVariable / @RequestBody](./17-param-binding.md)
- [ ] [3.4 统一返回结果：Result / R](./18-result-wrapper.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [19-*-web-layer: Controller / 映射 / 参数 / 统一返回](./19-*-web-layer.md)
  - 覆盖：15-controller.md, 16-request-mapping.md, 17-param-binding.md, 18-result-wrapper.md

- [ ] [3.5 全局异常处理：@ControllerAdvice](./20-exception-handler.md)
- [ ] [3.6 拦截器：HandlerInterceptor](./21-interceptor.md)
- [ ] [3.7 过滤器：Filter 与 OncePerRequestFilter](./22-filter.md)
- [ ] [3.8 ruoyi 的 Web 配置分析](./23-ruoyi-web.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [24-*-web-pipeline: 异常处理 / 拦截器 / Filter / ruoyi Web](./24-*-web-pipeline.md)
  - 覆盖：20-exception-handler.md, 21-interceptor.md, 22-filter.md, 23-ruoyi-web.md


## 模块 2.4 Spring Boot 高级

- [ ] [4.1 参数校验：@Valid / @Validated](./25-validation.md)
- [ ] [4.2 异步任务：@Async](./26-async.md)
- [ ] [4.3 定时任务：@Scheduled](./27-scheduled.md)
- [ ] [4.4 Spring Cache 与缓存抽象](./28-cache.md)
- [ ] [4.5 国际化：MessageSource](./29-i18n.md)
- [ ] [4.6 Spring Boot 3.x 迁移要点](./30-spring-boot-3.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [31-*-boot-advanced: 校验 / 异步 / 缓存 / 国际化 / Boot3](./31-*-boot-advanced.md)
  - 覆盖：25-validation.md, 26-async.md, 27-scheduled.md, 28-cache.md, 29-i18n.md, 30-spring-boot-3.md


## 🎯 ruoyi-vue-pro 仓库对应位置

- 启动类：`yudao-server/src/main/java/`
- Web 配置：`yudao-framework/yudao-spring-boot-starter-web/`
- 异常处理：`yudao-common/`
- Result 包装：搜索 `CommonResult` / `R<>`
