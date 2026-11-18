# MyBatis 知识汇总

本文梳理 MyBatis 的核心概念、常用写法与进阶机制，面向有 1 年左右 Java 经验、写过 CRUD 但还没读过框架源码的读者。文中涉及的配置项与默认值以 MyBatis 3.5.x 官方参考文档为准，个别条目会额外标注引入或变更的版本。

## 本文导读

- 第 1 章 MyBatis 概述：它是什么、为什么叫"半 ORM"、优缺点
- 第 2 章 核心组件：SqlSessionFactory、SqlSession、Mapper 接口、映射文件，以及一个可运行的最小示例
- 第 3 章 基础用法：`#{}` 与 `${}`、映射标签、动态 SQL、工作流程、延迟加载、模糊查询
- 第 4 章 进阶机制：一二级缓存、懒加载与预加载、动态数据源、分页、插件
- 第 5 章 常见问题：与 JPA 的对比、速查表、常见坑
- 第 6 章 小结与参考资料

## 1 MyBatis 概述

本章回答三个问题：MyBatis 是什么、它处在 JDBC 与全自动 ORM 之间的哪个位置、以及什么场景该用它。

### 1.1 什么是 MyBatis

**持久化（persistence）**指把内存里的对象状态保存到数据库等介质中，并在需要时读回来；**持久化框架**就是替你做这件事的工具。

MyBatis 是一个 Java 持久化框架，核心职责是在 **Java 对象**和**关系型数据库的表**之间搬运数据：你写 SQL，它负责把方法参数塞进 SQL、把结果集（`ResultSet`）组装成对象、替你管理连接和事务。

生活化比喻：用 JDBC 像是自己买水泥、砌墙、刷漆，全程手工；全自动 ORM 像是精装修全包，你只说"我要一个三居室"，家具怎么摆由装修公司决定；MyBatis 更接近"你出设计图纸，施工队负责施工"——SQL 这张图纸由你画，框架负责把材料准确搬到位。

**主要特点**：

- 直接编写 SQL，便于针对性地优化查询；
- 可以充分利用数据库自身特性（窗口函数、特定语法、存储过程等）处理复杂业务；
- 自动映射只覆盖"列名 → 属性名"这一层，**表与对象之间的整体映射、尤其是关联关系仍需手动配置**；
- 控制粒度细，换来的代价是需要自己维护 SQL。

> 说明：早期资料常说"MyBatis 完全不做自动映射"，这不准确。MyBatis 的 `autoMappingBehavior` 默认值是 `PARTIAL`，会按列名自动匹配同名属性（忽略大小写），只是在遇到嵌套结果映射时不自动展开。

### 1.2 为什么说 MyBatis 是"半 ORM"

ORM（Object-Relational Mapping，对象关系映射）指把对象和表的记录对应起来的技术。按"SQL 由谁写、映射由谁做"可以把常见方案分成三档。

| 类型 | 代表 | SQL 由谁写 | 映射由谁做 |
| --- | --- | --- | --- |
| 纯 JDBC | JDBC API | 开发者 | 开发者手写 `rs.getString(...)` |
| 半自动 ORM | MyBatis | 开发者 | 框架做列到属性，关系由配置决定 |
| 全自动 ORM | Hibernate 等 | 框架生成 | 框架 |

"半"字的含义就是：**SQL 的可控性留在开发者手里，重复劳动交给框架。**

### 1.3 优点与缺点

| 维度 | 优点 | 代价 |
| --- | --- | --- |
| SQL 控制 | 想怎么优化就怎么优化，执行计划一目了然 | 需要自己写、自己调 |
| 入门难度 | 会 SQL 就能上手 | 插件、缓存等机制仍需额外理解 |
| 数据库特性 | 可用任何方言特性 | SQL 与具体数据库绑定，换库要改 |
| 映射配置 | 结果映射灵活、可控 | 表多、字段多时 XML 量较大 |
| 可移植性 | 不隐藏 SQL，排查问题直观 | 与数据库的耦合度高于全自动 ORM |

结论：**查询复杂、性能敏感、SQL 需要精细控制的系统适合 MyBatis；以简单 CRUD 为主、希望少写 SQL 的系统，全自动 ORM 更省事。**

