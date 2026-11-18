# Oracle 核心机制与实践：并行查询、共享池与 REF CURSOR

本文面向已经能写 Java CRUD、但还没有系统接触过 Oracle 内部机制的开发者，围绕三个在真实项目里最常被问到、也最容易踩坑的主题展开：并行查询（Parallel Query）、共享池（Shared Pool），以及在 Java 中处理 REF CURSOR。每个主题都按"是什么 → 为什么需要 → 怎么用"的顺序推进，涉及参数的结论均以 Oracle 官方文档为准，并标注适用版本。

## 本文导读

- 第一章：读懂后文需要的 Oracle 基础概念（实例、SGA、数据字典视图、一条 SQL 的执行过程）
- 第二章：并行查询——是什么、数据库内部怎么组织、Java 端要不要做事、怎么验证并行真的发生了
- 第三章：共享池——为什么同一句 SQL 第二次更快、绑定变量与连接池怎么配合
- 第四章：REF CURSOR——存储过程返回结果集时，Java 端怎么接、资源怎么关
- 第五章：参考资料

## 一、先补齐几个基础概念

这一章只讲后文会用到的概念，目的是让"共享池在内存的哪个位置""为什么改参数要重启"这类问题有落脚点。已经熟悉 Oracle 体系结构的读者可以直接跳到第二章。

### 1.1 实例与数据库

**数据库（database）**是磁盘上的一组文件：数据文件、控制文件、重做日志文件等。**实例（instance）**是内存结构加后台进程，负责读写这些文件。通过 JDBC 连接的其实是实例；实例停了，磁盘上的文件还在。

比喻：数据库像图书馆的书架，实例像管理员和检索台——书在架子上不会动，能不能查到、查得多快，取决于管理员怎么干活。

### 1.2 SGA 与 PGA

实例的内存分成两大部分：

- **SGA（System Global Area，系统全局区）**：所有会话共享，包含数据库缓冲区缓存（buffer cache，缓存数据块）、共享池（shared pool）、重做日志缓冲区（redo log buffer）、大池（large pool）等组件。
- **PGA（Program Global Area，程序全局区）**：每个服务进程私有，存放排序区、哈希区这类"工作台"内存。

共享池属于 SGA，这一点很关键：**放在共享池里的东西，所有会话都能复用**，所以一句 SQL 的执行计划被缓存后，第二个用户执行同样的语句就不用重新优化。

### 1.3 数据字典与动态性能视图

**数据字典（data dictionary）**是 Oracle 自己维护的元数据表，例如 `USER_TABLES`、`ALL_TABLES` 记录表和列的定义。**动态性能视图**以 `V$` 开头（如 `V$SQL`、`V$SQL_MONITOR`、`V$LIBRARYCACHE`），内容来自内存中的运行时统计，实例重启后清零——所以排查"刚才那条 SQL 为什么慢"要在问题还在时赶紧查。

### 1.4 一条 SQL 在数据库里经历什么

一条语句大致经历四个阶段：解析（parse，做语法与语义检查，并在共享池里找可复用的执行计划）→ 优化（optimizer 计算代价并生成执行计划）→ 执行（真正读数据、做连接与聚合）→ 取数（fetch，把结果行返回客户端）。

第二章关心"执行"阶段能不能拆给多个进程并行，第三章关心"解析"阶段能不能复用已有的执行计划。

## 二、并行查询（Parallel Query）

本章讲并行查询：它的定义、数据库内部的组织方式、Java 端需要做什么（结论是很少），以及如何用视图确认并行确实生效。

### 2.1 是什么

**并行查询（Parallel Query）**指数据库把一条 SQL 的执行拆成多个子任务，交给多个**并行执行服务器进程**（parallel execution server，简称 PX 进程）同时处理，最后由一个协调进程汇总结果。衡量并行规模的指标叫**并行度**（degree of parallelism，DOP），含义是"单个操作上同时干活的 PX 进程数"。

比喻：一个人清点整座仓库要 8 小时；8 个人分片清点、最后汇总，理论上一小时能完事。但"分片、汇总、互相等待"本身要花时间，人越多协调成本越高——这就是并行不是越多越好的原因。

### 2.2 为什么需要

并行是为"数据量大、单条语句耗时久、系统还有空闲资源"这类场景准备的。Oracle 官方文档给出的判断标准可以直接拿来对照：

| 更适合并行 | 更不适合并行 |
| --- | --- |
| 大表的全表扫描、大表连接、分区索引扫描 | 只返回少量行的小查询 |
| 复杂聚合、报表类查询 | 高并发 OLTP（语句通常一两秒内结束） |
| 批量 INSERT/UPDATE/DELETE、建大索引、建大表 | CPU、内存或 I/O 已经吃紧的系统 |
| 低并发、响应时间优先 | 效率（资源利用率）优先 |

