# 1.1.10 Java 8 时间 API（java.time）

> 掌握 `java.time` 包的时间日期类，理解 ruoyi 对 Hutool `LocalDateTimeUtil` 的二次封装与时区管理。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 `LocalDate` / `LocalTime` / `LocalDateTime` 替代旧的 `Date` / `Calendar`
- 掌握时间间隔 `Duration` / `Period`
- 用 `DateTimeFormatter` 格式化和解析时间字符串
- 理解 ruoyi 中时区管理（默认 `GMT+8`）与时间工具类的设计

## 📚 前置知识

- 集合基础
- Stream API
- 08-stream-lambda.md

## 1. 核心概念

### 1.1 为什么出现 `java.time` 包？

JDK 8 之前的 `java.util.Date` 和 `java.util.Calendar` 设计糟糕：可变、线程不安全、API 反人类。`java.time` 包完全重写，全部**不可变**且**线程安全**。

### 1.2 核心类

| 类                  | 用途           | 示例                          |
|--------------------|--------------|-----------------------------|
| `LocalDate`        | 日期（年月日）     | 2026-07-13                  |
| `LocalTime`        | 时间（时分秒）     | 12:30:00                    |
| `LocalDateTime`    | 日期+时间（无时区）  | 2026-07-13T12:30:00         |
| `ZonedDateTime`    | 带时区时间        | 2026-07-13T12:30:00+08:00   |
| `Instant`          | 时间戳（UTC 秒）  | 1752391800                  |
| `Duration`         | 时间间隔（时分秒）   | PT1H30M                     |
| `Period`           | 日期间隔（年月日）   | P1Y2M3D                     |

### 1.3 关键 API

```java
// 现在时间
LocalDateTime now = LocalDateTime.now();

// 创建指定时间
LocalDate date = LocalDate.of(2026, 7, 13);
LocalDateTime dt = LocalDateTime.of(2026, 7, 13, 12, 30, 0);

// 增减
LocalDateTime.plusDays(7);
LocalDateTime.minusHours(2);

// 比较
dt.isBefore(now);
dt.isAfter(now);

// 格式化
String s = now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));

// 解析
LocalDate parsed = LocalDate.parse("2026-07-13");
```

### 1.4 时区问题

`LocalDateTime` 不带时区，处理**多时区**时要用 `ZonedDateTime` 或 `Instant`。中国一般用 `Asia/Shanghai`（GMT+8）。

## 2. 代码示例

### 2.1 LocalDateTime 基础操作

```java
// 文件：TimeApiDemo.java
import java.time.*;
import java.time.format.DateTimeFormatter;

public class TimeApiDemo {
    public static void main(String[] args) {
        // 1. 当前时间
        LocalDateTime now = LocalDateTime.now();
        System.out.println("现在: " + now);

        // 2. 1 周后 / 3 天前
        LocalDateTime nextWeek = now.plusDays(7);
        LocalDateTime threeDaysAgo = now.minusDays(3);

        // 3. 计算两个时间相差多少天
        long days = Duration.between(threeDaysAgo, now).toDays();
        System.out.println("相差: " + days + " 天");

        // 4. 格式化
        String formatted = now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        System.out.println("格式化: " + formatted);

        // 5. 解析
        LocalDate date = LocalDate.parse("2026-07-13");
        System.out.println("解析: " + date);

        // 6. 时间戳
        long epochSecond = now.atZone(ZoneId.systemDefault()).toEpochSecond();
        System.out.println("时间戳: " + epochSecond);
    }
}
```

### 2.2 计算年龄（Period）

```java
// 文件：AgeCalculator.java
import java.time.LocalDate;
import java.time.Period;

public class AgeCalculator {
    public static int calculate(LocalDate birth) {
        return Period.between(birth, LocalDate.now()).getYears();
    }

    public static void main(String[] args) {
        System.out.println(calculate(LocalDate.of(1990, 5, 20)));  // 36
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 时区常量与基础时间工具

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/date/DateUtils.java`
**核心代码**（行 17-46）：

