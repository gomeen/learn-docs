# 1.3.3 类加载机制

> 理解 JVM 的类加载过程（加载 → 连接 → 初始化）与双亲委派模型，能解释 Spring Boot 的 Fat Jar 启动原理。

## 🎯 学习目标

完成本文档后，你将能够：
- 画出类加载的 5 个阶段（加载、验证、准备、解析、初始化）
- 理解双亲委派模型（Bootstrap → Ext → AppClassLoader）
- 解释何时触发"初始化"（5 种情况）
- 能手写一个自定义 `ClassLoader` 加载加密 class

## 📚 前置知识

- Java 反射基础
- JVM 内存模型
- 05-reflection.md、18-jvm-memory.md

## 1. 核心概念

### 1.1 类加载 5 阶段

```
加载 → 验证 → 准备 → 解析 → 初始化
        (连接阶段)
```

| 阶段         | 作用                                                                 |
|------------|--------------------------------------------------------------------|
| **加载**     | 读 `.class` 字节流，在方法区创建 Class 对象                                 |
| **验证**     | 校验字节码合法性（魔数、版本号、语法、符号引用）                                      |
| **准备**     | 类变量（`static`）赋值**默认零值**，不是 final                          |
| **解析**     | 符号引用 → 直接引用的转换（可选，动态绑定时延后）                                    |
| **初始化**   | `<clinit>`：执行 static 代码块 + 显式赋值                               |

注意：**准备阶段**赋值的是 `0 / null`，到 **初始化阶段**才执行 `<clinit>` 把 `static int i = 10` 中的 10 赋上去。

### 1.2 何时触发"初始化"？

只有下列 5 种场景才会触发类的初始化（**主动引用**）：

1. `new` 一个对象
2. 访问类的 static 字段（非 final）
3. 调用类的 static 方法
4. `Class.forName()` 加载类（默认会触发）
5. 反射调用方法 / 创建实例

其他场景（**被动引用**）：
- `static final` 常量（编译期常量）不会触发初始化
- 通过子类访问父类 static 字段，只触发父类初始化
- 数组定义类（`User[] arr = new User[10]`）不会触发

### 1.3 双亲委派模型

类加载器有层次结构：

```
Bootstrap ClassLoader (rt.jar, 启动类)
       ↑
Extension ClassLoader (ext/, 扩展类)
       ↑
Application ClassLoader (classpath, 应用类)
       ↑
Custom ClassLoader (用户自定义)
```

**双亲委派原则**：当需要加载一个类时，加载器先委派给父加载器去加载，父加载器又委派给爷爷……只有父加载器都加载不了时，才由自己加载。

目的：
1. 防止重复加载（用户写一个 `java.lang.String` 也加载不到，因为 Bootstrap 已加载）
2. 保证核心类的安全

### 1.4 关键 API

```java
ClassLoader cl = MyClass.class.getClassLoader();  // 获取类加载器
Class.forName("cn.iocoder.yudao.User");            // 默认会触发初始化
Class.forName(name, false, cl);                    // 不触发初始化
URLClassLoader ucl = new URLClassLoader(urls);    // 自定义类加载器
```

## 2. 代码示例

### 2.1 演示"static final 常量不触发初始化"

```java
// 文件：ConstHolder.java
public class ConstHolder {
    public static final int VALUE = 100;
    static {
        System.out.println("ConstHolder 初始化");
    }
}
```

```java
// 文件：ConstDemo.java
public class ConstDemo {
    public static void main(String[] args) {
        System.out.println(ConstHolder.VALEU);   // 不会触发 ConstHolder 的 static 块
        // 编译期常量被 Java 直接内联到调用方字节码中
    }
}
```

### 2.2 自定义 ClassLoader（加载加密 class）

