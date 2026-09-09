# MyBatis知识汇总

## 目录

1. [MyBatis概述](#1-mybatis概述)
2. [核心组件](#2-核心组件)
3. [基础篇](#3-基础篇)
4. [高级篇](#4-高级篇)
5. [常见问题](#5-常见问题)

---

## 1. MyBatis概述

### 1.1 什么是MyBatis

MyBatis是Java领域中的一款**持久化框架**，主要功能是让我们能够轻松地在**Java对象**和**数据库**之间建立联系。

**特点**：
- 直接编写SQL语句，提供更精准的查询优化
- 充分利用数据库的特性，处理复杂业务逻辑
- 不会自动将对象和数据库表进行完全映射
- 需要手动编写映射配置
- 更加灵活，适用于精细控制数据库操作

### 1.2 为什么说MyBatis是半ORM映射工具？

- **全自动ORM（如Hibernate）**：自动映射对象和表，自动生成SQL
- **MyBatis**：需要手动编写SQL和映射配置
- **半ORM**：介于JDBC和全自动ORM之间，提供了SQL可控性

### 1.3 MyBatis的优点&缺点

**优点**：
- SQL可控性强
- 性能优化灵活
- 适用于复杂查询
- 学习成本低

**缺点**：
- 需要手动编写SQL
- 映射配置繁琐
- 数据库耦合度高

---

## 2. 核心组件

### 2.1 MyBatis的核心组件

1. **SqlSessionFactory**
   - 会话工厂
   - 创建SqlSession对象
   - 配置数据库连接信息和事务管理
   - 加载配置和映射文件

2. **SqlSession**
   - 与数据库交互的窗口
   - 执行SQL语句
   - 提交或回滚事务
   - 获取Mapper接口实例
   - 生命周期短暂，操作完成后应关闭

3. **Mapper接口**
   - 定义数据库操作规则
   - 对应一个或多个映射文件
   - 通过动态代理关联SQL语句
   - 方法定义增删改查操作

4. **映射文件**
   - 连接Java对象和数据库表的桥梁
   - 定义SQL语句、参数映射、结果映射
   - 包含增删改查操作

---

## 3. 基础篇

### 3.1 #{}和${}的区别是什么？

| 特性 | #{} | ${} |
|------|-----|-----|
| **SQL注入** | 防止 | 存在风险 |
| **预编译** | 是 | 否 |
| **性能** | 较高 | 较低 |
| **使用场景** | 参数传递 | 动态表名、排序 |

**示例**：
```sql
-- #{}：预编译，防止SQL注入
SELECT * FROM user WHERE id = #{id}

-- ${}：直接拼接，存在SQL注入风险
SELECT * FROM user WHERE id = ${id}
```

### 3.2 MyBatis中XML映射有哪些标签？

- ``：查询
- ``：插入
- ``：更新
- ``：删除
- ``：结果映射
- ``：可重用SQL片段
- ``：引用SQL片段

### 3.3 MyBatis中的动态SQL是什么？

**动态SQL标签**：
- ``：条件判断
- ``、``、``：选择分支
- ``：智能WHERE子句
- ``：智能SET子句
- ``：循环遍历
- ``：智能修剪

**示例**：
```xml

    SELECT * FROM user

        AND name = #{name}
        AND age = #{age}

```

### 3.4 MyBatis的工作流程是怎样的？

1. 加载配置文件，创建SqlSessionFactory
2. 打开SqlSession
3. 获取Mapper接口实例
4. 执行SQL语句
5. 提交/回滚事务
6. 关闭SqlSession

### 3.5 MyBatis如何处理延迟加载？

**延迟加载配置**：
```xml

```

**实现方式**：
- 使用Javassist或CGLIB创建代理对象
- 访问关联对象时才执行查询

### 3.6 模糊查询like语句该怎么写？

**方式1：使用${}**
```xml
SELECT * FROM user WHERE name LIKE '%${value}%'
```

**方式2：使用CONCAT函数**
```xml
SELECT * FROM user WHERE name LIKE CONCAT('%', #{name}, '%')
```

**方式3：使用bind标签**
```xml

SELECT * FROM user WHERE name LIKE #{pattern}
```

### 3.7 mybatis使用like的时候，如何防止SQL注入？

**推荐方式**：
1. 使用CONCAT函数
2. 使用bind标签
3. 在Java代码中拼接通配符

**不推荐**：
- 使用${}（存在SQL注入风险）

---

## 4. 高级篇

### 4.1 能说说MyBatis的工作原理吗？

**工作流程**：
1. 读取配置文件
2. 创建SqlSessionFactory
3. 打开SqlSession
4. 执行Mapper接口方法
5. 动态代理生成SQL
6. 执行SQL并返回结果
7. 关闭SqlSession

### 4.2 MyBatis的一级、二级缓存

**一级缓存（SqlSession缓存）**：
- 作用域：SqlSession
- 默认开启
- 生命周期与SqlSession相同
- 存储在HashMap中

**二级缓存（Mapper缓存）**：
- 作用域：Mapper（Namespace）
- 需要手动开启
- 跨SqlSession共享
- 可配置存储方式（如Ehcache、Redis）

**区别**：
| 特性 | 一级缓存 | 二级缓存 |
|------|----------|----------|
| **作用域** | SqlSession | Mapper |
| **默认开启** | 是 | 否 |
| **跨会话** | 否 | 是 |
| **存储方式** | HashMap | 可配置 |

### 4.3 讲讲MyBatis中二级缓存的缺点？

**缺点**：
- 数据一致性问题
- 分布式环境下缓存同步困难
- 缓存击穿、雪崩、穿透风险
- 内存占用较大
- 不适合实时性要求高的场景

### 4.4 MyBatis如何处理懒加载和预加载？

**懒加载**：
- 配置lazyLoadingEnabled=true
- 访问关联对象时才执行查询
- 使用代理对象

**预加载**：
- 配置aggressiveLazyLoading=false
- 加载主对象时立即加载关联对象

### 4.5 MyBatis如何实现动态数据源切换？

**实现方式**：
1. 继承AbstractRoutingDataSource
2. 重写determineCurrentLookupKey方法
3. 使用ThreadLocal保存数据源标识
4. 通过AOP或注解切换数据源

### 4.6 Mybatis是如何进行分页的？

**分页方式**：
1. **数组分页**：内存分页（不推荐）
2. **SQL分页**：物理分页（推荐）
   - 使用LIMIT子句
3. **拦截器分页**：使用PageHelper等插件

### 4.7 MyBatis的插件能够在哪些地方进行拦截？

**可拦截方法**：
- Executor：update、query、flushStatements、commit、rollback
- StatementHandler：prepare、parameterize、batch、update、query
- ParameterHandler：getParameterObject、setParameters
- ResultSetHandler：handleResultSets、handleOutputParameters

### 4.8 如何编写一个MyBatis插件？

**步骤**：
1. 实现Interceptor接口
2. 使用@Intercepts注解指定拦截方法
3. 重写plugin方法
4. 在配置文件中注册插件

**示例**：
```java
@Intercepts({
    @Signature(type=Executor.class, method="query",
               args={MappedStatement.class, Object.class, RowBounds.class, ResultHandler.class})
})
public class MyPlugin implements Interceptor {
    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        // 拦截逻辑
        return invocation.proceed();
    }
}
```

### 4.9 简述Mybatis的插件运行原理

**原理**：
- 使用动态代理模式
- 拦截器链包装目标对象
- 调用拦截器的intercept方法
- 通过invocation.proceed()继续执行

---

## 5. 常见问题

### 5.1 MyBatis与JPA有哪些不同？

| 特性 | MyBatis | JPA |
|------|---------|-----|
| **SQL控制** | 手动编写 | 自动生成 |
| **映射方式** | 手动配置 | 自动映射 |
| **学习成本** | 低 | 高 |
| **性能优化** | 灵活 | 受限 |
| **适用场景** | 复杂查询 | 简单CRUD |

### 5.2 模糊查询like语句该怎么写？

**推荐方式**：
```xml

SELECT * FROM user WHERE name LIKE CONCAT('%', #{name}, '%')

SELECT * FROM user WHERE name LIKE #{pattern}
```

### 5.3 MyBatis一二级缓存的区别？

（详见4.2节）

---

## 总结

本文档系统性地汇总了MyBatis的核心知识点，包括：

1. **MyBatis概述**：定义、特点、优缺点
2. **核心组件**：SqlSessionFactory、SqlSession、Mapper、映射文件
3. **基础篇**：#{}与${}、动态SQL、工作流程、延迟加载、模糊查询
4. **高级篇**：缓存机制、分页、插件、数据源切换
5. **常见问题**：与JPA对比、模糊查询、缓存区别

通过本文档，可以系统性地掌握MyBatis的核心概念和实践方法。