## 2 核心组件

本章介绍 MyBatis 的四个核心对象，以及它们在一次数据库调用中各自扮演的角色。把四个对象对上号，后面所有配置项都能找到归属。

### 2.1 四个核心组件

| 组件 | 职责 | 生命周期 |
| --- | --- | --- |
| `SqlSessionFactory` | 会话工厂：加载配置与映射文件、持有 `Configuration`（内含数据源与事务管理器信息）、创建 `SqlSession` | 应用级，全局建一次 |
| `SqlSession` | 与数据库交互的入口：执行 SQL、提交/回滚事务、获取 Mapper 实例 | 请求级，用完即关 |
| Mapper 接口 | 声明数据库操作的方法签名，由框架用动态代理生成实现 | 随 `SqlSession` 获取 |
| 映射文件（Mapper XML） | 定义 SQL、参数映射、结果映射 | 启动时加载 |

几个容易踩的点：

1. `SqlSessionFactory` 是**线程安全**的，应当复用；每次请求都 new 一个是很常见的性能浪费。
2. `SqlSession` **不是线程安全的**，必须一次请求一个，并用 try-with-resources 关闭。
3. Mapper 接口不需要实现类，也不需要继承任何父接口——方法名与映射文件里的 `id` 对上即可。
4. 一个 `SqlSessionFactory` 只对应**一个**数据库环境；要连两个库，就得建两个工厂，或在上层做数据源路由（见 4.5）。

生活化比喻：`SqlSessionFactory` 像一家银行的营业厅（网点信息、业务规则都在这里，全天不变），`SqlSession` 像你取的一个号，办完一次业务就该作废；Mapper 接口像柜台上贴的业务清单，你按名字点名，柜员（也就是动态代理）就知道该走哪套流程。

### 2.2 一个最小可运行示例

下面几个文件构成一个能跑起来的最小工程，适合第一次接触时对照理解。

**（1）全局配置文件 `mybatis-config.xml`**

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<configuration>
  <!-- 打开下划线转驼峰：user_name -> userName -->
  <settings>
    <setting name="mapUnderscoreToCamelCase" value="true"/>
  </settings>

  <environments default="dev">
    <environment id="dev">
      <transactionManager type="JDBC"/>
      <dataSource type="POOLED">
        <property name="driver" value="com.mysql.cj.jdbc.Driver"/>
        <property name="url" value="jdbc:mysql://localhost:3306/demo"/>
        <property name="username" value="demo"/>
        <property name="password" value="demo"/>
      </dataSource>
    </environment>
  </environments>

  <mappers>
    <mapper resource="mapper/UserMapper.xml"/>
  </mappers>
</configuration>
```

**（2）映射文件 `mapper/UserMapper.xml`**

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<mapper namespace="demo.UserMapper">

  <select id="findById" resultType="demo.User">
    SELECT id, user_name, age FROM t_user WHERE id = #{id}
  </select>

</mapper>
```

> 实际项目里这份文件的开头通常还有一行 DTD 声明，用于 IDE 校验和自动补全，省略不影响运行。`namespace` 必须与 Mapper 接口的全限定名一致。

**（3）Mapper 接口与实体类**

```java
package demo;

public interface UserMapper {
    User findById(Long id);
}
```

```java
package demo;

public class User {
    private Long id;
    private String userName;
    private Integer age;
    // getter / setter 省略
}
```

**（4）调用方**

```java
package demo;

import java.io.InputStream;
import org.apache.ibatis.io.Resources;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;

public class Main {
    public static void main(String[] args) throws Exception {
        try (InputStream in = Resources.getResourceAsStream("mybatis-config.xml")) {
            SqlSessionFactory factory = new SqlSessionFactoryBuilder().build(in);
            try (SqlSession session = factory.openSession()) {
                UserMapper mapper = session.getMapper(UserMapper.class);
                System.out.println(mapper.findById(1L).getUserName());
            }
        }
    }
}
```

### 2.3 Spring Boot 项目里的常见配置

实际项目多用 `mybatis-spring-boot-starter`，此时通常不必手写 `mybatis-config.xml`，用 `application.yml` 配置即可（属性前缀统一是 `mybatis`）：

