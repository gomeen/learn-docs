# 1.1.10 Java 8 时间 API（java.time）

> 掌握 `java.time` 包的时间日期类，理解 ruoyi 对 Hutool `LocalDateTimeUtil` 的二次封装与时区管理（Hutool 工具库详见 [16-hutool](./19-hutool.md)）。

## 🎯 学习目标

完成本文档后，你将能够：
- 使用 `LocalDate` / `LocalTime` / `LocalDateTime` 替代旧的 `Date` / `Calendar`
- 掌握时间间隔 `Duration` / `Period`
- 用 `DateTimeFormatter` 格式化和解析时间字符串
- 理解 ruoyi 中时区管理（默认 `GMT+8`）与时间工具类的设计

## 📚 前置知识

- 集合基础
- Stream API
- 09-stream-lambda.md

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

## 3. 关键要点总结

- `java.time` 包是 JDK 8 重写的时间 API，全部不可变、线程安全
- 常用 `LocalDate` / `LocalTime` / `LocalDateTime` / `Instant`
- 时间间隔：`Duration`（时分秒）、`Period`（年月日）
- ruoyi 默认 `GMT+8` 时区，业务代码统一使用 `LocalDateTimeUtils`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