官方文档明确指出：并行适用于大结果集、低并发、响应时间重要的场景；当 CPU、内存或 I/O 资源已经被大量占用时，并行不但没有收益，还可能拖慢系统。

### 2.3 数据库内部怎么组织

理解下面五个步骤，就能解释"为什么并行查询有时会报找不到足够 PX 进程"：

1. 发起 SQL 的会话变成**查询协调进程**（query coordinator，QC）。
2. QC 向 PX 进程池申请 PX 进程，数量取决于语句的 DOP。
3. PX 进程按**生产者/消费者模型**工作：一组负责扫描数据（生产者），另一组负责连接、排序、聚合（消费者）。两组可以同时干活，这叫操作间并行。
4. 每一组 PX 进程的数量等于 DOP，因此**一条并行语句通常要占用约 2 × DOP 个 PX 进程**。
5. QC 完成无法并行的收尾工作（例如把各进程的小计再加总），然后把结果返回给客户端。

| 语句 DOP | 单组 PX 进程 | 通常占用的 PX 进程总数 | 说明 |
| --- | --- | --- | --- |
| 2 | 2 | 约 4 | 小规模并行，适合试水 |
| 4 | 4 | 约 8 | 文档中最常见的示例取值 |
| 8 | 8 | 约 16 | 需要核对 `PARALLEL_MAX_SERVERS` 是否够用 |

### 2.4 怎么开启并行

开启并行有三条路，作用范围各不相同：

| 方式 | 写法 | 生效范围 | 注意事项 |
| --- | --- | --- | --- |
| 对象级 | 建表或改表时写 `PARALLEL n` | 访问该对象的语句 | 仅在 `PARALLEL_DEGREE_POLICY` 为 `MANUAL` 或 `LIMITED` 时按此并行度执行 |
| 语句级 | 优化器提示 `/*+ PARALLEL(别名, n) */` | 单条语句 | 提示写错（别名不存在等）不会报错，只会静默失效 |
| 自动 | `PARALLEL_DEGREE_POLICY = AUTO` 或 `ADAPTIVE` | 全库或全会话 | 由优化器按代价决定是否并行、用多少并行度 |

对象级的写法如下：

```sql
-- 建表时声明并行度为 4
CREATE TABLE large_sales_data (
  sale_id    NUMBER,
  product_id NUMBER,
  sale_date  DATE,
  amount     NUMBER(10,2)
) PARALLEL 4;

-- 也可以事后修改
ALTER TABLE large_sales_data PARALLEL 8;
```

需要注意语法细节：Oracle SQL 语言参考中 `parallel_clause` 的语法是 `{ NOPARALLEL | PARALLEL [ integer ] }`，并行度直接跟在 `PARALLEL` 后面；有些资料写作 `PARALLEL (DEGREE 4)`，与上述语法不一致；按官方语法应写成 `PARALLEL 4`。对象的当前并行度可以查 `ALL_TABLES` 或 `USER_TABLES` 的 `DEGREE` 列。

另外要建立一个正确预期：写在表上的并行度只是"声明这个对象适合并行"，最终是否并行、并行多少，还取决于语句、会话参数以及资源是否够用。

### 2.5 Java 端需要做什么

结论很简单：**并行几乎完全由数据库决定**。JDBC 只负责把 SQL 发出去、把结果行取回来，客户端无法"命令"数据库并行。客户端能做的是减少自己的开销：复用连接、使用绑定变量、设置合适的每次取行数。

```java
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import oracle.jdbc.pool.OracleDataSource;

public class ParallelQueryDemo {

    private static final String SQL =
        "SELECT /*+ PARALLEL(s, 4) */ " +
        "       product_id, SUM(amount) AS total_sales, COUNT(*) AS sale_count " +
        "FROM   large_sales_data s " +
        "WHERE  sale_date BETWEEN ? AND ? " +
        "GROUP BY product_id " +
        "ORDER BY total_sales DESC";

    public void run() throws SQLException {
        OracleDataSource ods = new OracleDataSource();
        ods.setURL("jdbc:oracle:thin:@//localhost:1521/ORCLPDB1");
        ods.setUser("your_username");
        ods.setPassword("your_password");

        try (Connection conn = ods.getConnection();
             PreparedStatement ps = conn.prepareStatement(SQL)) {

            // 每次网络往返多取一些行，减少 round trip（Oracle JDBC 默认预取为 10 行）
            ps.setFetchSize(500);

            ps.setDate(1, java.sql.Date.valueOf("2024-01-01"));
            ps.setDate(2, java.sql.Date.valueOf("2024-12-31"));

            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    System.out.printf("product=%d total=%.2f count=%d%n",
                        rs.getInt("product_id"),
                        rs.getDouble("total_sales"),
                        rs.getInt("sale_count"));
                }
            }
        }
    }

    public static void main(String[] args) throws SQLException {
        new ParallelQueryDemo().run();
    }
}
```

