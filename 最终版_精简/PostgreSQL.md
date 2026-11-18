# PostgreSQL 核心机制与调优实践

本文面向工作一年左右的 Java 开发者：能熟练用 JDBC、MyBatis 或 JPA 写增删改查，但对数据库内部"为什么这样设计"还比较陌生。全文围绕六个主题展开：WAL 预写日志、事务隔离级别、索引类型、MVCC（多版本并发控制）、慢查询优化、JSON 与 JSONB。

文中涉及的行为、默认值与版本差异，均以 PostgreSQL 官方文档为准；标注了适用版本的地方，请对照项目实际使用的版本阅读——不同大版本之间，默认值和行为可能不同。

## 本文导读

- 第一章 WAL（预写日志）机制：数据库凭什么在断电后还能恢复
- 第二章 事务隔离级别：多个事务同时改数据时，"谁看得见谁"
- 第三章 索引类型：B-Tree、Hash、GiST、SP-GiST、GIN、BRIN 怎么选
- 第四章 MVCC：一行数据为什么会有多个版本，以及 VACUUM 为什么重要
- 第五章 慢查询诊断与优化：从抓到慢 SQL 到调参的完整流程
- 第六章 JSON 与 JSONB：半结构化数据怎么存、怎么查
- 第七章 参数与版本差异速查：常用默认值、易错点与参考资料

## 一、WAL（预写日志）机制

WAL 是 PostgreSQL 保证"数据不丢"和"事务要么全做、要么全不做"的核心机制。理解它之后，很多现象就解释得通了：为什么提交频繁时瓶颈常常在磁盘、为什么崩溃后数据库能自己恢复到一致状态、为什么备库只要重放日志就能和主库保持一致。

### 1.1 是什么：先记账，后改账

可以把它想成记账：先在流水账上写下"某账户要减少 100 元"，再去改余额。万一改到一半停电，照着流水账把没做完的步骤重做一遍，账就平了。

WAL 的核心思想只有一句话：**在对数据文件做任何修改之前，必须先把这次修改对应的日志写入持久存储**。

关键特征：

- 先写日志，后修改数据文件
- 记录所有数据库状态变更（不只行数据，索引、系统表也在内）
- 提供崩溃恢复能力
- 支撑事务的原子性与一致性

### 1.2 为什么需要 WAL

数据库的数据文件按"页"（page，默认 8KB 一块）组织，一次事务可能同时改好几个页、好几个索引。如果直接把页写回磁盘，会碰到两个问题：

- **写一半崩溃**：一页只写了一半就断电，磁盘上留下"半新半旧"的页，数据无法解释。
- **无法撤销**：事务执行到一半失败时，已经落盘的部分没有依据回滚。

WAL 把"随机写数据页"变成"顺序写日志 + 延迟写数据页"，顺序写快得多，而且日志里记着完整的变更，重放即可重做、不回放即视为未发生。

MySQL 的 InnoDB 引擎也有同样思路的 redo log；区别在于 PostgreSQL 的 WAL 还兼作流复制和按时间点恢复（PITR）的数据源。

### 1.3 工作流程

```text
客户端请求 -> 事务开始 -> 记录 WAL 日志 -> 修改内存中的数据页
        -> 事务提交时刷 WAL（synchronous_commit = on 时）
        -> 后台进程周期性把脏页刷回磁盘 -> 检查点推进
```

需要注意：提交时落盘的是 **WAL**，不是数据页。数据页可以晚一点再写，只要日志已经在磁盘上，崩溃后就能靠日志把数据页补齐。

### 1.4 WAL 记录长什么样

下面是 WAL 记录字段的**伪代码示意**，用于帮助理解结构，并非 PostgreSQL 真实的二进制格式（真实格式由 `pg_waldump` 等工具解析）。

```sql
-- WAL 日志记录的结构示意（伪代码）
RECORD {
    transaction_id: 唯一事务标识,
    log_sequence_number: 日志序列号（LSN，日志文件中的位置）,
    operation_type: 操作类型（INSERT/UPDATE/DELETE）,
    table_id: 表标识,
    old_value: 变更前数据,
    new_value: 变更后数据,
    timestamp: 操作时间戳
}
```

其中 LSN（Log Sequence Number）是日志的"页码"，崩溃恢复就是从这个位置往后重放。

### 1.5 关键配置参数

```sql
-- 设置 WAL 相关配置（需超级用户；wal_level 只能重启生效，其余参数 pg_reload_conf() 即可）
ALTER SYSTEM SET wal_level = replica;        -- WAL 详细级别
ALTER SYSTEM SET max_wal_size = '1GB';       -- WAL 体积的软上限
ALTER SYSTEM SET checkpoint_timeout = '15min'; -- 两次自动检查点之间的最长间隔
```

| 参数 | 作用 | 官方默认值 | 备注 |
| --- | --- | --- | --- |
| `wal_level` | 决定 WAL 记录多少信息 | `replica` | `minimal` 最省，但不能做归档/流复制；`logical` 支持逻辑复制。只能在启动时设置 |
| `max_wal_size` | 自动检查点之间允许 WAL 增长的上限 | `1GB` | 软上限，高负载或归档失败时可能被突破 |
| `min_wal_size` | WAL 文件回收的下限 | `80MB` | 低于此值只回收不删除 |
| `checkpoint_timeout` | 两次自动检查点之间的最长间隔 | `5min`（可设 30 秒 ~ 1 天） | 调大可减少检查点频率，但崩溃恢复时间变长 |

> 版本提示：很多旧资料把 `checkpoint_timeout` 的默认值写成 15 分钟，这与官方文档不符——默认值是 **5 分钟**。示例里把它调到 `15min` 是一种常见做法，但那是"修改后的值"，不是默认值。

实际修改参数有两种写法，效果等价：

```sql
-- 方式一：写入配置文件，再重新加载
ALTER SYSTEM SET checkpoint_timeout = '15min';
SELECT pg_reload_conf();

-- 方式二：只影响当前会话，用于临时验证
SET checkpoint_timeout = '15min';
```

### 1.6 崩溃恢复过程

数据库重启时会读取最近一次检查点（checkpoint）的位置，从这里往后重放 WAL：