```yaml
mybatis:
  mapper-locations: classpath:mapper/*.xml
  type-aliases-package: com.example.demo.domain
  configuration:
    map-underscore-to-camel-case: true
    default-fetch-size: 100
    default-statement-timeout: 30
```

需要注意：`configuration.*` 与 `config-location` 不能同时使用——一旦指定了 XML 配置文件，这些嵌套属性就交给 XML 管理。

## 3 基础用法

本章覆盖日常写业务最常用的部分：参数占位符、映射标签、动态 SQL、执行流程、延迟加载与模糊查询。

### 3.1 #{} 和 ${} 的区别

**是什么**：两者都是映射文件里的取值语法。`#{}` 生成 JDBC 的占位符 `?`，值通过 `PreparedStatement` 的 `setXxx()` 绑定；`${}` 是**字符串替换**，在 SQL 拼装阶段就把值原样写进 SQL 文本。

**为什么需要区分**：`#{}` 的值始终被当作"数据"，不参与 SQL 语法解析，因此不会因这个参数引入注入；`${}` 的值成了 SQL 的一部分，一旦来自用户输入就可能改写语句语义。而有些位置（表名、列名、`ORDER BY` 字段）JDBC 不允许用 `?` 占位，只能拼接，`${}` 就是为这类场景保留的。

| 维度 | `#{}` | `${}` |
| --- | --- | --- |
| 生成的 SQL | 占位符 `?` | 值直接拼进 SQL 文本 |
| SQL 注入 | 不会 | 有风险，必须自行校验 |
| 执行计划复用 | 通常可以复用 | 值不同则 SQL 文本不同，通常更难复用（差异取决于数据库与驱动） |
| 典型用途 | 参数传递 | 动态表名、列名、`ORDER BY` 字段 |
| 建议 | 默认都用它 | 仅在无法用占位符时使用，且必须白名单校验 |

```sql
-- #{}：预编译，值不参与语法解析
SELECT * FROM t_user WHERE id = #{id}
-- 实际发送给数据库的语句：SELECT * FROM t_user WHERE id = ?

-- ${}：直接拼接，存在 SQL 注入风险
SELECT * FROM t_user WHERE id = ${id}
```

### 3.2 XML 映射文件里有哪些标签

| 标签 | 作用 |
| --- | --- |
| `<select>` | 查询语句 |
| `<insert>` | 插入语句 |
| `<update>` | 更新语句 |
| `<delete>` | 删除语句 |
| `<resultMap>` | 结果映射：定义列与属性的对应关系 |
| `<sql>` | 可复用的 SQL 片段 |
| `<include>` | 在语句中引用 `<sql>` 片段 |
| `<cache>` | 为当前命名空间开启二级缓存 |
| `<cache-ref>` | 引用另一个命名空间的缓存配置 |

`<resultMap>` 内部还有几个常用子标签：`<id>`（主键列）、`<result>`（普通列）、`<association>`（一对一）、`<collection>`（一对多）、`<discriminator>`（按列值选择不同映射）。

```xml
<sql id="baseColumns">id, user_name, age</sql>

<select id="findAll" resultType="demo.User">
  SELECT <include refid="baseColumns"/> FROM t_user
</select>
```

### 3.3 动态 SQL 是什么

**是什么**：在 XML 里用标签拼装 SQL，让同一条语句根据参数不同生成不同的 SQL 文本。判断条件用 OGNL 表达式（一种写在字符串里的条件表达式语法）。

**为什么需要**：条件查询、批量操作、可选字段更新这些场景，如果靠 Java 里拼字符串，很容易漏空格、漏逗号、多出 `AND`。

| 标签 | 作用 | 相当于 Java 里的 |
| --- | --- | --- |
| `<if>` | 条件成立才拼接 | `if` |
| `<choose>` / `<when>` / `<otherwise>` | 多分支里选一个 | `switch` |
| `<where>` | 有内容时才加 `WHERE`，并去掉开头的 `AND` / `OR` | 自动补 `WHERE` 的拼接器 |
| `<set>` | 动态拼 `SET`，并去掉多余的逗号 | 自动补 `SET` 的拼接器 |
| `<trim>` | `where` / `set` 的通用版，可自定义前后缀 | 自定义拼接器 |
| `<foreach>` | 遍历集合，拼 `IN (...)` 或批量插入 | `for` |
| `<bind>` | 用 OGNL 表达式定义一个变量 | 局部变量 |