一个常见误解是用 `((OracleConnection) conn).setDefaultExecuteBatch(100)` 之类的 JDBC 调用去"启用并行查询"。该方法是 JDBC 端的批量 DML 提交批次设置，与 SQL 是否并行执行没有关系；并行与否只由对象属性、优化器提示和并行相关参数决定，因此示例中不包含这类调用。

### 2.6 怎么确认并行真的发生了

有三类手段，建议同时用：执行计划、`V$SQL`、`V$SQL_MONITOR`。

```sql
-- 手段一：执行计划出现 PX COORDINATOR、PX BLOCK ITERATOR，说明走了并行
EXPLAIN PLAN FOR
SELECT /*+ PARALLEL(s, 4) */ product_id, SUM(amount)
FROM   large_sales_data s
GROUP BY product_id;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY());
```

```sql
-- 手段二：V$SQL 里能看的是“并行执行服务器执行次数”
-- 注意：V$SQL 没有 PX_SERVERS_REQUESTED / PX_SERVERS_ALLOCATED 两列
SELECT sql_id,
       sql_text,
       px_servers_executions,
       elapsed_time / 1000000 AS elapsed_sec
FROM   v$sql
WHERE  px_servers_executions > 0
ORDER  BY elapsed_time DESC;
```

```sql
-- 手段三：申请/实际分配到的 PX 进程数要看 V$SQL_MONITOR
SELECT sql_id,
       status,
       px_servers_requested,
       px_servers_allocated,
       elapsed_time / 1000000 AS elapsed_sec
FROM   v$sql_monitor
WHERE  px_servers_requested > 0
ORDER  BY elapsed_time DESC;
```

一个容易踩的坑：在 `V$SQL` 上查询 `PX_SERVERS_REQUESTED`、`PX_SERVERS_ALLOCATED` 会直接报 `ORA-00904: 无效标识符`。按 Oracle 参考手册，`V$SQL` 只有 `PX_SERVERS_EXECUTIONS` 一列与并行相关；而 `PX_SERVERS_REQUESTED`（请求的 PX 进程总数）与 `PX_SERVERS_ALLOCATED`（实际分配的 PX 进程数）属于 `V$SQL_MONITOR`。

使用 `V$SQL_MONITOR` 还要知道它的记录条件：语句并行执行、单次执行消耗 5 秒以上 CPU 或 I/O、或者加了 `/*+ MONITOR */` 提示，满足其一才会被监控；而且监控数据在语句结束后只保留一小段时间。

### 2.7 关键参数与默认值（19c）

并行行为由一组初始化参数控制。下表默认值均取自 Oracle Database Reference 19c，可直接用于核对现场配置。

| 参数 | 作用 | 默认值 | 备注 |
| --- | --- | --- | --- |
| `PARALLEL_DEGREE_POLICY` | 是否启用自动并行度、语句排队、内存并行 | `MANUAL` | 取值 `MANUAL`/`LIMITED`/`AUTO`/`ADAPTIVE`；`ADAPTIVE` 在 12c 起提供性能反馈 |
| `PARALLEL_THREADS_PER_CPU` | 每个 CPU（核）可承载的并行进程系数 | `1` | 参与计算默认并行度和 `PARALLEL_MAX_SERVERS` |
| `PARALLEL_DEGREE_LIMIT` | 自动并行度的系统级上限 | `CPU` | 即不超过 `PARALLEL_THREADS_PER_CPU × CPU_COUNT` |
| `PARALLEL_MIN_TIME_THRESHOLD` | 预估执行时间超过该值才考虑自动并行 | `AUTO`（即 10 秒） | 需要 `PARALLEL_DEGREE_POLICY` 为 `AUTO`/`ADAPTIVE`/`LIMITED` |
| `PARALLEL_MAX_SERVERS` | 实例允许存在的 PX 进程上限 | `PARALLEL_THREADS_PER_CPU × CPU_COUNT × concurrent_parallel_users × 5` | 还会被 `PROCESSES` 减去保留进程后的值压低 |
| `PARALLEL_MIN_SERVERS` | 实例启动时即创建的 PX 进程数 | `CPU_COUNT × PARALLEL_THREADS_PER_CPU × 2` | 这些进程常驻，用于快速响应并行请求 |
| `PARALLEL_ADAPTIVE_MULTI_USER` | 按系统负载自动下调并行度 | `false` | 12c Release 2（12.2.0.1）起已废弃，官方建议改用并行语句排队 |