1. 从最近一次成功的检查点开始，确定重放起点
2. 顺序重放 WAL 中记录的变更（redo），把数据页恢复到崩溃前一刻的状态
3. 已提交事务的效果随之恢复；未提交事务不会被当作有效数据
4. 未提交事务残留在数据页上的行版本会被标记为无效，随后由 VACUUM 清理

> 常见误解：PostgreSQL **没有独立的 undo 阶段**。它只做 redo，未提交事务靠"事务状态"判断不可见，而不是靠回滚日志把数据改回去。这也是 PostgreSQL 必须依赖 VACUUM 清理旧版本的根本原因（见 4.8 节）。

### 1.7 性能优化策略

- **批量写入日志**：一次事务里合并多条变更，减少提交次数
- **异步提交**：`synchronous_commit = off` 时提交不等待 WAL 落盘，吞吐提升明显，但极端故障下可能丢失"最近已提交"的少量事务（数据仍然一致，不会损坏）
- **调整检查点频率**：`checkpoint_timeout` 与 `max_wal_size` 配合，避免检查点过于密集造成 I/O 抖动
- **使用更快的存储介质**：WAL 是顺序写，SSD 或独立盘位能显著降低提交延迟

> 关于 `fsync`：生产环境不要关闭。关闭后一旦断电，可能造成无法恢复的数据损坏，而不只是丢几条事务。

### 1.8 Java 模拟 WAL 事务示例

下面用 Java 简化演示"先写日志、提交时落盘"的思路（仅用于理解流程，不涉及真实磁盘协议）：

```java
import java.util.ArrayList;
import java.util.List;

public class WalSimulator {

    // 内存中的日志缓冲，真实实现会写入 WAL 段文件
    private final List<LogEntry> walLog = new ArrayList<>();

    public void beginTransaction() {
        // 开始事务：记录事务号与时间戳
        LogEntry logEntry = new LogEntry();
        logEntry.setTransactionId(generateUniqueId());
        logEntry.setTimestamp(System.currentTimeMillis());
    }

    public void logOperation(String operationType, Object oldValue, Object newValue) {
        // 修改数据前，先记录变更日志
        LogEntry entry = new LogEntry();
        entry.setOperationType(operationType);
        entry.setOldValue(oldValue);
        entry.setNewValue(newValue);
        walLog.add(entry);
    }

    public void commitTransaction() {
        // 提交：把日志刷到持久存储，返回成功即代表可恢复
        persistWalLog();
    }

    private void persistWalLog() {
        for (LogEntry entry : walLog) {
            // 真实实现写入 WAL 段文件并调用 fsync
            writeToStorage(entry);
        }
    }

    private void writeToStorage(LogEntry entry) {
        // 省略具体 I/O 实现
    }

    private long generateUniqueId() {
        return System.nanoTime();
    }
}
```

### 1.9 优势与适用场景

- **优势**：数据持久性保证、事务原子性、崩溃恢复、性能可控、支持并发事务。
- **持久性保证**：在突然断电、操作系统崩溃、硬件故障、进程被意外终止等情况下，已提交的数据都能恢复（前提是 `fsync` 未被关闭、存储本身没有谎报刷盘）。
- **适用场景**：高可靠性系统、金融交易、需要精确恢复到某个时间点的应用、大规模在线事务处理系统。

一句话总结：WAL 用"顺序写日志"换来了可靠性和写入性能，是 PostgreSQL 故障保护的地基。

### 1.10 进阶了解（可跳过）：检查点、复制与 wal_level

初学可略过本节，等需要做高可用或调优时再回来看。

- **检查点（checkpoint）**：把内存中的脏页刷回磁盘，并记录一个"从这里开始重放即可"的位置。检查点越稀疏，写入越平顺，但崩溃恢复越慢。
- **物理流复制**：主库持续把 WAL 发给备库，备库不断重放，因此备库数据与主库一致。`wal_level = replica`（默认值）就足够支撑归档与流复制。
- **逻辑复制**：需要 `wal_level = logical`，它比 `replica` 多记录解码所需的信息，WAL 体积会变大；逻辑复制按行/表级别传输变更，可跨大版本、可只同步部分表。
- **归档与时间点恢复（PITR）**：把历史 WAL 段保存到外部存储，配合基础备份，就能恢复到"某一时刻"。

## 二、事务隔离级别

隔离级别（isolation level）回答的是：多个事务同时读写同一批数据时，一个事务能看到另一个事务的哪些中间状态。级别越高越安全，但并发能力越弱。它本质上是一份"并发行为合同"，数据库按合同决定读到的数据长什么样。

生活化比喻：几个人同时编辑同一份在线文档。有人希望"只看自己打开文档那一刻的版本"，有人希望"随时看到别人刚保存的内容"，隔离级别就是这份约定。

### 2.1 三种常见的并发异常

| 并发异常 | 描述 | 生活化解释 |
| --- | --- | --- |
| 脏读（dirty read） | 读到了另一个事务尚未提交的数据 | 看到了别人还没点"保存"的草稿 |
| 不可重复读（nonrepeatable read） | 同一事务内两次读同一行，结果不同 | 读完一遍再读，数字被人改了 |
| 幻读（phantom read） | 同一事务内两次执行同一条件查询，返回的行集合变了 | 名单里凭空多出/少了一行 |
| 序列化异常（serialization anomaly） | 多个事务并发提交的结果，与任何一种串行执行的结果都不一致 | 各自都对，合起来账不平 |

### 2.2 四种隔离级别的实际行为

PostgreSQL 名义上支持四种标准隔离级别，但**内部只实现三种**：请求"读未提交"时会自动按"读已提交"处理。官方文档给出的实际行为如下：

| 隔离级别 | 脏读 | 不可重复读 | 幻读 | 序列化异常 |
| --- | --- | --- | --- | --- |
| 读未提交（Read Uncommitted） | 不允许（等同读已提交） | 可能 | 可能 | 可能 |
| 读已提交（Read Committed，默认） | 不允许 | 可能 | 可能 | 可能 |
| 可重复读（Repeatable Read） | 不允许 | 不允许 | **不允许** | 可能 |
| 串行化（Serializable） | 不允许 | 不允许 | 不允许 | 不允许 |