```xml
<select id="search" resultType="demo.User">
  SELECT id, user_name, age FROM t_user
  <where>
    <if test="name != null and name != ''">
      AND user_name = #{name}
    </if>
    <if test="minAge != null">
      AND age &gt;= #{minAge}
    </if>
  </where>
</select>
```

```xml
<!-- 批量插入：foreach 拼出多行 values -->
<insert id="insertBatch">
  INSERT INTO t_user (user_name, age) VALUES
  <foreach collection="list" item="u" separator=",">
    (#{u.userName}, #{u.age})
  </foreach>
</insert>
```

> 提示：XML 里的 `<`、`>` 要写成 `&lt;`、`&gt;`，或者用 `<![CDATA[ ... ]]>` 包起来。

### 3.4 工作流程

一次完整调用会经过下面六步：

1. **加载配置**：读取 `mybatis-config.xml` 与各映射文件，构建全局唯一的 `Configuration`，再由 `SqlSessionFactoryBuilder` 造出 `SqlSessionFactory`；
2. **打开会话**：`factory.openSession()` 从数据源取连接并开启事务（默认不是自动提交）；
3. **获取 Mapper**：`session.getMapper(XxxMapper.class)` 返回一个动态代理对象；
4. **执行 SQL**：调用代理方法 → 找到对应的 `MappedStatement` → 交给 `Executor` 执行，参数绑定与结果映射由框架完成；
5. **提交或回滚**：写操作必须显式 `commit()`，否则会话关闭时会被回滚；
6. **关闭会话**：释放连接，归还连接池。

第 5 步是新手最容易漏的：**MyBatis 默认不自动提交**，插入成功了却查不到数据，多数是这个原因。

### 3.5 延迟加载

**是什么**：查询主对象时先不查它的关联对象，等代码真正访问关联属性时才补一条 SQL。

**为什么需要**：关联数据可能很大而且常常用不到，提前查出来既慢又占内存。

**怎么配**：

```xml
<settings>
  <setting name="lazyLoadingEnabled" value="true"/>
  <setting name="proxyFactory" value="JAVASSIST"/>
</settings>
```

- `lazyLoadingEnabled` 默认 `false`；置为 `true` 后所有关联关系默认改为延迟加载，单个关联可用 `fetchType="eager"` 覆盖。
- 延迟加载靠**代理对象**实现：框架给主对象生成一个代理，访问 `getAuthor()` 时才触发查询。`proxyFactory` 可选 `JAVASSIST`（3.3 起为默认值）或 `CGLIB`（自 3.5.10 起标记为废弃）。
- `aggressiveLazyLoading` 这个参数常被误解，它的真实语义见 4.4 节。

### 3.6 模糊查询 like 怎么写

三种写法，按推荐程度排列。

**方式一：`CONCAT` 拼接占位符（推荐）**

```sql
SELECT * FROM t_user WHERE user_name LIKE CONCAT('%', #{name}, '%')
```

**方式二：`<bind>` 标签先算好模式串（推荐）**

```xml
<select id="searchByName" resultType="demo.User">
  <bind name="pattern" value="'%' + name + '%'"/>
  SELECT * FROM t_user WHERE user_name LIKE #{pattern}
</select>
```

**方式三：`${}` 直接拼接（不推荐）**

```sql
SELECT * FROM t_user WHERE user_name LIKE '%${name}%'
```

> 补充：`CONCAT` 是 MySQL、PostgreSQL、Oracle 等数据库都支持的函数，SQL Server 2012 起也支持。跨库项目更稳妥的做法是在 Java 里拼好通配符，再作为普通参数传给 `#{}`。

### 3.7 使用 like 时如何防止 SQL 注入

原则只有一条：**让用户输入永远以参数形式进入 SQL，而不是成为 SQL 文本的一部分。**

- 首选 `CONCAT` 或 `<bind>`，把值交给 `#{}` 绑定；
- 或者在 Service 层拼好 `%name%`，作为普通字符串参数传给 `#{}`；
- 不要用 `${}` 拼接用户输入；确实必须拼（例如动态排序字段）时用白名单校验，例如只允许 `id`、`age`、`create_time` 三个值；
- 通配符本身也要留意：用户输入的 `%`、`_` 会被当成通配符，必要时做转义。

