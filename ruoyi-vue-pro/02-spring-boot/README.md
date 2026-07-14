# 02 - Spring Boot 核心

> Spring Boot 是 ruoyi-vue-pro 的核心框架。理解 IoC、AOP、AutoConfiguration 是阅读源码的基础。

## 模块 2.1 Spring 核心概念

- [ ] [1.1 IoC 容器与依赖注入](./01-ioc.md)
- [ ] [1.2 Bean 生命周期与作用域](./02-bean-lifecycle.md)
- [ ] [1.3 AOP 面向切面编程](./03-aop.md)
- [ ] [1.4 Spring 事务管理](./04-transaction.md)
- [ ] [1.5 Spring 事件机制：ApplicationEvent](./05-event.md)
- [ ] [1.6 Spring Profile 多环境配置](./06-profile.md)

## 模块 2.2 Spring Boot 基础

- [ ] [2.1 Spring Boot 启动流程](./07-startup.md)
- [ ] [2.2 自动配置原理：@SpringBootApplication](./08-auto-config.md)
- [ ] [2.3 自定义 Starter](./09-custom-starter.md)
- [ ] [2.4 配置文件：application.yml 多环境](./10-config.md)
- [ ] [2.5 Actuator 监控端点](./11-actuator.md)
- [ ] [2.6 Spring Boot 启动加载器](./12-bootstrap.md)

## 模块 2.3 Spring MVC

- [ ] [3.1 @Controller / @RestController](./13-controller.md)
- [ ] [3.2 请求映射：@RequestMapping / @GetMapping](./14-request-mapping.md)
- [ ] [3.3 参数绑定：@RequestParam / @PathVariable / @RequestBody](./15-param-binding.md)
- [ ] [3.4 统一返回结果：Result / R](./16-result-wrapper.md)
- [ ] [3.5 全局异常处理：@ControllerAdvice](./17-exception-handler.md)
- [ ] [3.6 拦截器：HandlerInterceptor](./18-interceptor.md)
- [ ] [3.7 过滤器：Filter 与 OncePerRequestFilter](./19-filter.md)
- [ ] [3.8 ruoyi 的 Web 配置分析](./20-ruoyi-web.md)

## 模块 2.4 Spring Boot 高级

- [ ] [4.1 参数校验：@Valid / @Validated](./21-validation.md)
- [ ] [4.2 异步任务：@Async](./22-async.md)
- [ ] [4.3 定时任务：@Scheduled](./23-scheduled.md)
- [ ] [4.4 Spring Cache 与缓存抽象](./24-cache.md)
- [ ] [4.5 国际化：MessageSource](./25-i18n.md)
- [ ] [4.6 Spring Boot 3.x 迁移要点](./26-spring-boot-3.md)

## 🎯 ruoyi-vue-pro 仓库对应位置

- 启动类：`yudao-server/src/main/java/`
- Web 配置：`yudao-framework/yudao-spring-boot-starter-web/`
- 异常处理：`yudao-common/`
- Result 包装：搜索 `CommonResult` / `R<>`
