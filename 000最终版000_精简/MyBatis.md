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

MyBatis是Java领域的一款**持久化框架**，用于在**Java对象**与**数据库**之间建立映射。

**特点**：
- 直接编写SQL，便于精准优化查询
- 充分利用数据库特性，处理复杂业务逻辑
- 不做对象与表的完全自动映射，映射配置需手动编写
- 更灵活，便于精细控制数据库操作

### 1.2 为什么说MyBatis是半ORM映射工具？

- **全自动ORM（如Hibernate）**：自动映射对象与表，自动生成SQL
- **MyBatis**：SQL与映射配置均需手动编写
- **半ORM**：介于JDBC与全自动ORM之间，保留SQL可控性

### 1.3 MyBatis的优点与缺点

**优点**：SQL可控性强、性能优化灵活、适合复杂查询、学习成本低。

**缺点**：需手动编写SQL、映射配置繁琐、与数据库耦合度较高。

---

## 2. 核心组件

### 2.1 MyBatis的核心组件

1. **SqlSessionFactory**
   - 会话工厂，负责创建SqlSession
   - 管理数据库连接信息与事务
   - 加载配置文件和映射文件

2. **SqlSession**
   - 与数据库交互的入口
   - 执行SQL、提交或回滚事务、获取Mapper实例
   - 生命周期短暂，用完即关

3. **Mapper接口**
   - 定义数据库操作
   - 对应一个或多个映射文件，通过动态代理关联SQL

4. **映射文件**
   - 连接Java对象与数据库表
   - 定义SQL、参数映射、结果映射

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

- `<select>`：查询
- `<insert>`：插入
- `<update>`：更新
- `<delete>`：删除
- `<resultMap>`：结果映射
- `<sql>`：可重用SQL片段
- `<include>`：引用SQL片段

### 3.3 MyBatis中的动态SQL是什么？

**动态SQL标签**：`<if>`（条件判断）、`<choose>/<when>/<otherwise>`（分支选择）、`<where>`、`<set>`、`<foreach>`（循环）、`<trim>`。

**示例**：
```xml
<select id="selectUser" resultType="User">
    SELECT * FROM user
    <where>
        <if test="name != null">AND name = #{name}</if>
        <if test="age != null">AND age = #{age}</if>
    </where>
</select>
```

### 3.4 MyBatis的工作流程是怎样的？

1. 加载配置，创建SqlSessionFactory
2. 打开SqlSession
3. 获取Mapper接口实例
4. 执行SQL
5. 提交/回滚事务
6. 关闭SqlSession

### 3.5 MyBatis如何处理延迟加载？

通过 `lazyLoadingEnabled=true` 开启延迟加载，配合 `aggressiveLazyLoading=false` 实现按需加载；底层用Javassist或CGLIB创建代理对象，访问关联对象时才执行查询。

### 3.6 模糊查询like语句该怎么写？

**方式1：使用${}**
```sql
SELECT * FROM user WHERE name LIKE '%${value}%'
```

**方式2：使用CONCAT函数**
```sql
SELECT * FROM user WHERE name LIKE CONCAT('%', #{name}, '%')
```

**方式3：使用bind标签**
```xml
<select id="selectUser" resultType="User">
    <bind name="pattern" value="'%' + name + '%'"/>
    SELECT * FROM user WHERE name LIKE #{pattern}
</select>
```

### 3.7 使用like时如何防止SQL注入？

推荐：使用CONCAT函数、bind标签，或在Java代码中拼接通配符；不推荐使用`${}`。

---

## 4. 高级篇

### 4.1 能说说MyBatis的工作原理吗？

读取配置 → 创建SqlSessionFactory → 打开SqlSession → 调用Mapper方法 → 动态代理生成SQL → 执行并返回结果 → 关闭SqlSession。

### 4.2 MyBatis的一级、二级缓存

**一级缓存（SqlSession缓存）**：作用域为SqlSession，默认开启，随SqlSession销毁，存于HashMap。

**二级缓存（Mapper缓存）**：作用域为Mapper（Namespace），需手动开启，跨SqlSession共享，存储方式可配置（如Ehcache、Redis）。

| 特性 | 一级缓存 | 二级缓存 |
|------|----------|----------|
| **作用域** | SqlSession | Mapper |
| **默认开启** | 是 | 否 |
| **跨会话** | 否 | 是 |
| **存储方式** | HashMap | 可配置 |

### 4.3 二级缓存的缺点？

- 存在数据一致性问题，分布式环境下缓存同步困难
- 有缓存击穿、雪崩、穿透风险
- 内存占用较大，不适合实时性要求高的场景

### 4.4 MyBatis如何处理懒加载和预加载？

**懒加载**：`lazyLoadingEnabled=true`，通过代理对象在访问关联对象时才查询。

**预加载**：`aggressiveLazyLoading=false`，加载主对象时立即加载关联对象。

### 4.5 MyBatis如何实现动态数据源切换？

1. 继承`AbstractRoutingDataSource`
2. 重写`determineCurrentLookupKey`方法
3. 用ThreadLocal保存数据源标识
4. 通过AOP或注解切换数据源

### 4.6 MyBatis是如何进行分页的？

1. **数组分页**：内存分页，不推荐
2. **SQL分页**：物理分页，使用LIMIT，推荐
3. **拦截器分页**：使用PageHelper等插件

### 4.7 MyBatis的插件能在哪些地方进行拦截？

- Executor：update、query、flushStatements、commit、rollback
- StatementHandler：prepare、parameterize、batch、update、query
- ParameterHandler：getParameterObject、setParameters
- ResultSetHandler：handleResultSets、handleOutputParameters

### 4.8 如何编写一个MyBatis插件？

1. 实现`Interceptor`接口
2. 用`@Intercepts`注解指定拦截方法
3. 重写`plugin`方法
4. 在配置文件中注册插件

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

### 4.9 简述MyBatis插件的运行原理

基于动态代理：拦截器链包装目标对象，调用拦截器的`intercept`方法，再由`invocation.proceed()`继续执行。

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

```sql
-- CONCAT方式
SELECT * FROM user WHERE name LIKE CONCAT('%', #{name}, '%')
-- bind方式
SELECT * FROM user WHERE name LIKE #{pattern}
```

### 5.3 MyBatis一二级缓存的区别？

详见 4.2 节。

---

## 总结

本文档汇总了MyBatis的核心知识点：概述（定义、特点、优缺点）、核心组件（SqlSessionFactory、SqlSession、Mapper、映射文件）、基础篇（#{}与${}、动态SQL、工作流程、延迟加载、模糊查询）、高级篇（缓存、分页、插件、数据源切换）、常见问题（与JPA对比、模糊查询、缓存区别）。