## 4 进阶机制

本章讲机制层面的内容：缓存、懒加载的真实语义、数据源路由、分页与插件。初学阶段建议先看 4.2 和 4.6，其余按需查阅。

### 4.1 内部执行链路

比 3.4 节更细一层的调用链：

```text
SqlSession.getMapper()  ->  动态代理（MapperProxy）
        ↓
Executor（SIMPLE / REUSE / BATCH，负责一二级缓存与事务）
        ↓
StatementHandler（创建 Statement、设置参数、执行）
        ↓
ParameterHandler（参数绑定）          ResultSetHandler（结果映射）
        ↓
JDBC Driver  ->  数据库
```

其中 `Executor`、`StatementHandler`、`ParameterHandler`、`ResultSetHandler` 四个组件都可被插件拦截（见 4.7），这也是 MyBatis 扩展性较好的原因。

### 4.2 一级缓存与二级缓存

**一级缓存（local cache）**：作用域是**一个 `SqlSession`**。同一会话内，相同语句 + 相同参数 + 相同分页参数的查询只会真正打一次数据库。它默认开启，并在 `update`、`commit`、`rollback`、`close` 时被清空。实现类是 `PerpetualCache`，内部就是一个 `HashMap`。

**二级缓存（second level cache）**：作用域是**一个命名空间（namespace）**，跨 `SqlSession` 共享。它默认关闭，需要在映射文件里加一行 `<cache/>` 开启。

| 特性 | 一级缓存 | 二级缓存 |
| --- | --- | --- |
| 作用域 | 同一个 `SqlSession` | 同一个 namespace，跨会话 |
| 默认开启 | 是（无法完全关闭） | 否，需 `<cache/>` |
| 失效时机 | `update`、`commit`、`rollback`、`close` | 同 namespace 的写操作、`flushCache="true"` |
| 底层存储 | `HashMap`（`PerpetualCache`） | 可替换实现（Ehcache、Redis 等） |

```xml
<mapper namespace="demo.UserMapper">
  <!-- 开启二级缓存；默认 LRU、最多 1024 个引用、无刷新间隔、读写模式 -->
  <cache eviction="LRU" flushInterval="60000" size="512" readOnly="true"/>
  ...
</mapper>
```

`<cache/>` 的默认行为（官方文档有明确说明）：使用 LRU 淘汰策略、不按时间刷新、最多缓存 1024 个对象引用、读写模式（`readOnly=false`，返回序列化副本，较慢但更安全）。

还有两个开关值得记住：

- `cacheEnabled`（全局设置，默认 `true`）是二级缓存的总开关；
- `localCacheScope`（默认 `SESSION`）可设为 `STATEMENT`，让一级缓存只在单条语句内有效，能规避"同一会话读到旧数据"的问题。

> 注意：一级缓存返回的是**缓存中的同一个对象引用**，修改返回对象会污染缓存。实践中的建议是不要修改 MyBatis 返回的对象，或者把 `localCacheScope` 设为 `STATEMENT`。

### 4.3 二级缓存的缺点

- **一致性难保证**：缓存以 namespace 为单位，跨表、跨 namespace 的写操作不会互相同步；多实例部署时各节点缓存独立，读到旧数据的概率更高。
- **分布式同步困难**：进程内缓存无法天然共享，通常要换成 Redis 之类的集中式实现，随之引入序列化、网络开销与新的失效策略问题。
- **缓存穿透、击穿、雪崩风险**：查不到的数据不会被缓存，请求每次都落到数据库（穿透）；热点 key 过期的瞬间大量请求压到数据库（击穿）；大批 key 同时失效造成数据库瞬时压力（雪崩）。
- **内存占用可控性差**：默认只限制条目数（1024），不限制总内存，大结果集容易占满内存。
- **不适合强实时场景**：对"写完立刻要读到最新值"的业务，二级缓存往往是负担而非收益。

结论：**多数互联网业务优先考虑在业务层用 Redis 做缓存，而不是依赖 MyBatis 二级缓存。**