下面逐个说明。

### 2.3 读未提交（Read Uncommitted）

```sql
-- 设置隔离级别为读未提交
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

-- 特征
-- 1. 标准中允许脏读
-- 2. 一致性最低、理论上开销最小
-- 3. PostgreSQL 内部按"读已提交"执行，因此实际不会出现脏读
```

因为 PostgreSQL 的 MVCC 实现里没有"读别人未提交数据"这条路径，所以这个级别在 PostgreSQL 中与读已提交完全等价。想靠它"再快一点"是没有收益的。

### 2.4 读已提交（Read Committed，默认级别）

```sql
-- PostgreSQL 的默认隔离级别
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- 特征
-- 1. 只能读到已提交的数据，不会脏读
-- 2. 每条语句开始时取一个新快照（语句级快照）
-- 3. 同一事务内两条 SELECT 之间，别人提交的修改可见，所以可能出现不可重复读与幻读
-- 4. 对同一行的并发更新会互相等待，拿到锁后重新判断条件再改
```

这是绝大多数应用的默认选择，简单、并发好。代价是"同一事务内多次读到的数据可能不一致"，涉及复杂判断的业务（例如先查余额再扣款）需要显式加锁或提高隔离级别。

### 2.5 可重复读（Repeatable Read）

```sql
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- 特征
-- 1. 事务内第一次执行语句时取快照，整个事务都用这个快照
-- 2. 同一事务内两次查询结果一致，不会不可重复读
-- 3. PostgreSQL 的实现（快照隔离）也不会出现幻读，比 SQL 标准要求更严格
-- 4. 若试图修改"事务开始后被别人改过"的行，会报错并需要重试
```

> 版本/实现提示：SQL 标准允许"可重复读"出现幻读，但 PostgreSQL 的实现（快照隔离，Snapshot Isolation）从根上避免了幻读。所以"可重复读可能幻读"这句结论对 MySQL 的某些实现成立，对 PostgreSQL **不成立**，不要混用。

这类事务失败时收到的是：

```text
ERROR:  could not serialize access due to concurrent update
```

处理方式是**整个事务回滚并重试**。应用层要为此准备重试逻辑（通常重试 2~3 次）。

### 2.6 串行化（Serializable）

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- 特征
-- 1. 并发执行的多个事务，效果等价于某种串行顺序执行
-- 2. 在可重复读的基础上，额外监视"读写依赖"，用谓词锁（predicate lock）发现潜在冲突
-- 3. 谓词锁本身不阻塞读写，但发现冲突会让其中一个事务失败：could not serialize access
-- 4. 一致性最强，重试成本也最高
```

要点：串行化不是"变慢的锁"，而是"事后校验 + 让冲突事务重试"。所以应用必须能处理 SQLSTATE `40001`（序列化失败）。

### 2.7 Java 中设置与重试

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class TransactionIsolationDemo {

    private Connection getConnection() throws SQLException {
        // 示例连接串，实际项目使用连接池
        return DriverManager.getConnection("jdbc:postgresql://localhost:5432/mydb");
    }

    public void demonstrateIsolation() throws SQLException {
        try (Connection conn = getConnection()) {
            // 串行化事务容易被中止，必须关闭自动提交并显式控制边界
            conn.setAutoCommit(false);
            conn.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);

            try {
                performTransactionalWork(conn);
                conn.commit();
            } catch (SQLException e) {
                conn.rollback();
                // 40001 = 序列化失败，可重试；其他错误直接抛出
                throw e;
            }
        }
    }

    private void performTransactionalWork(Connection conn) throws SQLException {
        // 具体业务 SQL
    }
}
```

### 2.8 隔离级别怎么选

| 隔离级别 | 推荐场景 | 说明 |
| --- | --- | --- |
| 读已提交 | 默认场景、绝大多数 CRUD 业务 | 并发好，成本低 |
| 可重复读 | 一个事务内要多次读同一批数据并做判断 | 不会幻读，冲突时需重试 |
| 串行化 | 强一致性要求极高、逻辑复杂难以加锁 | 冲突事务会被中止，必须实现重试 |

按业务粗略划分：金融核心账务倾向串行化或"读已提交 + 显式行锁"；普通业务用读已提交；报表/分析类长查询可用可重复读获得稳定快照。

> 与 MySQL 的差异：MySQL InnoDB 的默认隔离级别是 REPEATABLE READ，而 PostgreSQL 默认是 READ COMMITTED。从 MySQL 迁过来时，不要假设"默认就是可重复读"。

### 2.9 实际配置示例

```sql
-- 会话级：当前连接后续事务的默认隔离级别
SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- 单个事务级：只影响这一次事务
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- ... 业务 SQL ...
COMMIT;

-- 数据库级默认值（需管理员）
ALTER DATABASE mydb SET default_transaction_isolation = 'repeatable read';
```

### 2.10 性能与一致性权衡

```text
隔离级别：低开销、弱一致  <---------------->  高开销、强一致
          读未提交 -> 读已提交 -> 可重复读 -> 串行化
          （PG 中等同读已提交）
```

隔离级别越高，冲突检测与重试成本越大，但换来的是更强的一致性。PostgreSQL 主要通过 **MVCC**、快照隔离与锁机制实现隔离：读已提交用语句级快照，可重复读用事务级快照，串行化再加谓词锁校验。

**最佳实践：**

- 显式声明隔离级别，不要依赖"默认值恰好合适"
- 事务尽量短，避免"开着事务等用户输入"
- 配合合适的索引，减少扫描行数（扫描行越多，冲突概率越高）
- 串行化事务必须实现重试，并区分可重试错误与业务错误

## 三、索引类型与适用场景

索引（index）是数据库为了"少读几页数据"而额外维护的数据结构，代价是占用空间、拖慢写入。选择索引类型的关键，是先看清查询长什么样：等值、范围、包含、相似、还是"只关心大范围的时间段"。

### 3.1 基本概念

索引类似书籍的目录：想找某一章，不必从第一页翻起。

基本原理：

