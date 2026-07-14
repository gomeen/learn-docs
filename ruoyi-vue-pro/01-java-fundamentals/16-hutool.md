# 1.2.6 Hutool 工具库

> 掌握 ruoyi-vue-pro 大量使用的国产 Java 工具库 Hutool，它提供 date、collection、convert 等场景化工具。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Hutool 的定位和模块结构
- 使用常见工具类（`CollUtil`、`StrUtil`、`LocalDateTimeUtil`、`ObjUtil`）
- 在 ruoyi 中识别 Hutool API 与 Apache Commons / JDK 的差异
- 避免常见的字符串判空、判等错误

## 📚 前置知识

- 集合框架
- Java 8 时间 API
- 07-collections.md、10-time-api.md

## 1. 核心概念

### 1.1 Hutool 是什么？

Hutool 是国产的 Java 工具库，由 loolly（looly）开发，被国内中小企业广泛采用。它的定位是"小而全"：把日常开发中常用的工具方法集中起来，避免每个项目都重复造轮子。

**核心思想**：能让你用一行代码完成原本 5-10 行的功能。

### 1.2 模块划分

| 模块              | 工具类（举例）                  |
|-----------------|--------------------------|
| `hutool-core`   | `StrUtil`、`ObjUtil`、`CollUtil` |
| `hutool-date`   | `LocalDateTimeUtil`、`DatePattern` |
| `hutool-crypto` | 安全加密                     |
| `hutool-http`   | HTTP 客户端                 |
| `hutool-extra`  | 模板引擎、二维码等             |
| `hutool-poi`    | Excel 导入导出              |

### 1.3 为什么 ruoyi 选 Hutool 而非 Apache Commons？

- Hutool 是中文文档 + 中文社区
- API 更现代（`String -> CharSequence`、`Function` 风格）
- 模块化按需引入，体积可控

但仍需要 Apache Commons 的几个特定场景（如 `commons-lang3`、`commons-io`）。

## 2. 代码示例

### 2.1 字符串工具 `StrUtil`

```java
// 文件：StrUtilDemo.java
import cn.hutool.core.util.StrUtil;
import cn.hutool.core.util.BooleanUtil;

public class StrUtilDemo {
    public static void main(String[] args) {
        // 1. 空判断
        boolean a = StrUtil.isEmpty("");          // true
        boolean b = StrUtil.isBlank("   ");      // true（包含空格）
        boolean c = StrUtil.isNotBlank("Tom");   // true

        // 2. 包含判断
        boolean d = StrUtil.containsAny("user", "admin", "guest");  // false

        // 3. 转换
        String camel = StrUtil.toCamelCase("user_name");   // userName
        String snake = StrUtil.toUnderlineCase("userName"); // user_name

        System.out.println(a + "/" + b + "/" + c);  // true/true/true
        System.out.println("camel = " + camel);
        System.out.println("snake = " + snake);
    }
}
```

### 2.2 集合工具 `CollUtil`

```java
// 文件：CollUtilDemo.java
import cn.hutool.core.collection.CollUtil;
import java.util.*;

public class CollUtilDemo {
    public static void main(String[] args) {
        List<Integer> list = Arrays.asList(1, 2, 3);

        // 1. 空判断
        boolean empty = CollUtil.isEmpty(list);

        // 2. 添加所有
        List<Integer> target = new ArrayList<>();
        CollUtil.addAll(target, 4, 5, 6);

        // 3. distinct / sort
        List<Integer> dup = Arrays.asList(3, 1, 2, 3, 1);
        List<Integer> unique = CollUtil.distinct(dup, false);  // [3, 1, 2]

        System.out.println("empty: " + empty);     // false
        System.out.println("target: " + target);   // [4, 5, 6]
        System.out.println("unique: " + unique);   // [3, 1, 2]
    }
}
```

### 2.3 时间工具 `LocalDateTimeUtil`