### 4.4 懒加载与预加载

这一节要澄清一个常见的错误说法。

| 概念 | 含义 | 怎么开 |
| --- | --- | --- |
| 懒加载（lazy loading） | 访问关联属性时才查库 | 全局 `lazyLoadingEnabled=true`，或单个关联写 `fetchType="lazy"` |
| 预加载（eager loading） | 查主对象时顺带把关联对象查出来 | 单个关联写 `fetchType="eager"`（会覆盖全局设置） |

`aggressiveLazyLoading` **不是**"预加载开关"。它的真实含义是：开启后，**对主对象的任意方法调用都会把它所有延迟属性一次性加载出来**；关闭时则按需逐个加载。它的默认值在 MyBatis 3.4.2 发生了变化——3.4.1 及更早版本默认 `true`，3.4.2 起默认 `false`。

所以正确的表述是：

- `lazyLoadingEnabled=true` 配合 `aggressiveLazyLoading=false`（3.4.2 及以上版本的默认组合）= 真正按需加载；
- 想预加载某个关联，用 `fetchType="eager"`，而不是去动 `aggressiveLazyLoading`。

### 4.5 动态数据源切换

先说明一点：**动态数据源不是 MyBatis 自带的能力**，它依赖 Spring 提供的 `AbstractRoutingDataSource`（位于 `org.springframework.jdbc.datasource.lookup` 包）。理解这一点，可以避免在纯 MyBatis 项目里白找一顿对应 API。

**是什么**：一个"路由器"数据源。它本身不连数据库，而是持有一组真实数据源，每次 `getConnection()` 时根据当前查找键（lookup key）挑一个。

**为什么需要**：读写分离、分库、多租户等场景，需要在不改业务代码的前提下切换底层连接。

**怎么做**（四步）：

1. 继承 `AbstractRoutingDataSource`；
2. 重写 `determineCurrentLookupKey()`，返回本次要用的数据源标识；
3. 用 `ThreadLocal` 保存这个标识（一次请求可能跨多个方法，需要线程内传递）；
4. 用 AOP 或自定义注解在方法进入/退出时设置、清理标识。

```java
public class DynamicDataSource extends AbstractRoutingDataSource {
    @Override
    protected Object determineCurrentLookupKey() {
        return DataSourceContextHolder.get();   // 从 ThreadLocal 读
    }
}
```

```java
public final class DataSourceContextHolder {
    private static final ThreadLocal<String> KEY = new ThreadLocal<>();

    public static void set(String key) { KEY.set(key); }

    public static String get() { return KEY.get(); }

    // 务必在请求结束时清理，避免线程池复用导致串库
    public static void clear() { KEY.remove(); }
}
```

> 第 4 步里的 `clear()` 很容易被忽略：线程池会复用线程，不清理就可能让下一个请求莫名其妙连到上一个请求的库。

### 4.6 分页的三种做法

| 做法 | 原理 | 优点 | 缺点 |
| --- | --- | --- | --- |
| 内存分页 | 查出全部结果后在内存里截取（`RowBounds` 或 `List.subList`） | 不改 SQL，写法简单 | 数据量大时内存与网络开销高，深分页尤其慢 |
| SQL 分页 | 在 SQL 里写 `LIMIT`/`OFFSET`、`ROWNUM`、`TOP` 等 | 只取需要的数据，性能最好 | 方言不同，SQL 需按数据库改写 |
| 插件分页 | 由拦截器在执行前改写 SQL（如 PageHelper） | 业务代码不用写分页 SQL | 引入额外依赖，SQL 被改写后排查略复杂 |

几点补充：

- `RowBounds` 是 MyBatis 内置的分页参数，原理是**跳过前 N 条、返回 M 条**，本质上仍是把结果集取回来再丢弃，属于内存分页；官方文档也提示其效率取决于驱动。
- SQL 分页写法与数据库强相关：MySQL、PostgreSQL、SQLite 常用 `LIMIT ... OFFSET ...`；Oracle 12c 起支持 `OFFSET ... FETCH`；SQL Server 2012 起支持 `OFFSET ... FETCH`。
- PageHelper 是常用的 MyBatis 分页插件，通过拦截 `Executor` 把 SQL 改写成对应数据库的物理分页语句；使用它需要额外引入 `pagehelper` 与 `jsqlparser` 依赖（它支持 MyBatis 3.1.0 及以上版本）。