- 为数据建立一条快速查找路径
- 减少全表扫描（Seq Scan）
- 以空间换时间

> 与 MySQL 的差异：PostgreSQL 的表是"堆表"，所有索引里存的是行在数据页中的位置，查到索引后还要"回表"取整行；InnoDB 的主键索引本身即数据（聚簇索引）。

### 3.2 B-Tree 索引（默认、最常用）

```sql
-- 创建 B-Tree 索引
CREATE INDEX idx_users_username ON users (username);

-- 复合 B-Tree 索引
CREATE INDEX idx_users_name_email ON users (last_name, first_name);
```

特征：支持等值与范围（`=`、`<`、`>`、`BETWEEN`、`IN`、`IS NULL`）；支持按索引顺序取数据（可省掉排序）；`LIKE 'abc%'` 这种"前缀固定"的匹配也可能用到（非 C 排序规则时通常需要专门的 operator class）；是 `CREATE INDEX` 的默认类型。

### 3.3 Hash 索引

```sql
-- 创建 Hash 索引
CREATE INDEX idx_users_email_hash ON users USING HASH (email);
```

特征：只支持 `=` 等值比较，不支持范围查询；索引同样存储在磁盘上，并非"内存结构"；由于只能等值匹配，适用面比 B-Tree 窄，通常只在超长文本等值匹配且 B-Tree 索引过大时才有意义。

> 版本提示：PostgreSQL 9.6 及更早版本的 Hash 索引不写 WAL，崩溃后可能需要 `REINDEX` 重建，且变更不会随流复制同步，官方当时明确"不建议使用"。较新版本中该限制已取消，但仍建议先用 B-Tree 验证是否真的需要 Hash。使用前请查阅部署版本的文档。

### 3.4 GiST（广义搜索树）索引

```sql
-- 创建地理空间索引（需要 PostGIS 等扩展提供操作符类）
CREATE INDEX idx_locations_point ON locations USING GIST (location);
```

应用：地理空间数据、全文检索、相似性搜索、复杂数据类型。GiST 本身是一套"索引框架"，具体支持哪些操作符取决于所选的操作符类（operator class）；内置支持的有几何类型，还可以做"最近邻"查询（例如按距离排序取前 10 个点）。

### 3.5 SP-GiST（空间分区广义搜索树）索引

```sql
-- 创建 SP-GiST 索引
CREATE INDEX idx_points ON points USING SPGIST (location);
```

特点：面向非平衡的树形结构（四叉树、k-d 树、基数树等）；适合有明显分区特征的数据；同样支持最近邻搜索；也依赖操作符类决定可用操作符。

### 3.6 GIN（倒排索引）

```sql
-- 全文检索：对表达式建索引
CREATE INDEX idx_articles_text ON articles USING GIN (to_tsvector('english', content));

-- 数组 / JSONB 的包含查询
CREATE INDEX idx_profiles_gin ON user_profiles_jsonb USING GIN (profile);
```

特征：倒排结构，为每个"分量值"建一条索引项，因此特别适合"一个字段里含多个值"的场景——数组、`jsonb`、全文检索词元；高效支持包含（`@>`）、存在（`?`）等查询；写入成本高于 B-Tree（一次写入要更新多个索引项），适合读多写少的检索场景。

### 3.7 BRIN（块范围索引）

```sql
-- 超大表上的时间列
CREATE INDEX idx_large_table_date ON large_table USING BRIN (created_at);
```

特点：不为每行建索引项，而是为"连续的一段数据块"记录摘要（如最小值/最大值），索引极小；只有当列值与物理存储顺序强相关时才有效（典型是自增 ID、写入时间）；精度是"块范围"级别，扫到候选块后仍需逐行过滤——用近似的精度换极小的体积。

> 补充：数据量特别大时，还可以配合声明式分区（`CREATE TABLE ... PARTITION BY RANGE (created_at)`）让查询只扫描相关分区。注意 PostgreSQL 的 autovacuum 不会对分区父表执行 `ANALYZE`，父表统计信息需要手动维护。

### 3.8 Java 持久层里怎么定义索引

JPA 的 `@Index` 要写在 `@Table` 的 `indexes` 属性里，不能直接标在字段上（标在字段上是无效的写法）：

```java
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;

@Entity
@Table(
    name = "users",
    indexes = @Index(name = "idx_users_username", columnList = "username")
)
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "username")
    private String username;

    // 全文检索列：类型为 tsvector，通常配合 GIN 索引
    @Column(columnDefinition = "tsvector")
    private String searchVector;
}
```

需要注意：JPA 不能直接把 `String` 字段映射成 `tsvector`，上面的写法只表达"这一列存的是检索向量"；真实项目通常用原生 SQL、`@Column(insertable = false, updatable = false)` 配合数据库触发器，或引入 Hibernate 的自定义类型来处理。

实际项目中索引多由迁移脚本（Flyway / Liquibase）管理，注解只用于本地开发或自动建表。

### 3.9 索引选择指南

| 索引类型 | 适用场景 | 查询类型 | 主要代价 |
| --- | --- | --- | --- |
| B-Tree | 大多数场景 | 等值、范围、排序 | 通用、平衡，写入开销中等 |
| Hash | 仅等值匹配 | 精确匹配 | 适用面窄，不支持范围 |
| GiST | 几何、全文、相似性 | 包含、距离排序 | 依赖操作符类，专业度高 |
| SP-GiST | 分区特征明显的数据 | 空间分区、最近邻 | 场景专一 |
| GIN | 数组、JSONB、全文检索 | 包含、存在 | 索引大、写入慢 |
| BRIN | 超大表、时间序列 | 范围 | 精度低，依赖物理相关性 |

### 3.10 索引维护与优化建议

```sql
-- 看执行计划：是否真的走了索引
EXPLAIN ANALYZE SELECT * FROM users WHERE username = 'user_a';

-- 查看索引大小
SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE relname = 'users';

-- 重建索引（会阻塞写入；在线重建用 REINDEX INDEX CONCURRENTLY）
REINDEX INDEX idx_users_username;
```

**性能与最佳实践：**