`concurrent_parallel_users` 的取值取决于内存参数：设置 `MEMORY_TARGET` 或 `SGA_TARGET` 时为 4；只设置 `PGA_AGGREGATE_TARGET` 时为 2；都没设置时为 1。

常用配置示例：

```sql
-- 打开自动并行度：由优化器决定是否并行、并行多少
ALTER SYSTEM SET PARALLEL_DEGREE_POLICY = AUTO;

-- 调整 PX 进程池大小
ALTER SYSTEM SET PARALLEL_MAX_SERVERS = 64;
ALTER SYSTEM SET PARALLEL_MIN_SERVERS  = 4;

-- 已废弃参数，仅在旧系统沿用、且确实需要按负载自动降并行度时才设置
-- ALTER SYSTEM SET PARALLEL_ADAPTIVE_MULTI_USER = TRUE;
```

### 2.8 并行度怎么定

默认并行度有明确公式，可以直接算出来：

- 单实例：DOP = `PARALLEL_THREADS_PER_CPU × CPU_COUNT`
- Oracle RAC：DOP = `PARALLEL_THREADS_PER_CPU × sum(CPU_COUNT)`

按 19c 的默认值 `PARALLEL_THREADS_PER_CPU = 1`，一台 16 核的机器默认 DOP 就是 16，而不是 32 或 64——这一点常被误解。

实践中通常这样定：先让 DOP 不超过该实例可用的 CPU 核数，再观察 `V$SQL_MONITOR` 的 `px_servers_allocated`、实际耗时以及系统负载，逐步微调；同时用"一条语句约占 2 × DOP 个 PX 进程"估算并发上限，避免多租户或高并发时把 `PARALLEL_MAX_SERVERS` 用光、语句退化为串行。

把并行度设成"CPU 核心数的 2~4 倍"是一种流传较广的说法，但官方文档里没有这条规则，而且按 2 × DOP 估算进程占用时很容易超配。建议以上述公式和实际观测为准；团队内部若确有历史经验值，应标注为经验值而非规则。

### 2.9 进阶了解（可跳过）

初学阶段可以略过本节。以下内容包括多表并行的提示写法、自动并行度涉及的排队机制，以及一段客户端计时对比代码。

多表并行时，提示需要写在 `SELECT` 之后、且别名必须与 `FROM` 中的别名一致：

```java
String advancedQuery =
    "SELECT /*+ PARALLEL(o, 4) PARALLEL(d, 4) USE_NL(o d) INDEX(o idx_order_date) */ " +
    "       o.customer_id, d.department_name, COUNT(*) AS order_count " +
    "FROM   orders o " +
    "JOIN   departments d ON o.department_id = d.department_id " +
    "WHERE  o.order_date > SYSDATE - 365 " +
    "GROUP  BY o.customer_id, d.department_name";
```

提示只是"建议"：`USE_NL` 要求走嵌套循环连接、`INDEX` 要求用指定索引，条件不满足时优化器会忽略提示，语句照常执行且不报错。生产环境中的提示应当配套执行计划回归测试。

自动并行度打开后，还会牵动两个机制：一是**并行语句排队**（资源不足时语句进入队列等待，而不是强行降级执行），二是**内存并行执行**（数据在内存列式存储中并行扫描）。这两者都由 `PARALLEL_DEGREE_POLICY` 的取值控制。

最后是客户端计时对比。它只能说明"这次执行变快了"，不能当成并行加速比的结论：

```java
public class ParallelQueryBenchmark {

    public void compareSerialVsParallel() {
        long startSerial = System.nanoTime();
        // 此处执行不带并行提示的 SQL
        long serialMs = (System.nanoTime() - startSerial) / 1_000_000;

        long startParallel = System.nanoTime();
        // 此处执行同一句 SQL，但加上 /*+ PARALLEL(t, 4) */
        long parallelMs = (System.nanoTime() - startParallel) / 1_000_000;

        System.out.printf("串行：%d ms，并行：%d ms，加速比：%.2f 倍%n",
            serialMs, parallelMs, speedup(serialMs, parallelMs));
    }

    private double speedup(long serialMs, long parallelMs) {
        return parallelMs == 0 ? 0 : (double) serialMs / parallelMs;
    }
}
```