```java
/**
 * 时区 - 默认
 */
public static final String TIME_ZONE_DEFAULT = "GMT+8";

/**
 * 秒转换成毫秒
 */
public static final long SECOND_MILLIS = 1000;

public static final String FORMAT_YEAR_MONTH_DAY = "yyyy-MM-dd";

public static final String FORMAT_YEAR_MONTH_DAY_HOUR_MINUTE_SECOND = "yyyy-MM-dd HH:mm:ss";

/**
 * 将 LocalDateTime 转换成 Date
 *
 * @param date LocalDateTime
 * @return LocalDateTime
 */
public static Date of(LocalDateTime date) {
    if (date == null) {
        return null;
    }
    // 将此日期时间与时区相结合以创建 ZonedDateTime
    ZonedDateTime zonedDateTime = date.atZone(ZoneId.systemDefault());
    // 本地时间线 LocalDateTime 到即时时间线 Instant 时间戳
    Instant instant = zonedDateTime.toInstant();
    // UTC时间(世界协调时间,UTC + 00:00)转北京(北京,UTC + 8:00)时间
    return Date.from(instant);
}
```

**解读**：
- 第 4 行：常量 `GMT+8` 作为默认时区，避免各处硬编码
- 第 12 行：`yyyy-MM-dd` 是国际化通用日期格式
- 第 21-32 行：`LocalDateTime` 与 `Date` 互转工具，注释里写得很详细——"本地时间线到即时时间线 Instant"
- **业务场景**：MyBatis 数据库存储仍是 `Date`，需要在 `LocalDateTime`（业务代码友好）和 `Date`（数据库）之间切换

### 3.2 LocalDateTimeUtils 时间段生成

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/date/LocalDateTimeUtils.java`
**核心代码**（行 273-280）：

```java
/**
 * 获取最近 N 天的 0 点时刻序列（升序，含今天）
 * <p>
 * 例：getLatestDays(3) 返回 [前天 00:00, 昨天 00:00, 今天 00:00]
 *
 * @param days 天数（含今天）
 * @return 升序的 LocalDateTime 列表
 */
public static List<LocalDateTime> getLatestDays(int days) {
    LocalDateTime today = getToday();
    List<LocalDateTime> dates = new ArrayList<>(days);
    for (int i = days - 1; i >= 0; i--) {
        dates.add(today.minusDays(i));
    }
    return dates;
}
```

**解读**：
- `LocalDateTime` 不可变，返回新对象
- 业务场景：统计近 7 天用户登录次数、生成图表的横坐标等
- 这种"工具类返回时间序列"的封装思路在 ruoyi 中极常见——避免业务代码重复写 for 循环

## 4. 关键要点总结

- `java.time` 包是 JDK 8 重写的时间 API，全部不可变、线程安全
- 常用 `LocalDate` / `LocalTime` / `LocalDateTime` / `Instant`
- 时间间隔：`Duration`（时分秒）、`Period`（年月日）
- ruoyi 默认 `GMT+8` 时区，业务代码统一使用 `LocalDateTimeUtils`

## 5. 练习题

### 练习 1：基础（必做）

写一个方法 `boolean isSameDay(LocalDateTime a, LocalDateTime b)`：判断两个 `LocalDateTime` 是否是同一天。

### 练习 2：进阶

阅读 `LocalDateTimeUtils#getDateRangeList`（行 282-346），解释它是如何按"小时 / 天 / 周 / 月 / 季度 / 年"切分时间段的。

### 练习 3：挑战（选做）

实现一个 `CronExpressionParser`：给定 "0 0 12 * * ?"（每天 12 点执行），返回未来 10 次触发的时间戳列表。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/date/DateUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/date/LocalDateTimeUtils.java`
- 《Java 核心技术 卷 II》第 6 章：日期时间 API
- Java 时间 API 教程：https://docs.oracle.com/javase/tutorial/datetime/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