- 索引会增加写入开销，索引过多会拖慢 `INSERT/UPDATE/DELETE`，要平衡读写
- 不是所有列都需要索引；复合索引要注意字段顺序（最左前缀）
- 选择索引前先分析查询模式与数据分布，并用 `EXPLAIN` 验证
- 定期 `ANALYZE` 更新统计信息；长期不用的索引及时清理
- 建大索引时用 `CREATE INDEX CONCURRENTLY`，避免长时间锁表

## 四、MVCC（多版本并发控制）

MVCC 是 PostgreSQL 并发能力的来源：读操作看不到别人未提交的修改，也不需要等写操作结束。理解它的关键是接受一件事——**表里的"一行"其实可能有多个版本同时存在**。

生活化比喻：像文档的"历史版本"功能。每个人打开文档时看到的是自己打开那一刻的版本，别人后续的修改会生成新版本，不会把你正在看的内容改掉。

### 4.1 是什么

**定义：** 多版本并发控制（Multi-Version Concurrency Control，MVCC）是一种并发访问技术：每次修改产生一个新版本，读操作按自己的快照选择"该看哪个版本"，从而避免读写互相阻塞。

核心思想：

- 每个事务看到的是数据在某个时间点的一致视图
- 读不阻塞写，写不阻塞读
- 旧版本不会立刻删除，等没人需要它了再清理

### 4.2 为什么需要它

如果只有锁，读和写就要排队：一个长查询会把同表的写入全部堵住，反之亦然。MVCC 用"多版本 + 快照"把读写解耦，代价是存储膨胀和清理成本——这部分成本由 VACUUM 承担。

> 与 MySQL 的差异：InnoDB 把旧版本放在 undo 日志里，由后台 purge 清理；PostgreSQL 把旧版本**留在表的数据页里**，由 VACUUM 清理。所以 PostgreSQL 对"表和索引膨胀"更敏感，autovacuum 的配置也更值得关注。

### 4.3 版本信息存在哪里

每行都有几个系统列（system column），普通 `SELECT *` 看不到，但可以直接查询：

```sql
-- 建表（业务列）
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    created_at TIMESTAMP
);

-- 系统列（由数据库维护，不需要也不能手工创建）
-- xmin：创建该行版本的事务 ID
-- xmax：删除/更新该行版本的事务 ID（0 表示尚未被删除）
-- cmin / cmax：同一事务内的命令序号，用于区分语句顺序

-- 观察一下：xmin 就是插入这行的事务号
SELECT id, username, xmin, xmax FROM users;
```

### 4.4 事务快照

事务开始时（读已提交是每条语句开始时），数据库会记录"当前哪些事务还活着"，形成快照（snapshot）。判断一行是否可见，本质就是拿这行的 `xmin/xmax` 和快照比对。

```sql
-- 快照相关函数：查看当前快照与事务号
SELECT txid_current(), pg_current_snapshot();
```

### 4.5 插入、更新、删除分别发生了什么

**插入：**

```sql
INSERT INTO users (username) VALUES ('user_a');
-- 新行的 xmin = 当前事务 ID，xmax = 0
```

**更新：**

```sql
UPDATE users SET username = 'user_b' WHERE id = 1;

-- 实际发生的事：
-- 1. 复制出一行新版本，写入新值，xmin = 当前事务 ID
-- 2. 旧版本的 xmax 被标记为当前事务 ID（表示"被这个事务取代"）
-- 3. 索引项指向新版本（可能新增索引项，旧项成为"死项"）
```

> 删除只是把目标行的 `xmax` 设为当前事务 ID，并不立即物理删除；真正的空间回收要等 VACUUM。

也就是说：**一次 UPDATE = 一次插入 + 一次逻辑删除**。这解释了为什么频繁更新的表会膨胀。

### 4.6 可见性判断（简化版）

```sql
-- 可见性判断伪代码（真实实现更复杂，还涉及命令 ID、子事务、冻结等）
FUNCTION is_visible(row_version, snapshot):
    IF row_version.xmin == current_transaction:
        RETURN true                      -- 本事务自己插入的，可见
    IF row_version.xmin 在快照中已提交
       AND (row_version.xmax == 0 OR row_version.xmax 未提交):
        RETURN true                      -- 别人早于我提交，且没被有效删除
    RETURN false                         -- 其余情况（未提交、已删除、未来事务）不可见
```

### 4.7 Java 侧的并发控制

JPA 的 `@Version` 是**应用层乐观锁**，靠版本号比较实现"后写不覆盖先写"；它和数据库内部的 MVCC 不是同一件事，但目标一致：避免并发更新互相覆盖。两者可以配合使用。

```java
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "username")
    private String username;

    // 乐观锁版本号：每次更新自动 +1，冲突时抛 OptimisticLockException
    @Version
    private Long version;
}
```

```java
import org.springframework.transaction.annotation.Transactional;

@Transactional
public User updateUser(Long userId, String newUsername) {
    User user = userRepository.findById(userId)
        .orElseThrow(() -> new IllegalStateException("user not found"));

    user.setUsername(newUsername);
    // 提交时：UPDATE ... WHERE id = ? AND version = ?，由数据库的 MVCC 保证行级并发安全
    return userRepository.save(user);
}
```

### 4.8 垃圾回收：VACUUM 与 autovacuum

旧版本行不会再被任何事务看到之后，就变成"死元组"（dead tuple），需要清理。

```sql
-- 清理死元组，把空间标记为可复用（不阻塞读写）
VACUUM users;

-- 重写整张表，真正把空间还给操作系统（会锁表，慎用）
VACUUM FULL users;

-- 更新统计信息，让优化器选到更好的执行计划
ANALYZE users;
```

三者的区别与代价：

| 操作 | 做了什么 | 是否把空间还给操作系统 | 锁与影响 |
| --- | --- | --- | --- |
| `VACUUM` | 清理死元组、更新可见性映射、可顺带冻结旧事务号 | 一般不会（仅表尾整页空闲且能快速拿到排他锁时例外） | 与读写基本可并行，但会占用 I/O |
| `VACUUM FULL` | 重写整表文件，彻底压实 | 会 | 需要 `ACCESS EXCLUSIVE` 锁，期间表不可读写，还需要额外磁盘空间 |
| `ANALYZE` | 采样统计信息 | 无关 | 很轻量，可与业务并行 |