注意：`(1 - 并行耗时 / 串行耗时) × 100` 算出的是耗时下降的百分比，不是加速倍数；加速倍数应为 `串行耗时 / 并行耗时`，上面代码已按此实现。另外，实测时应保证两次查询除提示外完全一致、数据已在缓存中、并多次执行取中位数，否则结论多半是噪声。

### 2.10 小结

并行查询的本质是"用更多进程换更短响应时间"，代价是协调开销和进程资源。要点有四条：真正的开关在数据库端（对象属性、提示、`PARALLEL_DEGREE_POLICY`）；默认并行度由 `PARALLEL_THREADS_PER_CPU × CPU_COUNT` 决定；一条语句约占 2 × DOP 个 PX 进程；验证要看执行计划和 `V$SQL_MONITOR`，而不是凭感觉。

## 三、共享池（Shared Pool）

本章讲共享池：它缓存什么、为什么能让"同一句 SQL 第二次更快"、以及 Java 应用侧怎样配合才能少做无用功。

### 3.1 是什么

**共享池（Shared Pool）**是 SGA 中的一块共享内存，用来缓存各类"程序数据"：已解析的 SQL 语句及其执行计划、PL/SQL 存储过程与函数的编译结果、数据字典信息，以及闩锁、队列等控制结构。

比喻：共享池像办公室的公共工具墙。工具挂上去一次，谁都能取用；但如果墙上挂满了一次性工具（每条 SQL 都不同），真正要用的那把就找不到了，还得重新打造——这就是"共享池碎片化"。

### 3.2 由哪些部分组成

| 组件 | 存放内容 |
| --- | --- |
| 库高速缓存（library cache） | 共享 SQL 区（语句文本 + 执行计划）、PL/SQL 单元、游标，以及保护它们的句柄与闩锁 |
| 数据字典高速缓存（dictionary cache，也称 row cache） | 表、列、索引、用户、权限等元数据 |
| 保留区（reserved area） | 为较大的连续内存请求预留的空间，减少碎片带来的失败 |
| 其他控制结构 | 锁、闩锁、并行执行消息缓冲区等 |

需要注意的是：如果未设置 `SGA_TARGET`，Oracle 还会从共享池中分配并行执行的消息缓冲区——这也是并行度开得很大时共享池压力上升的原因之一。

### 3.3 为什么需要：硬解析与软解析

解析一条 SQL 时，Oracle 会对语句文本做哈希，然后在库高速缓存里寻找"文本相同、且可以共享"的游标：

- **找到**：直接复用已有执行计划，省掉优化器的计算和大块共享内存分配，这个过程常被称为**软解析**（soft parse）。注意即便复用计划，语法与语义检查仍然要做。
- **没找到**：优化器重新生成执行计划并放入共享池，常被称为**硬解析**（hard parse），消耗 CPU 与闩锁，并发高时会成为瓶颈。

由此可以推出两个实践结论：字面量不同（`WHERE id = 1` 与 `WHERE id = 2`）会被当成两条不同的 SQL，各自硬解析；改用绑定变量后，文本一致，就能复用同一份计划。

### 3.4 怎么用：用绑定变量复用执行计划

下面的例子连续执行两次结构相同的查询，第二次通常可以直接复用第一次产生的游标：

```java
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import oracle.jdbc.pool.OracleDataSource;

public class SharedPoolDemo {

    private static final String SQL =
        "SELECT employee_id, first_name FROM employees WHERE department_id = ?";

    public void run() throws SQLException {
        OracleDataSource ods = new OracleDataSource();
        ods.setURL("jdbc:oracle:thin:@//localhost:1521/ORCLPDB1");
        ods.setUser("your_username");
        ods.setPassword("your_password");

        try (Connection conn = ods.getConnection()) {
            query(conn, 10); // 第一次执行：共享池里没有该语句，通常发生硬解析
            query(conn, 20); // 第二次执行：文本相同，通常只做软解析
        }
    }

    private void query(Connection conn, int departmentId) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement(SQL)) {
            ps.setInt(1, departmentId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    System.out.println(rs.getInt("employee_id") + " " + rs.getString("first_name"));
                }
            }
        }
    }
}
```

想确认究竟发生了硬解析还是软解析，可以结合 `V$SQL` 的 `LOADS`（游标被加载/重载的次数）、`EXECUTIONS`（执行次数）、`PARSE_CALLS`（解析调用次数）一起看：执行次数增长而加载次数不增长，说明计划被复用了。

### 3.5 关键参数