### 4.7 插件能在哪些地方拦截

MyBatis 允许在四个组件的指定方法上插入拦截逻辑，下面是官方文档列出的完整清单：

| 组件 | 可拦截的方法 |
| --- | --- |
| `Executor` | `update`、`query`、`flushStatements`、`commit`、`rollback`、`getTransaction`、`close`、`isClosed` |
| `StatementHandler` | `prepare`、`parameterize`、`batch`、`update`、`query` |
| `ParameterHandler` | `getParameterObject`、`setParameters` |
| `ResultSetHandler` | `handleResultSets`、`handleOutputParameters` |

常见用途：分页（`Executor.query`）、SQL 打印与耗时统计（`StatementHandler`）、多租户或数据权限的过滤条件拼接（`Executor` / `StatementHandler`）、加密字段自动解密（`ResultSetHandler`）。

### 4.8 编写一个插件

四步：实现 `Interceptor` 接口 → 用 `@Intercepts` + `@Signature` 声明拦截点 → 在 `intercept` 里写前置/后置逻辑 → 注册到配置中。

```java
import java.util.Properties;
import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.plugin.Interceptor;
import org.apache.ibatis.plugin.Invocation;
import org.apache.ibatis.plugin.Intercepts;
import org.apache.ibatis.plugin.Plugin;
import org.apache.ibatis.plugin.Signature;
import org.apache.ibatis.session.ResultHandler;
import org.apache.ibatis.session.RowBounds;

@Intercepts({
    @Signature(
        type = Executor.class,
        method = "query",
        args = {MappedStatement.class, Object.class, RowBounds.class, ResultHandler.class}
    )
})
public class SqlCostPlugin implements Interceptor {

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            return invocation.proceed();          // 继续执行被拦截的方法
        } finally {
            System.out.println("SQL 耗时(ms) = " + (System.currentTimeMillis() - start));
        }
    }

    @Override
    public Object plugin(Object target) {
        return Plugin.wrap(target, this);         // 交给框架生成代理
    }

    @Override
    public void setProperties(Properties properties) {
        // 读取 <plugin> 下的 <property> 配置
    }
}
```

```xml
<plugins>
  <plugin interceptor="demo.SqlCostPlugin">
    <property name="slowMillis" value="500"/>
  </plugin>
</plugins>
```

> 关键细节：`args` 必须与目标方法的参数列表**完全一致**。`Executor.query` 有 4 个参数和 6 个参数两个重载，签名写错插件就不会生效，而且通常不会给出明显报错。

### 4.9 插件的运行原理

基于**动态代理**：MyBatis 在创建 `Executor`、`StatementHandler` 等核心对象时，会依次用每个插件把它们包装一层。调用时先进入最外层的代理，执行插件的 `intercept`，再通过 `invocation.proceed()` 逐层向内传递，最终到达真实对象。多个插件形成一条链，顺序与注册顺序相关。

一句话记忆：**拦截器不修改目标类，而是在外面套一层"洋葱皮"，每一层都能在方法调用前后插一脚。**

### 4.10 进阶了解（可跳过）

本节涉及实现细节，初学可略过，遇到具体问题再回来查。

- **代理链的实现**：`Plugin` 类本身实现了 `InvocationHandler`，`Plugin.wrap(target, interceptor)` 会判断目标对象实现了哪些接口并为它生成代理。因此"哪些方法能被拦截"取决于接口声明，而不是任意方法。
- **一级缓存的键**：缓存键（`CacheKey`）通常由语句 id、SQL 文本、参数值、分页参数等共同决定，所以"参数不同却命中同一缓存"一般不会发生；但分页参数是否参与键的构成会影响命中率，调优时值得留意。
- **`Executor` 的三种类型**：`SIMPLE`（每条语句新建 `PreparedStatement`）、`REUSE`（复用 `PreparedStatement`）、`BATCH`（批量执行写操作，需手动 `flushStatements()`）。批量导入场景用 `BATCH` 往往能显著减少往返次数，但批量模式对自增主键回填等特性的支持有限，需要额外处理。