**autovacuum**：PostgreSQL 默认开启自动清理，由一个 launcher 进程按 `autovacuum_naptime`（默认 1 分钟）拉起多个 worker，逐个库检查。触发条件是"死元组数超过阈值"，阈值按"基础阈值 + 比例 × 表行数"计算，可用表级存储参数单独覆盖。autovacuum 永远不会执行 `VACUUM FULL`。

实践要点：

- 不要关闭 autovacuum。官方文档明确指出，除非负载极其可预测，否则关闭它并不明智
- 频繁更新的大表，可下调该表的 `autovacuum_vacuum_scale_factor`，让它更早触发
- 定期 VACUUM 还有一个硬性理由：**防止事务 ID 回卷**。事务 ID 是 32 位，长期不清理会导致旧数据"变成未来数据"而不可见，VACUUM 会把足够老的行标记为冻结（frozen）来避免这个问题
- 监控膨胀：`pg_stat_user_tables` 里的 `n_dead_tup`、`last_autovacuum` 是常用观测点

### 4.9 MVCC 与隔离级别的对应关系

| 隔离级别 | MVCC 行为 |
| --- | --- |
| 读已提交 | 每条语句取一个新快照 |
| 可重复读 | 事务内第一条语句取快照，整个事务复用 |
| 串行化 | 在可重复读基础上加谓词锁，检测读写依赖冲突 |

### 4.10 澄清："MVCC 就没有锁"是误解

MVCC 消除的是"读与写之间的阻塞"，并不是取消所有锁。表级锁的主要模式与实际影响：

| 操作 | 获取的表级锁 | 是否阻塞普通 `SELECT` |
| --- | --- | --- |
| `SELECT` | `ACCESS SHARE` | 否 |
| `INSERT` / `UPDATE` / `DELETE` | `ROW EXCLUSIVE` | 否（但会阻塞部分 DDL） |
| `VACUUM`（不带 FULL）、`ANALYZE`、`CREATE INDEX CONCURRENTLY` | `SHARE UPDATE EXCLUSIVE` | 否 |
| `CREATE INDEX`（不带 CONCURRENTLY） | `SHARE` | 否（阻塞写入） |
| `DROP` / `TRUNCATE` / `REINDEX` / `CLUSTER` / `VACUUM FULL` / 多数 `ALTER TABLE` | `ACCESS EXCLUSIVE` | **是** |

另外还有行级锁：更新同一行的两个事务必须排队；`SELECT ... FOR UPDATE` 会显式加行锁。两个事务互相等待对方持有的锁时形成死锁，PostgreSQL 会自动检测并中止其中一个事务。

### 4.11 MVCC 的优缺点

**优点：** 读写互不阻塞、并发能力强、天然提供语句级/事务级一致视图、无需应用层加读锁。

**缺点：** 存储膨胀（旧版本占空间）、清理成本（VACUUM 消耗 I/O 与 CPU）、长事务会让旧版本迟迟无法回收、索引也可能膨胀。

### 4.12 最佳实践

- 控制事务粒度，避免长事务（长事务 = 旧版本回收的"钉子户"）
- 合理配置 autovacuum，必要时对热点表单独设置参数
- 监控表与索引膨胀，及时处理异常增长
- 大批量删除后，评估是否需要 `VACUUM`，而不是直接 `VACUUM FULL`
- 定期 `ANALYZE`，让优化器拿到准确统计

## 五、慢查询诊断与优化

慢查询优化的核心不是"背技巧"，而是形成固定流程：先定位是哪条 SQL 慢，再看它的执行计划为什么慢，最后按"改 SQL → 改索引 → 改参数 → 换硬件"的顺序处理。跳过诊断直接调参，往往是在猜。

### 5.1 第一步：把慢 SQL 抓出来

**开启慢语句日志：**

```sql
-- 记录执行超过 1 秒的语句（也可写 1000，单位为毫秒）
ALTER SYSTEM SET log_min_duration_statement = '1s';

-- 该参数属于配置文件级（SIGHUP），重新加载即可，无需重启实例
SELECT pg_reload_conf();
```

> 常见错误：先"重启数据库"再执行 `pg_reload_conf()`。这个参数不需要重启，`pg_reload_conf()` 就够了；重启只在改 `shared_preload_libraries`、`wal_level` 这类"只能在启动时设置"的参数时才需要。

**用扩展做统计聚合：**

```sql
-- 安装扩展（需要先在 shared_preload_libraries 中加载并重启实例）
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 按平均耗时排序，找出最耗时的语句
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

> 版本提示：PostgreSQL 13 起列名为 `total_exec_time` / `mean_exec_time`；12 及更早版本是 `total_time` / `mean_time`。从旧版本升级脚本时，列名对不上是常见报错原因。

### 5.2 第二步：看执行计划

```sql
EXPLAIN ANALYZE
SELECT u.username, COUNT(o.id) AS order_count
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.total_amount > 1000
GROUP BY u.username
ORDER BY order_count DESC;
```

`EXPLAIN` 只显示"计划与估算"，`EXPLAIN ANALYZE` 会真正执行并给出实际耗时——**在生产上对大查询直接跑 ANALYZE 要谨慎**，可先加 `EXPLAIN (ANALYZE, BUFFERS)` 在测试库验证。

执行计划里的关键指标：

- `Seq Scan`：全表顺序扫描，通常意味着没有可用索引或选择性太差
- `Index Scan` / `Bitmap Index Scan`：走了索引
- `Cost`：优化器的估算代价（相对值，不是毫秒）
- `Rows`：估算返回行数；与实际行数差很多，说明统计信息不准
- `Actual Time`：实际耗时（仅 `ANALYZE` 时出现）

### 5.3 第三步：索引层面优化

```sql
-- 为高频查询条件建复合索引（注意字段顺序：等值在前，范围在后）
CREATE INDEX idx_orders_user_total ON orders (user_id, total_amount);

-- 多条件组合查询
CREATE INDEX idx_orders_user_total_created ON orders (user_id, total_amount, created_at);