| 参数 | 作用 | 默认值（19c） | 是否可动态修改 |
| --- | --- | --- | --- |
| `SHARED_POOL_SIZE` | 共享池大小 | 设置了 `SGA_TARGET` 时为 0（内部自动决定，手工值为下限）；未设置时 32 位平台 64 MB、64 位平台 128 MB，向上取整到 granule | 可（`ALTER SYSTEM`） |
| `SHARED_POOL_RESERVED_SIZE` | 为较大连续请求预留的空间 | `SHARED_POOL_SIZE` 的 5% | 否，需写 `SPFILE` 后重启 |

```sql
-- 显式指定共享池大小（重启后生效的前提是写入了 SPFILE）
ALTER SYSTEM SET SHARED_POOL_SIZE = 1G SCOPE = SPFILE;

-- 保留区不可动态修改，必须写入 SPFILE 并重启实例
ALTER SYSTEM SET SHARED_POOL_RESERVED_SIZE = 200M SCOPE = SPFILE;
```

补充两点：在启用自动共享内存管理（设置了 `SGA_TARGET`）时，Oracle 会自行在 SGA 各组件之间调内存，此时手工设置的 `SHARED_POOL_SIZE` 被当作下限；另外 Oracle 不建议在 PDB 内设置 `SHARED_POOL_SIZE`，PDB 级别应通过 `SGA_TARGET` 控制。

### 3.6 怎么监控

```sql
-- 共享池内部各组件占用与剩余空间
SELECT name, bytes / 1024 / 1024 AS mb
FROM   v$sgastat
WHERE  pool = 'shared pool'
ORDER  BY bytes DESC;
```

```sql
-- 库高速缓存命中率，按 namespace 分组看更有意义
SELECT namespace,
       gets,
       gethits,
       ROUND(gethitratio * 100, 2) AS hit_pct,
       reloads,
       invalidations
FROM   v$librarycache
ORDER  BY gets DESC;
```

```sql
-- 数据字典缓存命中率
SELECT parameter,
       gets,
       getmisses,
       ROUND((1 - getmisses / GREATEST(gets, 1)) * 100, 2) AS hit_pct
FROM   v$rowcache
WHERE  gets > 0
ORDER  BY gets DESC;
```

| 指标 | 看什么 | 异常时的常见原因 |
| --- | --- | --- |
| 库高速缓存命中率（`gethitratio`） | 越高越好，一般应在 90% 以上 | 语句大量使用字面量、未用绑定变量 |
| `reloads` | 游标被挤出后重新加载的次数 | 共享池偏小，或一次性 SQL 太多 |
| `invalidations` | 依赖对象变更导致的失效次数 | 频繁 DDL、统计信息收集 |
| 共享池剩余空间 | 长期接近 0 需关注 | 大对象、大量硬解析、并行消息缓冲区 |

如果共享池严重不足，典型报错是 `ORA-04031`（无法分配共享内存）。排查顺序通常是：先看是否有大量未使用绑定变量的 SQL，再看是否有异常大的匿名 PL/SQL 块，最后才考虑扩容或调整保留区。

### 3.7 Java 应用侧的建议

对共享池最友好的做法是：使用连接池、坚持用 `PreparedStatement` 配合绑定变量、避免拼接 SQL 字面量、控制动态 SQL 的数量。此外，Oracle JDBC 驱动自身也提供连接缓存与语句缓存：

```java
import java.sql.Connection;
import java.sql.SQLException;
import javax.sql.DataSource;
import oracle.jdbc.pool.OracleDataSource;

public final class OracleDataSourceHolder {

    private static final DataSource DATA_SOURCE = build();

    private static DataSource build() {
        try {
            OracleDataSource ods = new OracleDataSource();
            ods.setURL("jdbc:oracle:thin:@//localhost:1521/ORCLPDB1");
            ods.setUser("your_username");
            ods.setPassword("your_password");

            // 21c 驱动：开启隐式连接缓存（即驱动内置连接池），并为每条连接缓存语句
            ods.setImplicitCachingEnabled(true);
            ods.setMaxStatements(20);
            return ods;
        } catch (SQLException e) {
            throw new IllegalStateException("初始化数据源失败", e);
        }
    }

    public static Connection getConnection() throws SQLException {
        return DATA_SOURCE.getConnection();
    }

    private OracleDataSourceHolder() {
    }
}
```

注意 API 签名：`setConnectionCacheProperties` 接收的是 `java.util.Properties`，不能传 Lambda 表达式；在 21c 的 JDBC API 参考中，连接缓存相关的入口是 `setImplicitCachingEnabled(boolean)` 与 `setMaxStatements(int)`，连接属性通过 `setConnectionProperties(Properties)` 设置。11g/12c 时代的驱动使用另一套以 `ConnectionCaching` 命名的方法，写法与新版不同，升级驱动时需要留意。