## 5 常见问题

本章用问答与速查表收尾，方便定向查阅。

### 5.1 MyBatis 与 JPA 有哪些不同

先澄清概念：JPA（Java Persistence API，现名 Jakarta Persistence）是一套 **ORM 规范**，Hibernate 是它最常见的实现之一。所以严格来说，与 MyBatis 对比的是"JPA 体系（以 Hibernate 为代表）"，而不是某个具体产品。

| 维度 | MyBatis | JPA（以 Hibernate 为例） |
| --- | --- | --- |
| SQL 来源 | 开发者手写 | 框架按映射生成，也可写原生 SQL |
| 映射方式 | 列到属性为主，关联关系手动配 | 注解声明实体与关联，自动生成 |
| 上手成本 | 会 SQL 就能用 | 需要理解实体生命周期、脏检查、抓取策略 |
| 优化手段 | 直接改 SQL，所见即所得 | 依赖抓取策略、缓存与批量配置，调优更间接 |
| 数据库耦合 | 较高（SQL 用方言特性） | 较低（可切换方言） |
| 适用场景 | 复杂查询、报表、SQL 需精调 | 领域模型清晰、以 CRUD 为主 |

两者并非互斥：同一项目里可以用 JPA 处理常规 CRUD，用 MyBatis 处理复杂查询。

### 5.2 模糊查询速查

| 写法 | 片段 | 是否推荐 |
| --- | --- | --- |
| `CONCAT` | `... LIKE CONCAT('%', #{name}, '%')` | 推荐 |
| `bind` | `<bind name="pattern" value="'%' + name + '%'"/>` 后接 `LIKE #{pattern}` | 推荐 |
| `${}` | `... LIKE '%${name}%'` | 不推荐（注入风险） |

### 5.3 一二级缓存速查

| 问题 | 一级缓存 | 二级缓存 |
| --- | --- | --- |
| 作用范围 | 一个 `SqlSession` | 一个 namespace |
| 是否需要配置 | 默认开启 | 需要 `<cache/>` |
| 何时失效 | `update`、`commit`、`rollback`、`close` | 同 namespace 写操作、`flushCache="true"` |
| 能否跨会话 | 不能 | 能 |

### 5.4 几个常见坑

- **写完查不到**：忘了 `commit()`，会话关闭时事务被回滚。
- **字段映射不上**：列名 `user_name` 与属性 `userName` 不匹配，打开 `mapUnderscoreToCamelCase` 或写列别名。
- **返回对象被改坏**：一级缓存返回同一引用，改动会污染后续查询。
- **动态 SQL 少了空格**：`<if>` 之间要留空格，或用 `<where>` / `<trim>` 兜底。
- **`${}` 拼了用户输入**：排序字段、表名要白名单校验。
- **`SqlSession` 没关**：连接池很快被耗尽，用 try-with-resources。

## 6 小结

本文从"是什么"讲到"怎么用"，再到"为什么这样设计"：MyBatis 用"手写 SQL + 自动映射"的方式，在 JDBC 的繁琐与全自动 ORM 的黑盒之间取了一个平衡点。掌握四个核心组件（`SqlSessionFactory`、`SqlSession`、Mapper 接口、映射文件）、两条取值语法（`#{}` 与 `${}`）、一套动态 SQL 标签、两级缓存的作用域，以及插件的拦截点，日常开发与排查基本够用；更深入的内容（代理链、缓存键、批量执行器）留到遇到具体问题时再研究。

## 参考资料

以下为本文核对事实时参考的公开资料，均为纯文字条目：

- MyBatis 官方参考文档（MyBatis 3，版本 3.5.19，2025 年 1 月发布）：配置 XML、Mapper XML、动态 SQL、Java API 四章。
- MyBatis-Spring-Boot-Starter 官方文档（4.0.0）：Configuration 一节列出的 `mybatis.*` 属性。
- Spring Framework API 文档：`org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource` 类说明。
- PageHelper（MyBatis 分页插件）项目说明文档：物理分页、支持 MyBatis 3.1.0 及以上。
- MyBatis 源码：`org.apache.ibatis.executor.Executor` 接口、`org.apache.ibatis.cache.impl.PerpetualCache` 类。