-- 部分索引：只为"经常被查的那一小部分数据"建索引，体积更小
CREATE INDEX idx_high_value_orders ON orders (user_id)
WHERE total_amount > 1000;
```

部分索引（partial index）的前提是查询条件里**也带同样的 WHERE**，否则优化器用不上它。

### 5.4 第四步：改写 SQL

**避免在条件里堆子查询（视情况改写为连接）：**

```sql
-- 可读性差、有时执行计划不理想的写法
SELECT * FROM users
WHERE id IN (SELECT user_id FROM orders WHERE total_amount > 1000);

-- 改为连接 + 去重（注意：结果集语义要与原写法一致）
SELECT DISTINCT u.*
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.total_amount > 1000;
```

**用 EXISTS 表达"存在性"判断：**

```sql
-- 关心"有没有"，不关心"有几条"时，EXISTS 语义更清晰
SELECT * FROM users u
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.user_id = u.id AND o.total_amount > 1000
);
```

> 客观提示：现代版本的优化器常把 `IN (子查询)` 改写成半连接，性能不一定比 `EXISTS` 差。不要背诵"EXISTS 一定更快"，应以 `EXPLAIN` 的实际计划为准。

### 5.5 Java 侧配合优化

```java
import java.util.List;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.springframework.stereotype.Repository;

@Repository
public class UserOrderRepository {

    @PersistenceContext
    private EntityManager entityManager;

    // 只查需要的列、用 DTO 承接，避免查出整实体再丢弃
    public List<UserOrderSummary> getHighValueOrders(int threshold) {
        return entityManager.createQuery(
                "SELECT new UserOrderSummary(u.id, u.username, COUNT(o)) " +
                "FROM User u JOIN u.orders o " +
                "WHERE o.totalAmount > :threshold " +
                "GROUP BY u.id, u.username",
                UserOrderSummary.class)
            .setParameter("threshold", threshold)
            .setHint("org.hibernate.cacheable", true) // 需要开启二级缓存才有意义
            .getResultList();
    }
}
```

此外要注意：避免 N+1 查询、批量操作使用 `saveAll` 或 `JOIN FETCH`、分页查询不要用超大 offset（深分页可改为"按主键游标"）。

### 5.6 系统参数调优

```sql
-- 共享缓冲区：通常按物理内存的 25% 左右起步（经验值，需压测验证）
ALTER SYSTEM SET shared_buffers = '4GB';

-- 告诉优化器"操作系统缓存大概有多少"，只影响估算，不真正分配内存
ALTER SYSTEM SET effective_cache_size = '12GB';

-- 单个 Gather 节点可用的并行工作进程数（默认 2）
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
```

`shared_buffers` 默认值偏小（通常 128MB），生产环境几乎都要调；但并不是越大越好——超过一定比例后，收益会被操作系统页缓存的重叠抵消。

### 5.7 定期维护

```sql
-- 更新统计信息
ANALYZE users;
ANALYZE orders;

-- 重建索引（大表用 CONCURRENTLY 版本，代价是耗时更长）
REINDEX INDEX CONCURRENTLY idx_orders_user_total;
```

### 5.8 性能诊断清单

| 诊断点 | 可能原因 | 优化方向 |
| --- | --- | --- |
| 全表扫描（Seq Scan） | 缺索引、条件选择性差、统计信息过期 | 建合适索引、`ANALYZE` |
| 大量 JOIN | 连接顺序差、缺连接列索引 | 补索引、改写查询、拆分 |
| 复杂子查询 | 无法下推、重复扫描 | 改写为连接或 EXISTS |
| 估算行数与实际差很多 | 统计信息不准、数据倾斜 | `ANALYZE`、调 `default_statistics_target` |
| 临时文件/排序溢出 | `work_mem` 不足 | 适当提高 `work_mem`、加索引避免排序 |
| 锁等待 | 长事务、DDL 阻塞 | 缩短事务、用 `CONCURRENTLY` |

### 5.9 优化层次与指导原则

- **优化层次**：查询层（改写 SQL）→ 索引层（调整索引结构）→ 系统层（参数）→ 硬件层（内存、SSD）
- **指导原则**：越早优化成本越低；按数据特征定制方案；用指标量化收益；平衡开发成本与性能收益

一句话总结：先测量，再动手；每次只改一个变量，改完用执行计划验证。

## 六、JSON 与 JSONB

PostgreSQL 提供两种 JSON 类型，名字只差一个字母，行为差别却不小：`json` 保存原始文本，`jsonb` 保存解析后的二进制结构。选错类型最直接的后果是"查得慢、还建不了合适的索引"。

### 6.1 存储方式差异

**JSON 类型：** 以原始文本形式存储，保留空格、缩进和键的顺序，每次处理都要重新解析。

```sql
CREATE TABLE user_profiles (
  id SERIAL PRIMARY KEY,
  profile JSON
);

INSERT INTO user_profiles (profile)
VALUES ('{"name": "user_a", "age": 30, "skills": ["Java", "PostgreSQL"]}');

-- 原样返回，格式不变
SELECT profile FROM user_profiles;
```

**JSONB 类型：** 解析后以二进制形式存储，不保留空白，不保证键的顺序，重复键只保留最后一个。

```sql
CREATE TABLE user_profiles_jsonb (
  id SERIAL PRIMARY KEY,
  profile JSONB
);

INSERT INTO user_profiles_jsonb (profile)
VALUES ('{"name": "user_a", "age": 30, "skills": ["Java", "PostgreSQL"]}');

-- 输出会被重新格式化，键的顺序可能变化
SELECT profile FROM user_profiles_jsonb;
```

### 6.2 性能和查询特点

| 维度 | `json` | `jsonb` |
| --- | --- | --- |
| 存储形式 | 原始文本 | 解析后的二进制 |
| 写入速度 | 快（不做解析转换） | 略慢（有转换开销） |
| 查询速度 | 慢（每次重新解析，且无专用索引） | 快（可直接建 GIN 索引） |
| 保留格式 | 保留空白与键序 | 不保留 |
| 重复键 | 全部保留 | 只保留最后一个 |
| 特殊限制 | 不校验数值范围 | 拒绝超出 `numeric` 范围的数字 |

> 版本提示：`json` 与 `jsonb` 自 PostgreSQL 9.4 起提供；较早版本只有 `json`（9.2/9.3），升级老项目时要注意。

### 6.3 查询示例

**JSON 查询：**

```sql
-- 每次都要重新解析文本；-> 返回 json，->> 返回 text
SELECT profile -> 'name' AS name_json
FROM user_profiles
WHERE profile ->> 'age' = '30';
```

**JSONB 查询：**

```sql
-- 建 GIN 索引：支持 @>、?、?|、?&、@?、@@ 等操作符
CREATE INDEX idx_user_profiles_gin ON user_profiles_jsonb USING GIN (profile);