实际项目里更常见的是用 HikariCP、Druid 等成熟连接池，再在其上配置语句缓存与超时；驱动内置缓存适合轻量场景。

### 3.8 进阶了解（可跳过）

初学阶段可以略过本节。

- **保留区与碎片**：当共享池出现大量大小不一的空闲块时，大请求可能找不到连续空间。`SHARED_POOL_RESERVED_SIZE` 预留一块区域专门服务大请求，默认是共享池的 5%，上限为共享池的一半。
- **`CURSOR_SHARING`**：把字面量自动替换成系统生成的绑定变量，看似能减少硬解析，但会引入执行计划不稳定的风险（不同字面量被迫共享同一计划），不建议作为默认方案。
- **固定热点游标**：可以用 `DBMS_SHARED_POOL.KEEP` 把核心 SQL 的游标固定在共享池中，避免被挤出后重新硬解析；`V$SQL.KEPT_VERSIONS` 可用来确认是否已固定。

### 3.9 小结

共享池解决的是"重复劳动"问题：解析结果集中缓存、所有会话复用。用好它只需记住三件事——用绑定变量让语句文本稳定、用连接池和语句缓存减少重复解析、用 `V$LIBRARYCACHE` 与 `V$SGASTAT` 观察而不是凭感觉调参。

## 四、在 Java 中处理 REF CURSOR

本章讲一个具体的接口问题：存储过程要返回"多行结果集"时，数据库端用 REF CURSOR 输出，Java 端怎样正确接收并释放资源。

### 4.1 是什么

**REF CURSOR** 是 PL/SQL 的游标变量（cursor variable）：它不像普通游标那样绑定死一条查询，而是一个**指向查询结果集工作区的指针**，可以先打开查询 A、再打开查询 B。`SYS_REFCURSOR` 是 Oracle 预定义的**弱类型** REF CURSOR 类型，可以关联任意查询，也是存储过程返回结果集时最常用的写法。

比喻：REF CURSOR 像餐厅的取餐号牌。号牌本身不是饭菜，它指向柜台里属于你的那一份；饭菜什么时候取、取完要交回号牌，都有规矩——对应到代码里，就是"必须关闭结果集"。

### 4.2 为什么需要

存储过程和函数默认只能返回标量值或集合类型。当需要把"某个部门的员工列表"这类多行结果直接交给 Java 处理时，用 REF CURSOR 输出参数是最直接的方式：数据库端只负责打开游标，行数据由客户端按需拉取，不必一次性在内存里拼装。

### 4.3 数据库端：打开游标并输出

```sql
CREATE OR REPLACE PROCEDURE get_employees_by_dept (
    p_dept_id IN  NUMBER,
    p_emp_cur OUT SYS_REFCURSOR
) AS
BEGIN
    OPEN p_emp_cur FOR
        SELECT employee_id, first_name, last_name, salary
        FROM   employees
        WHERE  department_id = p_dept_id;
END;
/
```

### 4.4 Java 端：注册、调用、取数、关闭

```java
import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import oracle.jdbc.OracleTypes;

public class RefCursorExample {

    /**
     * 调用存储过程并遍历返回的结果集。
     * 连接由调用方创建与关闭，避免在方法内部制造连接泄漏。
     */
    public void printEmployees(Connection conn, int departmentId) throws SQLException {
        String call = "{call get_employees_by_dept(?, ?)}";

        try (CallableStatement cs = conn.prepareCall(call)) {
            cs.setInt(1, departmentId);              // 输入参数
            cs.registerOutParameter(2, OracleTypes.CURSOR); // 输出参数：REF CURSOR
            cs.execute();

            // Oracle 驱动把 REF CURSOR 输出参数映射成 java.sql.ResultSet
            try (ResultSet rs = (ResultSet) cs.getObject(2)) {
                if (rs == null) {
                    return; // 游标未打开时可能为 null
                }
                while (rs.next()) {
                    System.out.printf("员工 %d：%s %s，薪资 %.2f%n",
                        rs.getInt("employee_id"),
                        rs.getString("first_name"),
                        rs.getString("last_name"),
                        rs.getDouble("salary"));
                }
            }
        }
    }
}
```

### 4.5 关键步骤对照