```java
// 文件：TimeUtilDemo.java
import cn.hutool.core.date.LocalDateTimeUtil;
import cn.hutool.core.date.DatePattern;
import java.time.LocalDateTime;

public class TimeUtilDemo {
    public static void main(String[] args) {
        LocalDateTime now = LocalDateTime.now();

        // 1. 格式化
        String s = LocalDateTimeUtil.format(now, DatePattern.NORM_DATETIME_PATTERN);
        System.out.println(s);   // 2026-07-13 12:30:00

        // 2. 一天的开始 / 结束
        LocalDateTime start = LocalDateTimeUtil.beginOfDay(now);
        LocalDateTime end   = LocalDateTimeUtil.endOfDay(now);

        // 3. 区间差
        long days = LocalDateTimeUtil.between(start, end, java.time.temporal.ChronoUnit.HOURS);
        System.out.println("相差小时: " + days);   // 24
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 `CollUtil.isEmpty` 判空

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/collection/CollectionUtils.java`
**核心代码**（行 36-41）：

```java
public static <T> List<T> filterList(Collection<T> from, Predicate<T> predicate) {
    if (CollUtil.isEmpty(from)) {
        return new ArrayList<>();
    }
    return from.stream().filter(predicate).collect(Collectors.toList());
}
```

**解读**：
- 第 1 行：用 `CollUtil.isEmpty()` 替代 `from == null || from.isEmpty()`
- 这个一行判空解决了两件事：
  1. **null 安全**：`from == null` 直接 true
  2. **空集合**：返回空 `List` 而不是 `null`，避免下游 NPE
- 几乎所有 `CollectionUtils` 的方法都用 `CollUtil.isEmpty` 起步

### 3.2 日期格式常量 `DatePattern`

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/date/LocalDateTimeUtils.java`
**核心代码**（行 49-55）：

```java
public static LocalDateTime parse(String time) {
    try {
        return LocalDateTimeUtil.parse(time, DatePattern.NORM_DATE_PATTERN);
    } catch (DateTimeParseException e) {
        return LocalDateTimeUtil.parse(time);
    }
}
```

**解读**：
- 第 1 行：先按 `yyyy-MM-dd` 严格格式解析
- 第 4 行：解析失败时回退到 Hutool 的 `parse(time)`（自适应格式）
- 这种"先严格后宽松"的容错策略在日期解析中很实用
- `DatePattern.NORM_DATE_PATTERN` 是 Hutool 标准格式常量，避免硬编码 `"yyyy-MM-dd"`

### 3.3 `ObjUtil.equal` 判等

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/enums/CommonStatusEnum.java`
**核心代码**（行 38-44）：

```java
public static boolean isEnable(Integer status) {
    return ObjUtil.equal(ENABLE.status, status);
}

public static boolean isDisable(Integer status) {
    return ObjUtil.equal(DISABLE.status, status);
}
```

**解读**：
- 第 1 行：`ObjUtil.equal(a, b)` 是 Hutool 的空安全 equals
- 比 `Objects.equals(a, b)` 多一层处理：还支持数组、自定义比较
- 当 `status == null` 时返回 `false`，不会 NPE
- 业务代码 `CommonStatusEnum.isEnable(user.getStatus())` 直接判，不用先判 null

## 4. 关键要点总结

- Hutool 是中文社区广泛采用的 Java 工具库，定位"小而全"
- 常用：`StrUtil` / `CollUtil` / `LocalDateTimeUtil` / `ObjUtil` / `DatePattern`
- 优势：API 现代化、空安全、模块按需引入
- ruoyi 全仓库深度依赖 Hutool，把常用工具集中管理

## 5. 练习题

### 练习 1：基础（必做）

用 Hutool 写一个工具方法：判断字符串是否为手机号（11 位、1 开头）。

### 练习 2：进阶

阅读 `LocalDateTimeUtils#parse()` 方法，解释它为什么用 try-catch + fallback 模式，而不是直接调用宽容解析。

### 练习 3：挑战（选做）

尝试用 Hutool 的 `StrUtil` 写一个"脱敏"工具：对手机号 / 邮箱 / 身份证号进行中间打码，仿照 ruoyi 的 `desensitize` 模块写一个 demo。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/collection/CollectionUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/date/LocalDateTimeUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/enums/CommonStatusEnum.java`
- Hutool 官方文档：https://hutool.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