-- 包含查询：找出 age = 30 的文档
SELECT profile -> 'name' AS name_json
FROM user_profiles_jsonb
WHERE profile @> '{"age": 30}';

-- 存在查询：数组里是否含有 "Java"
SELECT profile ->> 'skills' AS skills
FROM user_profiles_jsonb
WHERE profile -> 'skills' ? 'Java';
```

补充说明：

- `@>` 是"包含"，`?` 是"顶层键或数组元素存在"，两者语义不同，别混用
- 默认的 GIN 操作符类 `jsonb_ops` 支持 `@>`、`?`、`?|`、`?&`、`@?`、`@@`；另一种 `jsonb_path_ops` 只支持 `@>`、`@?`、`@@`，但索引更小、检索更精确，代价是无法再用 `?` 查键
- `jsonb` 也支持 B-Tree 与 Hash 索引，但通常只在"整份文档比相等"时才有用

### 6.4 使用场景推荐

| 类型 | 适合的场景 | 不适合的场景 |
| --- | --- | --- |
| `json` | 日志原文留存、需要保留输入格式的配置、几乎不检索的半结构化数据 | 需要按字段过滤、需要建索引 |
| `jsonb` | 需要频繁检索与过滤的文档、电商商品属性、用户动态配置、复杂查询与索引 | 必须逐字节保留原始文本 |

> 与 MySQL 的差异：MySQL 的 JSON 也是二进制存储，但要建索引通常得借助生成列或函数索引；PostgreSQL 的 `jsonb` 可以直接建 GIN 索引，写法更直接。

### 6.5 空间与写入代价

- `jsonb` 因解析与结构开销，通常会占用略多存储空间（视文档内容而定）
- 大量写入时，`jsonb` 的转换开销会让写入略慢
- 读取与复杂检索场景下，`jsonb` 明显优于 `json`
- 更新 JSONB 中某个字段时，整行会被重写并加行锁，因此单份文档不宜过大

### 6.6 实践建议与注意事项

1. 默认优先使用 `jsonb`
2. 只有"原始格式必须逐字节保留"时才用 `json`
3. 写入密集场景先做压测，再决定是否用 `jsonb`
4. 常用查询字段配 GIN 索引；只查固定路径时，表达式索引往往更小更快
5. 注意类型转换：`->>` 得到的是 `text`，比较数字要显式转型（例如 `(profile ->> 'age')::int`），否则会走字符串比较

注意事项：

- `json` / `jsonb` 自 PostgreSQL 9.4 起完整支持
- 谨慎处理类型转换，可能丢失精度或报错
- 复杂查询优先考虑 `jsonb`
- 结构化程度高、经常参与连接与聚合的数据，仍应拆成普通列（JSON 不能替代表设计）

一句话总结：JSONB 在大多数现代应用中是更合适的选择，除非确有"原样保留文本"的需求。

## 七、参数与版本差异速查

这一节把前文出现的默认值与"容易记错的点"集中列出，便于查对。表中默认值以 PostgreSQL 官方文档为准；**升级大版本前，务必核对目标版本的文档**，默认值可能调整。

### 7.1 常用参数默认值

| 参数 | 默认值 | 说明 | 生效方式 |
| --- | --- | --- | --- |
| `wal_level` | `replica` | 支持归档与流复制 | 重启 |
| `max_wal_size` | `1GB` | WAL 体积软上限 | 重载 |
| `min_wal_size` | `80MB` | WAL 文件回收下限 | 重载 |
| `checkpoint_timeout` | `5min`（30s ~ 1d） | 自动检查点最长间隔 | 重载 |
| `fsync` | `on` | 生产环境不要关闭 | 重启/配置文件 |
| `synchronous_commit` | `on` | 设为 `off` 可提速但可能丢最近提交 | 随时 |
| `shared_buffers` | 通常 `128MB` | 共享缓冲区，生产需按内存调整 | 重启 |
| `max_parallel_workers_per_gather` | `2` | 单 Gather 的并行度 | 随时 |
| `autovacuum` | `on` | 自动清理，默认开启 | 重载 |
| `log_min_duration_statement` | `-1`（不记录） | 设为正值记录慢语句 | 重载 |
| `default_transaction_isolation` | `read committed` | 默认隔离级别 | 随时 |

### 7.2 常见版本差异与易错点

- `checkpoint_timeout` 默认值是 **5 分钟**，不是 15 分钟
- PostgreSQL 的**可重复读不会出现幻读**（快照隔离），别照搬 MySQL 的结论
- 读未提交在 PostgreSQL 中等同读已提交，没有额外收益
- Hash 索引在 9.6 及更早版本不写 WAL、不建议使用；较新版本已修复
- `pg_stat_statements` 的列名在 13 起改为 `total_exec_time` / `mean_exec_time`
- `json` / `jsonb` 自 9.4 起提供；`jsonb` 不保留空白与键序
- 普通 `VACUUM` 一般不把空间还给操作系统，`VACUUM FULL` 会锁表
- autovacuum 不会对分区父表执行 `ANALYZE`，需要手动维护

### 7.3 参考资料

- PostgreSQL Global Development Group. PostgreSQL 官方文档：并发控制（事务隔离级别、显式锁）、索引（索引类型）、例行维护（VACUUM 与 autovacuum）、数据类型（JSON 类型）、服务器配置（WAL）。2026
- PostgreSQL Global Development Group. PostgreSQL 官方文档：pg_stat_statements 模块（9.6 / 12 / 18 版本对照）。2026