```java
// 文件：SimpleClassLoader.java
import java.io.*;
import java.lang.reflect.Method;

public class SimpleClassLoader extends ClassLoader {

    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        try {
            // 1. 模拟从网络 / 文件读取字节码
            String path = "/path/to/" + name.replace(".", "/") + ".class";
            FileInputStream fis = new FileInputStream(path);
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            byte[] buffer = new byte[1024];
            int len;
            while ((len = fis.read(buffer)) > 0) {
                baos.write(buffer, 0, len);
            }

            // 2. 假装"解密"（这里是异或，可替换成 AES 等真实算法）
            byte[] classBytes = baos.toByteArray();
            for (int i = 0; i < classBytes.length; i++) {
                classBytes[i] ^= 0x42;   // 用相同的密钥再次异或 = 解密
            }

            // 3. defineClass 把字节码注册成 Class 对象
            return defineClass(name, classBytes, 0, classBytes.length);
        } catch (IOException e) {
            throw new ClassNotFoundException(name, e);
        }
    }

    public static void main(String[] args) throws Exception {
        SimpleClassLoader cl = new SimpleClassLoader();
        Class<?> cls = cl.loadClass("com.example.Hello");
        Method m = cls.getMethod("say");
        Object instance = cls.getDeclaredConstructor().newInstance();
        m.invoke(instance);   // 调用 say()
    }
}
```

### 2.3 主动引用 vs 被动引用

```java
// 文件：LoadDemo.java
class Parent {
    static int parentStatic = 10;
    static { System.out.println("Parent init"); }
}
class Child extends Parent {
    static int childStatic = 20;
    static { System.out.println("Child init"); }
}

public class LoadDemo {
    public static void main(String[] args) {
        // 1. 主动引用：访问子类字段 → 父类先初始化
        System.out.println(Child.childStatic);
        // 输出：Parent init → Child init → 20

        // 2. 被动引用：通过子类访问父类字段 → 仅父类初始化
        // （代码见下文演示）
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 ruoyi 中无直接示例

> ruoyi 是 Spring Boot 应用，类加载完全由 Spring Boot 容器处理：

**Spring Boot Fat Jar 启动原理**：
```
spring-boot-loader 自定义 ClassLoader
       ↓
扫描 BOOT-INF/classes 与 BOOT-INF/lib 下的 jar
       ↓
委派到父加载器（加载 rt.jar / ext/）
       ↓
若父加载器无 → 自定义加载器加载 jar 内的类
```

业务代码无需关心。

### 3.2 Spring 上下文加载 Bean 的过程

Spring 启动时（`AbstractApplicationContext#refresh()`）会：
1. 加载所有 bean class（触发这些类的初始化）
2. 反射调用构造器创建 bean
3. 注入依赖（可能触发更多类的初始化）

这解释了为什么 Spring 项目启动**第一次访问时较慢**——类加载 + 反射开销。

## 4. 关键要点总结

- 类加载 5 阶段：加载 → 验证 → 准备 → 解析 → 初始化
- static final 常量**不**触发初始化（编译期常量内联）
- **双亲委派**：用户写的 `java.lang.String` 加载不到
- Spring Boot 自定义 ClassLoader 支持 Fat Jar

## 5. 练习题

### 练习 1：基础（必做）

写一个 `class Demo { static int x = 10; static { System.out.println("init"); } }`，证明：
- `Demo.x` 会触发 init
- `Demo.class` 不会触发 init
- `Class.forName("Demo")` 会触发 init

### 练习 2：进阶

实现"类加载阶段不要触发初始化"的 3 种方式（`Class.forName(name, false, cl)` 等）。

### 练习 3：挑战（选做）

写一个类加载器，把 class 文件读出来后用 Base64 解码再 `defineClass`，模拟"加密 class"的加载。

## 6. 参考资料

- 周志明《深入理解 Java 虚拟机》第 7 章：类加载机制
- Oracle Class Loading 文档：https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-5.html
- Spring Boot Loader 源码：https://github.com/spring-projects/spring-boot/tree/main/spring-boot-project/spring-boot-tools/spring-boot-loader

---

**文档版本**：v1.0
**最后更新**：2026-07-13