| 步骤 | 代码 | 说明 |
| --- | --- | --- |
| 准备调用 | `conn.prepareCall("{call proc(?, ?)}")` | `{call ...}` 是 JDBC 标准的存储过程调用转义语法 |
| 绑定输入参数 | `cs.setInt(1, departmentId)` | 位置从 1 开始，与存储过程参数顺序一致 |
| 注册输出参数 | `cs.registerOutParameter(2, OracleTypes.CURSOR)` | `OracleTypes.CURSOR` 是 Oracle 驱动定义的类型码，标准 JDBC 的通用类型常量里没有它，注册 REF CURSOR 输出参数时用它 |
| 执行 | `cs.execute()` | 有输出参数时用 `execute()`，不要用 `executeQuery()` |
| 取结果集 | `(ResultSet) cs.getObject(2)` | 驱动返回的是结果集对象，需要强转 |
| 关闭 | 依次关闭 `ResultSet`、`CallableStatement`、`Connection` | 用 try-with-resources 保证顺序与异常安全 |

### 4.6 常见坑

1. **忘记关闭返回的 `ResultSet`**。它对应数据库端的游标，不关会持续占用会话的打开游标数（受 `OPEN_CURSORS` 限制），高并发下表现为"游标数耗尽"。
2. **用 `executeQuery()` 调用带输出参数的过程**。`executeQuery()` 期望返回一个结果集，与 REF CURSOR 输出参数的用法不匹配。
3. **把 `getObject(2)` 的结果当成 `ResultSet` 以外的东西**。部分旧代码会先强转成驱动私有类型，跨驱动版本升级时容易失败。
4. **在方法内部创建连接却不关闭**。示例中把 `Connection` 作为参数传入、由调用方用 try-with-resources 管理，就是为了避免这一点。
5. **对返回结果做二次排序或分页**。REF CURSOR 已经把结果集定型，排序、过滤应在 SQL 中完成。

### 4.7 Maven 依赖

```xml
<dependency>
  <groupId>com.oracle.database.jdbc</groupId>
  <artifactId>ojdbc8</artifactId>
  <version>12.2.0.1</version>
</dependency>
```

说明：`com.oracle.database.jdbc:ojdbc8` 在 Maven 中央仓库确实提供 12.2.0.1 版本，该坐标可用。不过该版本年代较久，选择时建议注意三点：`ojdbc8` 面向 JDK 8，JDK 11 及以上通常选用 `ojdbc11`；驱动版本不必与数据库版本完全一致，但应选择仍在维护的补丁版本；同一项目内不要混用多个 Oracle 驱动版本。该坐标下目前已发布到 23.x 系列，具体选哪个版本应以官方兼容性说明和项目 JDK 版本为准。

### 4.8 小结

REF CURSOR 的处理只涉及四步：存储过程用 `SYS_REFCURSOR` 输出参数打开游标、Java 端用 `OracleTypes.CURSOR` 注册、`getObject` 拿到 `ResultSet`、用完按顺序关闭。真正容易出问题的地方不在语法，而在资源释放和连接归属。

## 五、参考资料

以下资料均为 Oracle 官方文档，按主题列出，便于逐条核对本文的参数默认值与语法：

- Oracle Database SQL Language Reference 19c，CREATE TABLE 章节中的 parallel_clause 语法。
- Oracle Database Reference 19c，初始化参数条目：PARALLEL_DEGREE_POLICY、PARALLEL_THREADS_PER_CPU、PARALLEL_DEGREE_LIMIT、PARALLEL_MIN_TIME_THRESHOLD、PARALLEL_MAX_SERVERS、PARALLEL_MIN_SERVERS、PARALLEL_ADAPTIVE_MULTI_USER、SHARED_POOL_SIZE、SHARED_POOL_RESERVED_SIZE。
- Oracle Database Reference 19c，动态性能视图条目：V$SQL、V$SQL_MONITOR、V$LIBRARYCACHE、V$SGASTAT。
- Oracle Database VLDB and Partitioning Guide 19c，Parallel Execution Concepts 与 Setting the Degree of Parallelism 两节。
- Oracle Database Concepts 19c，Memory Architecture 章节（SGA、PGA、共享池）。
- Oracle Database PL/SQL Language Reference 19c，Cursor Variables 一节（SYS_REFCURSOR 与弱类型游标变量）。
- Oracle Database JDBC Java API Reference 21c，OracleDataSource 与 OracleTypes 类。
- Maven 中央仓库 com.oracle.database.jdbc:ojdbc8 的版本清单（用于确认 12.2.0.1 存在及当前版本范围）。

关于无法核实的定量结论，本文的处理方式是：不采用"并行度为 CPU 核数 2~4 倍"这类无官方依据的倍数规则，改为按官方默认并行度公式并结合观测确定；客户端计时示例不宣称具体加速倍数；共享池命中率给出的是"通常应在 90% 以上"这类经验性参考，而非官方硬性指标。
