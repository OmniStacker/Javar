# Mysql知识汇总
---


# MySQL面试题合集

# 说说你对 MySQL 锁的理解

## 1.MySQL中的锁分类

* 按粒度分**表锁**、**行锁**和**页锁**三种，
* 按类型分\*\*读锁和写锁(都属于悲观锁)\*\*两种。
* 按性能分**乐观锁**、**悲观锁和意向锁**。

其中，MyISAM和MEMORY存储引擎采用的是**表级锁**，而InnoDB存储引擎支持**行级锁和表级锁**。

## 2.表锁、行锁、页锁

### 表锁：

每次操作锁住整张表。**开销小，加锁快；（**~~**不会出现死锁**~~评论反馈更正\*\*）发生死锁的概率更小(多事务循环等待情况)；\*\*锁定粒度大，发生锁冲突的概率最高，并发度最低；一般用在整表数据迁移的场景。

```sql
CREATE TABLE locker (
  id INT PRIMARY KEY,
  name VARCHAR(255),
  value INT
);

INSERT INTO locker (
	id, name, value
) VALUES
(1, '张三', 2),	(2, '张三', 3),(3, '张三', 4);
```

```sql
BEGIN;
SELECT * FROM locker WHERE value = 2 FOR UPDATE;
```

因value字段**没有索引**，所以这个 SQL 语句会对 locker 表进行加锁，也就是**表锁**。在事务提交之前，该表数据将无法被其他事务修改。

### 行锁：

对表中一行或多行记录进行加锁控制的方式。\*\*开销大，加锁慢；会出现死锁；\*\*锁定粒度最小，发生锁冲突的概率最低，并发度最高。在 MySQL 中，**行锁是基于索引加载的**，即行锁是要加在索引响应的行上。**索引失效时会升级为表锁。**

```sql
#给locker表中value列添加索引
ALTER TABLE locker ADD index idx_value (value);

BEGIN;
SELECT * FROM locker WHERE value = 2 FOR UPDATE;
```

value字段**添加索引后**，这条SQL只会针对value值为2的记录进行加锁，也就是**行锁**。在事务提交之前，这些行数据将无法被其他事务修改。

### 页锁：

只有BDB存储引擎支持页锁，页锁就是在页的粒度上进行锁定，锁定的数据资源比行锁要多，因为一个页中可以有多个行记录。当我们使用页锁的时候，会出现数据浪费的现象，但这样的浪费最多也就是一个页上的数据行。页锁的开销介于表锁和行锁之间，会出现死锁。锁定粒度介于表锁和行锁之间，并发度一般。

## 3.读锁、写锁、意向锁

### 读锁（共享锁，S锁（shared））：

多个读操作对同一个资源共享同一个锁，多个读操作可以同时进行而不会互相影响。因为读操作并不会改变数据内容，所以多个事务可以共享同一个锁，并行地读取同一个资源，这样可以提高并发效率。

### 写锁（排它锁，X锁（exclude））：

当两个事务同时对表中某行数据进行更新操作时，若一个事务先到达并给该行加上排它锁，那么另一个事务就不能在该行加任意类型的锁，直到第一个事务释放了该行的锁。因此，排它锁可以确保在同一时间只有一个事务可以对被加锁的资源进行修改操作，从而避免出现数据竞争和不一致问题。

### 意向锁（I锁（Intent Lock））：

数据库中的一种表级锁，在行级锁的基础上引入的一种概念。意向锁是用于解决多粒度锁定而设计的，可以避免行级锁和表级锁之间的冲突。\
意向锁分为两种类型：**意向共享锁（Intention Shared Lock, IS）和意向排他锁（Intention Exclusive Lock, IX）**。

* **意向共享锁（IS）**：在一个事务需要对表中某些行加共享锁（S锁）时，事务首先需要获得表的意向共享锁（IS锁）
* **意向排他锁（IX）**：指的是在一个事务需要对表中某些行加排它锁（X锁）时，事务首先需要获得表的意向排它锁（IX锁）。

**意向锁简单来说就是添加行锁时，给表添加一个标识表明该表已经存在共享锁或者是排它锁，其他事务需要加锁直接读取该标识判断是否已经存在锁。**

## 4.间隙锁（Gap-Lock）

间隙锁就是两个值之间的空隙加锁，是Innodb在可重复读隔离级别下为了解决幻读问题而引入的一种锁机制。需注意**间隙锁只会在可重复读隔离级别（REPEATABLE-READ）下才会生效**。

```sql
drop TABLE orders;
CREATE TABLE orders (
    order_id INT NOT NULL PRIMARY KEY,
    product_name VARCHAR(50) NOT NULL,
    quantity INT NOT NULL
)  ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT INTO orders (
	order_id,
	product_name,
	quantity
)
VALUES
	(1, 'iPhone', 2),
	(2, 'iPad', 1),
	(3, 'MacBook', 3),
	(7, 'AirPods', 7),
	(10, 'Apple Watch', 10);
```

![1681647534852-79c6b665-6a01-4e76-8ced-a59bd08408b7.png](images/1681647534852-79c6b665-6a01-4e76-8ced-a59bd08408b7.png)

此时orders表存在（3,7），（7,10），（10,正无穷）。\
**操作步骤如下**：\
开启A事务修改id为8的数据，但是不提交事务，同时开启事务B进行插入id为9的数据。

```sql
#事务A
set tx_isolation = 'REPEATABLE-READ';
BEGIN;
SELECT * FROM orders WHERE order_id = 8 FOR UPDATE;
COMMIT;

#事务B
set tx_isolation = 'REPEATABLE-READ';
BEGIN;
INSERT INTO orders (
	order_id,
	product_name,
	quantity
)
VALUES
	(9, 'AirPods Pro', 2);
COMMIt;

#事务C
BEGIN;
SELECT * FROM orders WHERE order_id = 10 FOR UPDATE;
COMMIt;
```

此时事务B阻塞无法插入成功；再开启事务C进行数据修改，可以修改成功；将事务A进行提交，事务B随即插入成功。\
**间隙锁可以锁定一个范围内的所有记录，包括不存在的记录，从而防止其他事务在该范围内插入或修改数据**\*\*。\*\*

**其他场景：**

```sql
-- 事务A
set tx_isolation = 'REPEATABLE-READ';
BEGIN;
SELECT * FROM orders WHERE order_id = 8 FOR UPDATE;
#commit;
```

其他事务无法在这个（7,10）区间插入任何数据。

```sql
-- 事务A
set tx_isolation = 'REPEATABLE-READ';
BEGIN;
SELECT * FROM orders WHERE order_id = 15 FOR UPDATE;
#commit;
```

其他事务无法在这个（10,正无穷）区间插入任何数据。

如果大家在操作时，按以上步骤未能重现，大概率是客户端工具有问题，在单个客户端界面中使用多查询页，有些工具是一个事务，即使是使用 begin 开启事务。可以尝试多开客户端工具重新测试。

## 5.临键锁（Next-key Locks）

临键锁（Next-key Locks）是MySQL InnoDB存储引擎实现的一种数据行级别的锁机制，它是**行级锁与间隙锁的组合**，即位于索引记录与索引区间之间的一种排它锁。\
临键锁主要目的是为了解决幻读问题，能够封锁该条记录相邻两个键之间的空白区域，防止其他事务在这个区域内插入、修改、删除数据。临键锁只与非唯一索引列有关，在唯一索引列（包括主键列）上不存在临键锁\
![1681647534852-79c6b665-6a01-4e76-8ced-a59bd08408b7.png](images/1681647534852-79c6b665-6a01-4e76-8ced-a59bd08408b7.png)

```sql
#事务A
set tx_isolation = 'REPEATABLE-READ';
BEGIN;
SELECT * FROM orders WHERE order_id >= 3 and  order_id  怎么保留呢？还记得事务日志undo log吗？

对于使用 InnoDB 存储引擎的数据库表，它的聚簇索引记录中都包含下面两个隐藏列：

* trx\_id，当一个事务对某条聚簇索引记录进行改动时，就会把**该事务的事务 id 记录在** trx\_id **隐藏列里**；
* roll\_pointer，每次对某条聚簇索引记录进行改动时，都会**把旧版本的记录写入到 undo 日志中，然后这个隐藏列是个指针，指向每一个旧版本记录**，于是就可以通过它找到修改前的记录。

InnoDB 里面每个事务有一个唯一的事务 ID，叫作 transaction id。它是在事务开始的时候向 InnoDB 的事务系统申请的，是按申请顺序严格递增的。

![1680071884160-c066d323-0ea4-4b3f-8f09-3ea38ce3330f.png](images/1680071884160-c066d323-0ea4-4b3f-8f09-3ea38ce3330f.png)

如上图所示，针对`id=10001`的这条数据，都会将旧值放到一条`undo`日志中，就算是该记录的一个旧版本，随着更新次数的增多，所有的版本都会被 `roll_pointer` 属性连接成一个链表，我们把这个链表称之为**版本链**，根据版本链就可以找到这条数据历史的版本。

![1680089702903-13895075-6e1a-47b4-b0f2-a299b7176d4e.png](images/1680089702903-13895075-6e1a-47b4-b0f2-a299b7176d4e.png)

利用`undo log`日志我们已经保留下了数据的各个版本，那么现在关键的问题是要读取哪个版本的数据呢？

这时就需要用到**ReadView**了，ReadView就是事务在使用MVCC机制进行快照读操作时产生的一致性视图, 比如**默认隔离级别可重复读隔离级别**（RR），在**第一次查询的时候(**注意这个细节，RC和RR区别关键在此**)**，创建一个ReadView, 那ReadView种都有哪些关键信息呢？

更多细节可超链接：[天明](https://www.yuque.com/tianming-aroh0/sagnbd/nfkf7dvzxgp26nw4)

![1680095929852-60ae40d0-a547-44dd-b419-677e29347107.png](images/1680095929852-60ae40d0-a547-44dd-b419-677e29347107.png)

![1740032620507-03f5705b-d889-4038-8524-688de3ab3fff.png](images/1740032620507-03f5705b-d889-4038-8524-688de3ab3fff.png)

* trx\_ids: 指的是在创建 ReadView 时，当前数据库中「活跃事务」的事务 id 列表，注意是一个列表， **“活跃事务”指的就是，启动了但还没提交的事务**。
* min\_trx\_id: 指的是在创建 ReadView 时，**当前数据库中「活跃事务」中事务 id 最小的事务**，也就是 m\_ids 的最小值。
* max\_trx\_id：这个并不是 m\_ids 的最大值，而是**创建** ReadView **时当前数据库中应该给下一个事务的 id 值，也就是全局事务中最大的事务 id 值 + 1**；
* creator\_trx\_id ：指的是创建该 ReadView 的事务的事务 id, 只有在对表中的记录做改动时（执行INSERT、DELETE、UPDATE这些语句时）才会为 事务分配事务id，否则在一个只读事务中的事务id值都默认为0。

![1680095960762-04342929-209b-4705-b013-a77e6c294eda.png](images/1680095960762-04342929-209b-4705-b013-a77e6c294eda.png)

对于当前事务的启动瞬间来说，读取的一个数据版本的trx\_id，有以下几种可能：

* 如果被访问版本的trx\_id属性值与ReadView中的 creator\_trx\_id 值相同，意味着当前事务在访问它自己修改过的记录，所以该版本可以被当前事务访问。
* 如果落在绿色部分，表示这个版本是已提交的事务或者是当前事务自己生成的，这个数据是可见的；
* 如果落在红色部分，表示这个版本是由将来启动的事务生成的，是肯定不可见的；
* 如果落在黄色部分，那就包括两种情况
  * 若 数据的trx\_id在trx\_ids数组中，表示这个版本是由还没提交的事务生成的，不可见, 去读取这条数据的历史版本，这条数据的历史版本中都包含了事务id信息，去查找第一个不在活跃事务数组的版本记录。
  * 若 数据的trx\_id不在trx\_ids数组中，表示这个版本是已经提交了的事务生成的，可见。

这种通过**版本链 + 一致性视图** 来控制并发事务访问同一个记录时的行为就叫 MVCC（多版本并发控制）。

为了方便大家深入理解。[我](https://www.yuque.com/tianming-aroh0/sagnbd/nfkf7dvzxgp26nw4)这里给大家通过源码整理图表。

![1740032712840-f93f6a56-77f9-46fa-9bc7-1f11c81c2d2f.png](images/1740032712840-f93f6a56-77f9-46fa-9bc7-1f11c81c2d2f.png)

不同事务是否可见可参看如下高低水位图。

![1740032759387-c47384a2-a648-48dc-8503-b78c73276c57.png](images/1740032759387-c47384a2-a648-48dc-8503-b78c73276c57.png)

如果你对MVCC机制的整个流程还是比较模糊，我们现在举例来说明下。比如student表中有一个事务`id`为`10001`的插入记录：

```sql
insert into student(id, name, balance) values(10001, '北冥', '2000')
```

我们现在在MySQL的读已提交和可重复读隔离级别下，MVCC机制的整个工作流程。

MySQL中的读未提交和序列化并不需要MVCC机制，读未提交，直接读取别人未提交的数据，而序列化全程用加锁的方式，也用不上MVCC, 大家体会下。

可重复读REPEATABLE READ 隔离级别的事务来说，只会在第一次执行查询语句时生成一个 ReadView ，之后的查询就不会重复生成了。（简单来说就是不管这个事务查多少次，他都用的一个全局的ReadView）

```sql
-- 事务A
-- 事务ID - 2
begin
UPDATE student SET name="北冥-2" WHERE id=10001;

-- 事务B
-- 事务ID - 3
UPDATE student SET name="北冥-3" WHERE id=10001;

-- 事务C
begin
SELECT * FROM student WHERE id = 10001;
```

![1680179062059-b0d38f09-c952-4985-8a6b-c4e4006d70d9.png](images/1680179062059-b0d38f09-c952-4985-8a6b-c4e4006d70d9.png)

![1680179084203-0d51bb36-caff-423f-a7b0-c3f49dbef6bc.png](images/1680179084203-0d51bb36-caff-423f-a7b0-c3f49dbef6bc.png)

事务A和B均未提交，现在事务C执行select, 那么得到的结果是什么呢？

1. 在执行select语句时会先生成一个ReadView：
   1. trx_ids列表的内容就是[2, 3]
   2. min_trx_id为1
   3. max_trx_id为4
   4. creator_trx_id为0
2. 然后从版本链中挑选可见的记录，从图中看出，
   1. 最新版本的列name的内容是'北冥-3'
   2. trx_id值为3
   3. 在trx_ids列表内，所以不符合可见性要求
   4. 根据roll_pointer跳到下一个版本。
3. 下一个版本的列name的内容是'北冥-2'
   1. 该版本的trx_id值为2
   2. 也在trx_ids列表内
   3. 所以也不符合要求，继续跳到下一个版本。
4. 下一个版本的列name的内容是'北冥'
   1. 该版本的trx_id值为1
   2. 小于ReadView中的min_trx_id值2
   3. 说明已经提交了，那么最终返回'北冥'。

读已提交`READ COMMITTED`是每次读取数据前都生成一个`ReadView`。这就是为啥RC读多次读可能结果不一致的原因。

![1680176728820-fd131d06-d868-4aef-951c-e195acf4e2cc.png](images/1680176728820-fd131d06-d868-4aef-951c-e195acf4e2cc.png)

![1680180052328-998ea2ad-345a-41d6-b37a-036fcb0f5223.png](images/1680180052328-998ea2ad-345a-41d6-b37a-036fcb0f5223.png)

这里重点介绍了MVCC机制，以及 MVCC 在 READ COMMITTD、 REPEATABLE READ 这两种隔离级别的事务在执行快照读操作时访问记录的版本链的过程。这样使不同事务的 读-写 、 写-读 操作并发执行，从而提升系统性能。

* READ COMMITTD 在每一次进行普通SELECT操作前都会生成一个ReadView
* REPEATABLE READ 只在第一次进行普通SELECT操作前生成一个ReadView，之后的查询操作都重复使用这个ReadView就好了。

# MySQL 深分页优化方案

### 1.数据准备

```plsql
-- 1.创建表：
drop table user_login_log;

CREATE TABLE user_login_log (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id VARCHAR(64) NOT NULL,
  ip VARCHAR(20) NOT NULL,
  attr1 VARCHAR(255),
  attr2 VARCHAR(255),
  attr3 VARCHAR(255),
  attr4 VARCHAR(255),
  attr5 VARCHAR(255),
  attr6 VARCHAR(255),
  attr7 VARCHAR(255),
  attr8 VARCHAR(255),
  attr9 VARCHAR(255),
  attr10 VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2.mock数据：
-- 创建存储过程
DELIMITER $$
CREATE PROCEDURE insert_mock_data(IN n INT)
BEGIN
  DECLARE i INT DEFAULT 0;
	set autocommit = 0;
  WHILE i  1000000 LIMIT 100;
```

![1683351737191-156c0921-f63a-4a4f-a798-5494ba32dfbe.png](images/1683351737191-156c0921-f63a-4a4f-a798-5494ba32dfbe.png)\
针对偏移量越大的情况，我们可以做如下优化：

* 添加where条件缩减扫描条数，然后limit关键再进行数据筛选（使用索引字段进行条件过滤）

# Binlog有几种录入格式与区别

MySQL的Binlog有三种录入格式，分别是**Statement格式**、**Row格式**和**Mixed格式**。它们的主要区别如下：

## Statement格式：

* 将SQL语句本身记录到Binlog中。
* 记录的是在主库上执行的SQL语句，从库通过解析并执行相同的SQL来达到复制的目的。
* 简单、易读，节省存储空间。
* 但是，在某些情况下，由于执行计划或函数等因素的影响，相同的SQL语句在主从库上执行结果可能不一致，导致复制错误。

## Row格式：

* 记录被修改的每一行数据的变化。
* 不记录具体的SQL语句，而是记录每行数据的变动情况，如插入、删除、更新操作前后的值。
* 保证了复制的准确性，不受SQL语句执行结果的差异影响，适用于任何情况。
* 但是，相比Statement格式，Row格式会占用更多的存储空间。

## Mixed格式：

* Statement格式和Row格式的结合，MySQL自动选择适合的格式。
* 大多数情况下使用Statement格式进行记录，但对于无法保证安全复制的情况，如使用非确定性函数、触发器等，会自动切换到Row格式进行记录。
* 结合了两种格式的优势，既减少了存储空间的占用，又保证了复制的准确性。

## 小结：

* Statement格式适用于简单的SQL语句，对存储空间要求较高；
* Row格式适用于需要精确复制的场景；
* Mixed格式是综合考虑两种格式的优势而出现的折中方案。

# 添加索引真的不会锁表吗？

## 1.MySQL DDL执行方式

MySQL5.5以及之前的版本，通常更改数据表结构操作(DDL)会阻塞对表数据的增删改操作(DML)。\
MySQL5.6提供Online DDL之后可支持DDL与DML操作同时执行，降低了DDL期间对业务延迟带来的影响。

## 2.Online ddl：

### 概念：

在不中断现有数据读写操作的情况下，自动执行 DDL 语句 (例如创建、修改、删除表等) 的机制。Online DDL 可以在MySQL进行表空间或数据文件的变化时，自动执行 DDL 语句，从而避免了传统方式中，执行 DDL 语句时对数据库读写操作的干扰和中断。

### 执行过程：

Online ddl执行大致可分为三个阶段：**初始化阶段、执行阶段和提交表定义阶段**：\
**初始化阶段：**

* 评估存储引擎能力与DDL语句
* 评估ALGORITHM 和 LOCK
* 创建可升级的**MDL读锁**

**执行阶段：**

* 此阶段分为两个步骤**准备**和**执行**DDL 语句
* 此阶段是否需要MDL写锁取决于**初始化阶段**评估的因素。如果需要MDL写锁的话，仅在**准备过程**会**短暂的使用MDL写锁**，然后**降级为MDL读锁**
* DDL执行过程（最耗时）

**提交表定义阶段：**

* 此阶段会将**MDL读锁升级到MDL写锁**，此阶段一般较快，因此独占锁的时间也较短
* 用新的表定义替换旧的表定义，**释放MDL锁**

### 用法：

```sql
ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=INPLACE, LOCK=NONE;

ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=COPY, LOCK=EXCLUSIVE;
```

### 参数：

**ALGORITHM：**

\*\*ALGORITHM=DEFAULT：\*\*默认算法，使用最高效的算法\
\*\*ALGORITHM=INPLACE：\*\*在原表上进行更改，不需要生成临时表，不需要进行数据copy的过程。\
添加索引步骤：\
1.创建索引(二级索引)数据字典\
2.加共享表锁，禁止DML，允许查询\
3.读取聚簇索引，构造新的索引项，排序并插入新索引\
4.等待打开当前表的所有只读事务提交\
5.创建索引结束

\*\*ALGORITHM=COPY：\*\*最原始的方式，通过临时表创建索引，需要多一倍存储，还有更多的IO（类似5.6版本之前的处理过程）\
添加索引步骤：\
1.新建带索引（主键索引）的临时表\
2.锁原表，禁止DML，允许查询\
3.将原表数据拷贝到临时表\
4.禁止读写,进行rename，升级字典锁\
5.完成创建索引操作

**LOCK：**

\*\*LOCK=DEFAULT：\*\*默认方式，MySQL自行判断使用哪种LOCK模式，尽量不锁表\
\*\*LOCK=NONE：\*\*无锁：允许Online DDL期间进行并发读写操作。如果Online DDL操作不支持对表的继续写入，则DDL操作失败，对表修改无效\
\*\*LOCK=SHARED：\*\*共享锁：Online DDL操作期间堵塞写入，不影响读取\
\*\*LOCK=EXCLUSIVE：\*\*排它锁：Online DDL操作期间不允许对锁表进行任何操作

### 注意事项：

不是所有的ddl都支持online ddl；如下官网给出的部分支持场景：\
![1680509607122-5e10d223-1b05-44b5-80dc-03b7594755ff.png](images/1680509607122-5e10d223-1b05-44b5-80dc-03b7594755ff.png)\
![1680509744854-3ae979f5-ef47-401f-a5b3-317a95bd104b.png](images/1680509744854-3ae979f5-ef47-401f-a5b3-317a95bd104b.png)\
![1680509756926-7c09c2d5-bcf8-4db2-a849-62f5ef978805.png](images/1680509756926-7c09c2d5-bcf8-4db2-a849-62f5ef978805.png)\
更多Online ddl支持场景，可以通过MySQL官方文档去获取\

## 3.演示：

```sql
DROP TABLE IF EXISTS `scores`;
CREATE TABLE scores (
   id INT NOT NULL AUTO_INCREMENT COMMENT '序号',
   student_id INT NOT NULL COMMENT '学号',
   course_name VARCHAR(50) NOT NULL COMMENT '课程名称',
   score INT NOT NULL COMMENT '分数',
	 remarks varchar(400) COMMENT '备注',
	 PRIMARY KEY (id)
);ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

select count(*) from scores; --240w
```

### 1.使用ALGORITHM = INPLACE，Lock = NONE;

使用INPLACE，NONE时不阻塞其他事务的DML操作。

```sql
ALTER TABLE scores drop index idx_student_id;
事务A使用online ddl添加索引:
begin;
ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=INPLACE, LOCK=NONE;
commit;

1.事务A使用online ddl添加索引，事务B进行查询，可以正常读取：
begin;
select * from scores where id = 1 ;
commit;

2.事务A使用online ddl添加索引，事务B进行修改，可以正常修改：
begin;
update scores set course_name = '张三' where id = 1 ;
commit;

3.事务A使用online ddl添加索引，事务B进行删除，可以正常删除：
begin;
delete from scores where id = 1;
commit

4.事务A使用online ddl添加索引，事务B进行插入，可以正常插入：
begin;
INSERT INTO `scores` (`id`, `student_id`, `course_name`, `score`, `remarks`)
	VALUES ('1', '1', 'mock_Chinese1', '71', 'mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks');
commit;
```

### 2.使用ALGORITHM = COPY，Lock = EXCLUSIVE;

使用COPY，EXCLUSIVE时，会阻塞其他事务的DML操作。当DDL事务提交后，其他事务才能正常DML操作。

```sql
ALTER TABLE scores drop index idx_student_id;
事务A使用online ddl添加索引:
begin;
ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=COPY, LOCK=EXCLUSIVE;
commit;

1.事务A使用online ddl添加索引，事务B进行查询出现阻塞，需等事务A结束：
begin;
select * from scores where id = 1 ;
commit;

2.事务A使用online ddl添加索引，事务B进行修改出现阻塞，需等事务A结束：
begin;
update scores set course_name = '张三' where id = 1 ;
commit;

3.事务A使用online ddl添加索引，事务B进行删除出现阻塞，需等事务A结束：
begin;
delete from scores where id = 1;
commit

4.事务A使用online ddl添加索引，事务B进行插入出现阻塞，需等事务A结束：
begin;
INSERT INTO `scores` (`id`, `student_id`, `course_name`, `score`, `remarks`)
	VALUES ('1', '1', 'mock_Chinese1', '71', 'mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks');
commit;
```

### 3.模拟online ddl执行时，有其他事务持有MDL锁。

Online DDL 过程必须等待已经持有MDL锁的并发事务提交或者回滚才能继续执行。

```sql
ALTER TABLE scores drop index idx_student_id;
事务A进行查询，不提交事务:
begin;
select * from scores;
--commit;

事务B使用online ddl添加索引，阻塞中:
begin;
ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=INPLACE, LOCK=NONE;
commit;

事务C进行查询，阻塞中:
select * from scores where id = 1 ;

查询进程信息：
show processlist;
```

## 4.总结：

在online ddl执行过程会两次获取MDL锁，并且需要等待已经持有DML锁的并发事务提交或回滚后才能继续执行，在实际执行时需注意以下几点：

* 进行DDL操作时尽量在业务低峰期进行操作。
* 在操作之前最好确认对要操作的表没有任何进行中的操作、没有未提交事务、也没有显式事务中的报错语句。
* 设置超时时间lock\_wait\_timeout，避免长时间的metedata锁等待。

# 7种SQL的进阶用法

## 前言

还只会使用SQL进行简单的insert、update、detele吗？本文给大家带来7种SQL的进阶用法，让大家在平常工作中使用SQL简化复杂的代码逻辑。

## 1.自定义排序（ORDER BY FIELD）

在MySQL中ORDER BY排序除了可以用ASC和DESC之外，还可以使用自定义排序方式来实现。

```plsql
CREATE TABLE movies (
  id INT PRIMARY KEY AUTO_INCREMENT,
  movie_name VARCHAR(255),
  actors VARCHAR(255),
  price DECIMAL(10, 2) DEFAULT 50,
  release_date DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO movies (movie_name, actors, price, release_date) VALUES
('咱们结婚吧', '靳东', 43.2, '2013-04-12'),
('四大名捕', '刘亦菲', 62.5, '2013-12-21'),
('猎场', '靳东', 68.5, '2017-11-03'),
('芳华', '范冰冰', 55.0, '2017-09-15'),
('功夫瑜伽', '成龙', 91.8, '2017-01-28'),
('惊天解密', '靳东', 96.9, '2019-08-13'),
('铜雀台', null, 65, '2025-12-16'),
('天下无贼', '刘亦菲', 44.9, '2004-12-16'),
('建国大业', '范冰冰', 70.5, '2009-09-21'),
('赛尔号4：疯狂机器城', '范冰冰', 58.9, '2021-07-30'),
('花木兰', '刘亦菲', 89.0, '2020-09-11'),
('警察故事', '成龙', 68.0, '1985-12-14'),
('神话', '成龙', 86.5, '2005-12-22');
```

用法如下：

```plsql
-- 查询并按演员名升序排序
select * from movies order by actors asc;
```

![1741007330440-a3e2a56b-3c26-4b87-ad03-44d47874bd83.png](images/1741007330440-a3e2a56b-3c26-4b87-ad03-44d47874bd83.png)

```plsql
-- 查询并按演员名的自定义顺序排序
SELECT * FROM movies
ORDER BY FIELD(actors, '靳东', '刘亦菲', '范冰冰', '成龙');
```

![1741007347863-8b9ff118-5265-4257-b963-df56764b4e26.png](images/1741007347863-8b9ff118-5265-4257-b963-df56764b4e26.png)

## 2.空值NULL排序（**ORDER BY IF(ISNULL**）)

在MySQL中使用ORDER BY关键字加上我们需要排序的字段名称就可以完成该字段的排序。如果字段中存在NULL值就会对我们的排序结果造成影响。\
这时候我们可以使用 \*\*ORDER BY IF(ISNULL(字段), 0, 1) \*\*语法将NULL值转换成0或1，实现NULL值数据排序到数据集前面还是后面。

```plsql
select * from movies ORDER BY actors, price desc;
```

![1741007362621-92faafee-d444-42eb-ba05-6180ffabddd7.png](images/1741007362621-92faafee-d444-42eb-ba05-6180ffabddd7.png)

```plsql
-- NULL 降序
select * from movies ORDER BY if(ISNULL(actors),1,0), actors, price;
```

![1741007440706-660c82fe-4638-45da-9b83-a4e22922a6f0.png](images/1741007440706-660c82fe-4638-45da-9b83-a4e22922a6f0.png)

## 3.CASE表达式（CASE···WHEN）

在实际开发中我们经常会写很多if ··· else if ··· else，这时候我们可以使用CASE···WHEN表达式解决这个问题。\
以学生成绩举例。比如说：学生90分以上评为优秀，分数80-90评为良好，分数60-80评为一般，分数低于60评为“较差”。那么我们可以使用下面这种查询方式：

```plsql
CREATE TABLE student (
  student_id varchar(10) NOT NULL COMMENT '学号',
  sname varchar(20) DEFAULT NULL COMMENT '姓名',
  sex char(2) DEFAULT NULL COMMENT '性别',
  age int(11) DEFAULT NULL COMMENT '年龄',
  score float DEFAULT NULL COMMENT '成绩',
  PRIMARY KEY (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生表';

INSERT INTO student (student_id, sname, sex, age , score)
VALUES ('001', '张三', '男', 20,  95),
       ('002', '李四', '女', 22,  88),
       ('003', '王五', '男', 21,  90),
       ('004', '赵六', '女', 20,  74),
       ('005', '陈七', '女', 19,  92),
       ('006', '杨八', '男', 23,  78),
       ('007', '周九', '女', 20,  55),
       ('008', '吴十', '男', 22,  91),
       ('009', '刘一', '女', 21,  87),
       ('010', '孙二', '男', 19,  60);
```

```plsql
select *,case when score > 90 then '优秀'
			when score > 80 then '良好'
			when score > 60 then '一般'
			else '较差' end level
from student;
```

![1741009641442-47ecb3b9-b323-4475-abb3-d93a7f81dc2e.png](images/1741009641442-47ecb3b9-b323-4475-abb3-d93a7f81dc2e.png)

## 4.分组连接函数（GROUP\_CONCAT）

分组连接函数可以在分组后指定字段的字符串连接方式，并且还可以指定排序逻辑；连接字符串默认为英文逗号。\
比如说根据演员进行分组，并将相应的电影名称按照票价进行降序排列，而且电影名称之间通过“\_”拼接。用法如下：

```plsql
select actors,
GROUP_CONCAT(movie_name) as movie_name,
GROUP_CONCAT(price) as price from movies GROUP BY actors;
```

![1741008250275-6a64948f-f5ce-4f4e-ab97-0103bf308f7c.png](images/1741008250275-6a64948f-f5ce-4f4e-ab97-0103bf308f7c.png)

```plsql
select actors,
GROUP_CONCAT(movie_name order by price desc SEPARATOR '_') as movie_name,
GROUP_CONCAT(price order by price desc SEPARATOR '_') as price
from movies GROUP BY actors;
```

![1741008259228-88794a8a-6642-4bde-b10c-b48b641f4cf8.png](images/1741008259228-88794a8a-6642-4bde-b10c-b48b641f4cf8.png)

## 5.分组统计数据后再进行统计汇总（with rollup）

在MySql中可以使用 with rollup在分组统计数据的基础上再进行数据统计汇总，即将分组后的数据进行汇总。

```plsql
SELECT actors, SUM(price) FROM movies GROUP BY actors;
```

![1741008389823-8b175b81-3f83-4eba-a00a-632d57f0e78f.png](images/1741008389823-8b175b81-3f83-4eba-a00a-632d57f0e78f.png)

```plsql
SELECT actors, SUM(price) FROM movies GROUP BY actors WITH ROLLUP;
```

![1741008375109-34def87a-7ed8-48da-9753-7d0855cb6768.png](images/1741008375109-34def87a-7ed8-48da-9753-7d0855cb6768.png)

## 6.子查询提取（with as）

如果一整句查询中多个子查询都需要使用同一个子查询的结果，那么就可以用with as将共用的子查询提取出来并取一个别名。后面查询语句可以直接用，对于大量复杂的SQL语句起到了很好的优化作用。\
需求：获取演员刘亦菲票价大于50且小于65的数据。

```plsql
with m1 as (select * from movies where price > 50),
 m2 as (select * from movies where price >= 65)
select * from m1 where m1.id
not in (select m2.id from m2) and m1.actors = '刘亦菲';
```

![1741008578356-162f0ba6-078a-46dd-8501-dd0a62ae7ed1.png](images/1741008578356-162f0ba6-078a-46dd-8501-dd0a62ae7ed1.png)

## 7.优雅处理数据插入、更新时主键、唯一键重复

在MySql中插入、更新数据有时会遇到主键重复的场景，通常的做法就是先进行删除在插入达到可重复执行的效果，但是这种方法有时候会错误删除数据。\
1.**插入数据时**我们可以使用**IGNORE**，它的作用是插入的值遇到主键或者唯一键重复时自动忽略重复的数据，不影响后面数据的插入，即**有则忽略，无则插入**。示例如下：

```plsql
select * from movies where id >= 13;

INSERT INTO movies (id, movie_name, actors, price, release_date) VALUES
(13, '神话', '成龙', 100, '2005-12-22');

INSERT IGNORE INTO movies (id, movie_name, actors, price, release_date) VALUES
(13, '神话', '成龙', 100, '2005-12-22');

INSERT IGNORE INTO movies (id, movie_name, actors, price, release_date) VALUES
(14, '神话2', '成龙', 114, '2005-12-22');
```

![1741008774673-df21cbaa-958b-4e74-951f-1c0506a5a814.png](images/1741008774673-df21cbaa-958b-4e74-951f-1c0506a5a814.png)

![1741008927438-d50b9582-bb85-4d8d-a643-6d04056a2030.png](images/1741008927438-d50b9582-bb85-4d8d-a643-6d04056a2030.png)

2.还可以使用**REPLACE**关键字，当插入的记录遇到主键或者唯一键重复时先删除表中重复的记录行再插入，即**有则删除+插入，无则插入**，示例如下：

```plsql
REPLACE INTO movies (id, movie_name, actors, price, release_date) VALUES
(14, '神话2', '成龙', 100, '2005-12-22');

REPLACE INTO movies (id, movie_name, actors, price, release_date) VALUES
(15, '神话3', '成龙', 115, '2005-12-22');
```

![1741009080468-7d4ff11a-0b7e-491d-b909-365af9a96bd4.png](images/1741009080468-7d4ff11a-0b7e-491d-b909-365af9a96bd4.png)

3.更新数据时使用**on duplicate key update**。它的作用就是当插入的记录遇到主键或者唯一键重复时，会执行后面定义的UPDATE操作。相当于先执行Insert 操作，再根据主键或者唯一键执行update操作，即**有就更新，没有就插入**。示例如下：

```plsql
INSERT INTO movies (id, movie_name, actors, price, release_date) VALUES
(15, '神话3', '成龙', 115, '2005-12-22') on duplicate key update price = price + 10;

INSERT INTO movies (id, movie_name, actors, price, release_date) VALUES
(16, '神话4', '成龙', 75, '2005-12-22') on duplicate key update price = price + 10;
```

![1741009118730-56414e05-a0ec-4a76-87e3-f78825fd98d5.png](images/1741009118730-56414e05-a0ec-4a76-87e3-f78825fd98d5.png)

# MySQL表设计经验汇总篇

表设计是每一个后端程序员都无法避开的一块砖，而且这块砖一不小心就很容易烫手，本

篇笔记就是为了帮助大家在设计表时能够轻松拿捏。

### 1.命名规范

数据库表名、字段名、索引名等都需要命名规范。命名可读性要高，尽量使用英文，采用驼峰或者下划线分割的方式，让人见名知意。

反例：这些命名过于简单，缺乏描述性，很难让人理解它的含义。

:::tips

1. 表名：a、b、c
2. 字段名：aaa、bbb、ccc
3. 索引名：index1、index2、index3

:::

正例：这些命名就让人见名知意。

:::tips

1. 表名：customers、orders、products
2. 字段名：customer\_id、order\_date、product\_name
3. 索引名：idx\_customer\_id、idx\_order\_date

:::

Tips：

* 表名、字段名必须使用小写字母，禁止使用数字开头，禁止使用拼音，并且一般不使用英文缩写。
* 主键索引名为pk\_字段名；唯一索引名为uk\_字段名；普通索引名则为idx\_字段名。

### 2.选择合适的字段类型

设计表时，需要选择合适字段类型，比如说：

* 根据数据类型选择字段类型：不同的数据类型应该使用不同的字段类型。
  * 整数型数据可以使用 INT 或 BIGINT 类型
  * 浮点型数据可以使用 FLOAT 或 DOUBLE 类型
  * 字符型数据可以使用 VARCHAR 或 CHAR 类型
* 考虑数据长度：字段类型应该根据所需存储的数据长度来选择。
  * 如果某个字段的数据长度不会超过 10 个字符，则可以使用 CHAR(10) 类型代替 VARCHAR(50) 类型，以节省空间。
  * 如果存储的值太大，建议字段类型修改为text，同时抽出单独一张表，用主键与之对应
* 注意精度和小数位数：对于需要精确数值计算的字段（如货币和百分比），应该选择带有精度和小数位数的字段类型（如 DECIMAL ）。
* 考虑数据完整性：字段类型也应该考虑到数据完整性。
  * 日期型数据应该使用 DATE 或 DATETIME 类型，以确保输入的日期格式正确。

### 3. 主键设计要合理

主键的设计在数据库中非常重要，它用于唯一标识表中的每一行数据，并且在数据操作和查询中起到关键作用。通常主键的设计，不要与业务相关联，因为业务是会发生变化的，应当使用自增的 id，并且保持主键的连续性。比如说可以使用优化的雪花 id 等等。

### 4. 选择合适的字段长度

首先问大家一个问题，数据库字段长度表示字符长度还是字节长度？

在mysql中，varchar和char类型表示字符长度，而其他类型表示的长度都表示字节长度。

char(10)表示字符长度是10。

bigint（4）表示显示长度是4个字节，但是因为bigint实际长度是8个字节，所以bigint（4）的实际长度就是8个字节。

所以在设计表时需要充分考虑一个字段的长度，比如一个用户名字段（它的长度5~20个字符），你觉得应该设置多长呢？可以考虑设置为  varchar（32）。需要注意字段长度一般设置为2的n次方。

### 5.优先考虑逻辑删除，而不是物理删除

什么是物理删除？什么是逻辑删除？

* 物理删除：把数据从硬盘中删除，可释放存储空间
* 逻辑删除：给数据添加一个字段，比如is\_deleted，以标记该数据已经逻辑删除。

为什么推荐用逻辑删除，不推荐物理删除呢？

* 数据恢复困难。
* 物理删除会导致索引树重构

### 6.每个表都需要添加通用字段

* id： 主键，一个表必须得有主键，必须
* create\_time： 创建时间
* creator ：创建人
* update\_time: 修改时间，必须，更新记录时，需要更新它
* update\_by :修改人，非必须
* remark ：数据记录备注，非必须

### 7.一张表的字段不宜过多

建表的时候一张表的字段不要太多了。尽量不超过 20 个。超出的话优先考虑拆分，也就是通常的查询表，详情表。

* 查询效率：当表中保存的数据数量很大时，查询操作需要检索的数据也会随之增加。如果表的字段数过多，查询操作就需要读取更多的数据，这会导致查询效率变慢。
* 存储空间：表的字段数越多，每一行数据占用的存储空间也就越大。对于大型数据库来说，这可能会导致磁盘空间的浪费。
* 数据库设计复杂性：当表的字段数过多时，数据库的设计和维护变得更加复杂。这可能涉及到索引和关联表的设计，以确保数据的完整性和一致性。

### 8.定义字段尽可能not null

如果没有特殊的理由， 一般都建议将字段定义为 NOT NULL 。为什么呢？

* 首先，NOT NULL 可以防止出现空指针问题。
* 其次，NULL值存储也需要额外的空间的，它也会导致比较运算更为复杂，使优化器难以优化SQL。
* NULL值有可能会导致索引失效

如果将字段默认设置成一个空字符串或常量值并没有什么不同，且都不会影响到应用逻辑， 那就可以将这个字段设置为NOT NULL。

### 9.合理添加索引

当设计表时，需要考虑哪些字段需要加索引，可以遵循以下几个原则：

* 根据查询条件进行选择（高频使用）：如果在查询中使用了某个字段作为查询条件，那么这个字段就应该建立索引。例如，在用户表中，如果需要根据用户的姓名进行查询，那么就应该为姓名字段建立索引。
* 区分度高的字段优先：如果一个字段的取值范围非常小，例如性别只有男女两种可能，那么这个字段就不适合建立索引。相反，如果一个字段的取值范围很大且区分度高，例如用户ID，那么这个字段就非常适合建立索引。
* 不要建立过多的索引：每个表所建立的索引数量应该控制在一个合理的范围内，一般不要超过5个。因为过多的索引会导致写入速度变慢，并占用更多的存储空间。
* 联合索引优化：在某些情况下，可以通过联合索引的方式来优化查询速度，减少所需的索引数量。例如，在用户表中，如果需要根据用户姓名和年龄进行查询，那么可以将这两个字段组合成联合索引。

假设你有一个订单表，包含订单ID、用户ID、订单金额、订单状态等字段。现在需要根据用户ID和订单状态进行查询，可以考虑为用户ID和订单状态这两个字段建立联合索引，例如：

```java
CREATE TABLE order_tab (
    id int(11) NOT NULL AUTO_INCREMENT,
    user_id int(11) NOT NULL,
    amount decimal(10,2) NOT NULL,
    status varchar(20) NOT NULL,
    create_time datetime NOT NULL,
    PRIMARY KEY (id),
    KEY idx_user_status (user_id, status) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

### 10.不需要严格遵守 3NF，通过业务字段冗余来减少表关联

简单来说就是反范式设计。常见形式是在第三范式(3NF)的基础上，进一步进行冗余，从而减少表关联。

回顾下什么是数据库三范式（3NF）？

* 第一范式：对属性的原子性，要求属性具有原子性，不可再分解；
* 第二范式：对记录的唯一性，要求记录有唯一标识，即实体的唯一性，即不存在部分依赖；
* 第三方式：对字段的冗余性，要求任何字段不能由其他字段派生出来，它要求字段没有冗余，即不存在传递依赖；

假设需要设计一个产品订单表，包含以下字段：订单ID、用户ID、订单日期、产品名称、产品价格、产品数量以及订单总价。正常情况下，可能会分别设计订单表和产品表，并使用外键进行关联，例如：

```java
CREATE TABLE order (
    `id` int(11) NOT NULL AUTO_INCREMENT,
`user_id` int(11) NOT NULL,
`order_date` date NOT NULL,
`product_id` int(11) NOT NULL,
`quantity` int(11) NOT NULL,
PRIMARY KEY (`id`),
FOREIGN KEY (`product_id`) REFERENCES `product` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE product (
    `id` int(11) NOT NULL AUTO_INCREMENT,
`name` varchar(255) NOT NULL,
`price` decimal(10,2) NOT NULL,
PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

这个设计方式符合范式要求，但在查询时需要进行表关联操作，可能会降低查询效率。为了提高查询效率，我们可以使用反范式的设计方式，将订单表中的产品名称、产品价格和订单总价冗余存储到订单表中，从而避免关联查询。例如：

```java
CREATE TABLE order (
    `id` int(11) NOT NULL AUTO_INCREMENT,
`user_id` int(11) NOT NULL,
`order_date` date NOT NULL,
`product_name` varchar(255) NOT NULL,
`product_price` decimal(10,2) NOT NULL,
`quantity` int(11) NOT NULL,
`total_price` decimal(10,2) NOT NULL,
PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

通过这种反范式的设计方式，我们可以避免表关联操作，提高查询效率。但同时也带来了一些缺点，例如数据冗余、数据更新困难等。因此，在实际应用中需要根据具体情况进行选择。

### 11. 避免使用MySQL保留字

如果库名、表名、字段名等属性含有保留字时，SQL语句必须用反引号来引用属性名称，这将使得SQL语句书写、SHELL脚本中变量的转义等变得非常复杂。

如果你需要使用这些保留字作为表名、列名或其他标识符，你可以考虑以下方法来避免冲突：

1. 在标识符前或后添加下划线：例如，将表名命名为 "my\_table"，列名命名为 "column\_name"。
2. 使用不同的单词或短语：例如，将表名命名为 "orders\_table"，列名命名为 "order\_status"。
3. 使用反引号（）将标识符括起来：例如，将表名命名为 "table"，列名命名为 "column\`"。请注意，在使用反引号时要小心，确保使用正确的语法和规范

```java
ADD
ALL
ALTER
AND
AS
BETWEEN
BY
CASE
DELETE
FROM
GROUP
HAVING
INSERT
INTO
JOIN
LIKE
NOT
OR
SELECT
UPDATE
WHERE
```

### 12.不搞外键关联，一般都在代码维护

在数据库设计中，使用外键关联是一种良好的实践，可以确保数据的完整性和一致性。外键关联可以帮助维护表之间的关系，防止无效或不一致的数据插入、更新或删除操作。然而，在某些情况下，也存在一些缺点，这可能是导致现在不太推荐使用外键关联的原因之一。以下是一些这种情况：

1. 可能会导致性能问题，尤其是在对大型数据集进行操作时。这是因为每次插入、更新或删除操作都需要进行约束检查，这可能会导致额外的开销和延迟。
2. 可能会限制数据库的灵活性和可扩展性。例如，如果需要对数据库进行分区或垂直分割，外键关联可能会导致额外的复杂性和限制。
3. 可能会导致死锁和死循环，特别是在进行并发操作时。这可能会导致数据库出现不稳定的状态，从而影响系统的性能和可用性。
4. 可能会导致数据库的维护和管理成本的增加。这是因为外键关联需要额外的管理和维护工作，例如添加、修改或删除外键约束时需要额外的测试和验证。

因此，在决定是否使用外键关联时，需要考虑实际业务需求和场景，并进行权衡和决策。在某些情况下，可以采用其他方法来保证数据的完整性和一致性，例如使用应用程序逻辑或数据库触发器来实现约束检查和数据操作。同时，需要注意数据库设计的基本原则和最佳实践，例如避免数据冗余、遵循规范化原则和正常化理论等。

### 13.字段注释

设计表时每个字段的含义要注释清楚，包括枚举类型。比如说：

```java
`order_status` varchar(2) COLLATE utf8_bin NOT NULL COMMENT '订单状态 01：待支付 02：已支付 03：已发货 04：已完成 05：已取消'
```

### 14.时间的类型选择

时间类型的选择一般都要好好考虑，因为不同的类型存储的格式不同。

对于MySQL来说，主要有date、datetime、time、timestamp 和 year。

* date ：表示的日期值, 格式yyyy-mm-dd,范围1000-01-01 到 9999-12-31，3字节
* time ：表示的时间值，格式 hh:mm:ss，范围-838:59:59 到 838:59:59，3字节
* datetime：表示的日期时间值，格式yyyy-mm-dd hh:mm:ss，范围1000-01-01 00:00:00到9999-12-31 23:59:59\`\`\`,8字节，跟时区无关
* timestamp：表示的时间戳值，格式为yyyymmddhhmmss，范围1970-01-01 00:00:01到2038-01-19 03:14:07，4字节，跟时区有关
* year：年份值，格式为yyyy。范围1901到2155，1字节

推荐优先使用datetime类型来保存日期和时间，因为存储范围更大，且跟时区无关。

### 15.SQL 编写的一些优化经验

1. 避免使用SELECT \* FROM 语句，应该只选择需要的列，以减少网络传输和提高查询性能。
2. 使用索引来提高查询速度，特别是在对大型表进行查询时。
3. 避免使用外键约束，因为它们可能会导致性能问题，特别是在对大型表进行插入、更新和删除操作时。
4. 使用LIMIT 1来限制查询结果只有一条记录。
5. 避免在where子句中使用OR来连接条件，应使用UNION来连接查询。
6. 注意优化LIMIT深分页问题，可以使用OFFSET来替代LIMIT。
7. 使用where条件限制要查询的数据，避免返回多余的行。
8. 尽量避免在索引列上使用MySQL的内置函数，这可能导致索引失效。
9. 应尽量避免在where子句中对字段进行表达式操作，这可能导致索引失效。
10. 应尽量避免在where子句中使用!=或<>操作符，这可能导致索引失效。
11. 使用联合索引时，注意索引列的顺序，一般遵循最左匹配原则。
12. 对查询进行优化，应考虑在where及order by涉及的列上建立索引。
13. 如果插入数据过多，考虑批量插入。
14. 在适当的时候，使用覆盖索引。
15. 使用EXPLAIN 分析你SQL的计划。

# 为什么MySQL要默认使用RR隔离级别？

## 隔离级别的划分

![1713701321250-68f56ec1-8ac9-4655-b042-318043ed61aa.png](images/1713701321250-68f56ec1-8ac9-4655-b042-318043ed61aa.png)

SQL-92 标准定义了 4 种隔离级别，从低到高依次为：\
**读未提交(Read Uncommitted)、读已提交(Read Committed)、可重复读(Repeatable Reads)、序列化(Serializable)**。

> 在 RU 级别下，可能会出现脏读、幻读、不可重复读等问题。\ 在 RC 级别下，解决了脏读的问题，但仍存在幻读、不可重复读的问题。\ 在 RR 级别下，解决了脏读和不可重复读的问题，但仍存在幻读的问题。\ 在 Serializable 隔离级别下，解决了脏读、幻读、不可重复读全部问题。

## 常见数据库的隔离级别支持

Oracle 数据库只支持 SQL92 中的 Serializable 和 Read Committed，但实际上根据Oracle官方文档的介绍，Oracle支持三种隔离级别：Read Committed、Serializable 和 Read-Only，[官网地址](https://docs.oracle.com/cd/E11882_01/server.112/e40540/consist.htm#CNCPT621)。

![1713704153308-c4461b3d-50ac-486c-bc79-6b4f4321b0f1.png](images/1713704153308-c4461b3d-50ac-486c-bc79-6b4f4321b0f1.png)

MySQL 数据库支持SQL92 中的四种隔离级别。

需要注意的是，**Oracle的默认隔离级别是RC，而MySQL的默认隔离级别是RR**。

## 为什么 MySQL 选择的是 RR 级别？

MySQL 默认使用RR（可重复读）隔离级别的原因是基于历史和技术考虑。

MySQL 主从复制是通过 binlog 日志进行数据同步的，而在早期的版本中 binlog 记录的是SQL语句的原文。这个时候就会有一个问题，如果此时 \[binlog 格式]\(https://www.yuque.com/tulingzhouyu/db22bv/yasy523q6yns52tc?singleDoc# 《Binlog有几种录入格式与区别》 密码：yk3o)设置为 statement 格式时，MySQL 可能会在从库执行 SQL 的逻辑与主库不一致。比如：

```sql
delete from user where a >= 13 and b 0 limit 100；
2. 上述改写和 offset 0 limit 100 的效果相同，都是每个分库返回了一页数据；
3. 服务层得到 2 页数据，内存排序，取出前 100 条数据，作为最终的第一页数据，这个全局的第一页数据，一般来说每个分库都包含一部分数据；

| database1 (id%2=0) | database2 (id%2=1) |
| --- | --- |
| db0-page1（**第一页**） | db1-page1（**第一页**） |
| db0-page2 | db1-page2 |
| db0-page3 | db1-page3 |
| ... (**order by time**) | ... (**order by time**) |

**疑问：这个方案也需要服务器内存排序，岂不是和“全局视野法”一样么**？

第一页数据的拉取确实一样，但每一次“下一页”拉取的方案就不一样了。

点击“下一页”时，需要拉取第二页数据，在第一页数据的基础之上，能够找到第一页数据 time 的最大值：

| database1 (id%2=0) | database2 (id%2=1) |
| --- | --- |
| db0-page1（**time 最大值**） | db1-page1 |
| db0-page2 | db1-page2（**time 最大值**） |
| db0-page3 | db1-page3 |
| ... (**order by time**) | ... (**order by time**) |

这个上一页记录的 time\_max，会作为第二页数据拉取的查询条件：

1. 将查询 order by time offset 100 limit 100，改写成 order by time where time > > $time\_max limit 100；
2. 这下不是返回 2 页数据了（“全局视野法，会改写成 offset 0 limit 200”），每个分库还是返回一页数据；
3. 服务层得到 2 页数据，内存排序，取出前 100 条数据，作为最终的第 2 页数据，这个全局的第 2 页数据，一般来说也是每个分库都包含一部分数据；
4. 如此往复，查询全局视野第 100 页数据时，不是将查询条件改写为 offset 0 limit 9900+100（返回 100 页数据），而是改写为 time > $time\_max99 limit 100（**每个分库还是返回一页数据**），以保证数据的传输量和排序的数据量不会随着不断翻页而导致性能下降。

### 方案二：允许数据精度损失

“全局视野法”能够返回业务无损的精确数据，而如果说业务不需要非常精准的数据，那这个时候就能就可以换一种方案了。

**数据库分库-数据均衡原理**

使用 partition key 进行分库，在数据量较大，数据分布足够随机的情况下，各分库所有非 partition key 属性，在各个分库上的数据分布，统计概率情况是一致的。

例如，在 uid 随机的情况下，使用 uid 取模分两库，db0 和 db1：

1. 性别属性，如果 db0 库上的男性用户占比 70%，则 db1 上男性用户占比也应为 70% ;
2. 年龄属性，如果 db0 库上 18-28 岁少女用户比例占比 15%，则 db1 上少女用户比例也应为 15% ;
3. 时间属性，如果 db0 库上每天 10:00 之前登录的用户占比为 20%，则 db1 上应该是相同的统计规律 ;

| database1 (id%2=0) | database2 (id%2=1) |
| --- | --- |
| db0-page1 | db1-page1 |
| db0-page2 | db1-page2 |
| db0-page3（**取一半**） | db1-page3（**取一半**） |
| ... (**order by time**) | ... (**order by time**) |

利用这一原理，要查询全局 100 页数据，offset 9900 limit 100 改写为 offset 4950 limit 50，每个分库偏移 4950（一半），获取 50 条数据（半页），得到的数据集的并集，基本能够认为，是全局数据的offset 9900 limit 100 的数据，**当然，这一页数据的精度，并不是精准的**。

## 3. 有没有一种技术方案，即满足业务的精确需要，又无需业务折衷，还高性能的方法呢？（经典：既要又要还要）

有没有一种技术方案，即满足业务的精确需要，又无需业务折衷，还高性能的方法呢？这就是接下来要介绍的终极武器：“二次查询法”。

为了方便举例，假设一页只有 5 条数据，查询第 200 页的 SQL 语句为 select \* from T order by time offset 1000 limit 5;

### 步骤一：查询 SQL 改写

将 select \* from T order by time offset 1000 limit 5

改写为 select \* from T order by time offset 500 limit 5

并投递给所有的分库，注意，这个 offset 的 500，来自于全局offset的总偏移量 1000，除以水平切分数据库个数 2。

如果是 3 个分库，则可以改写为 select \* from T order by time offset 333 limit 5

为了更加直观一点，我们按照 3 个分库的例子来演示，并且 time 用简单的 8 位数字来表示：

| database1 (id%3=0) | database2 (id%3=1) | database3 (id%3=2) |
| --- | --- | --- |
| 10000123 | 10000133 | 10000143 |
| 10000223 | 10000233 | 10000243 |
| 10000323 | 10000333 | 10000343 |
| 10000423 | 10000433 | 10000443 |
| 10000523 | 10000533 | 10000543 |

可以看到，每个分库都是返回的按照 time 排序的一页数据。

### 步骤二：找到返回 3 页全部数据的最小值

1. 第一个库，5 条数据的 time 最小值是 10000123；
2. 第二个库，5 条数据的 time 最小值是 10000133；
3. 第三个库，5 条数据的 time 最小值是 10000143；

| database1 (id%3=0) | database2 (id%3=1) | database3 (id%3=2) |
| --- | --- | --- |
| 10000123（**最小值**） | 10000133 | 10000143 |
| 10000223 | 10000233 | 10000243 |
| 10000323 | 10000333 | 10000343 |
| 10000423 | 10000433 | 10000443 |
| 10000523 | 10000533 | 10000543 |

这三页数据中，time 最小值来自第一个库，time\_min = 10000123，这个过程只需要比较各个分库第一条数据，时间复杂度很低。

### 步骤三：查询 SQL 二次改写第一次改写的 SQL 语句是 select \* from T order by time offset 333 limit 5 ；

第二次要改写成一个 between 语句，between 的起点是 time\_min，between 的终点是原来每个分库各自返回数据的最小值（between 是指 >= 和  data.sql
```

![1718702682524-73e6af95-9f70-4434-bd0b-4b142a6c72c7.png](images/1718702682524-73e6af95-9f70-4434-bd0b-4b142a6c72c7.png)

这里可以看到我们需要恢复的节点 position: 1023，接下来开始恢复数据：

```plsql
-- 恢复其他binlog文件数据
mysqlbinlog ./binlog.000001 ./binlog.000002 ./binlog.000003 ./binlog.000004 ./binlog.000005 ./binlog.000006 | mysql -uroot -p1qaz@WSX
-- 恢复删库跑路SQL前的数据
mysqlbinlog --stop-position=1023 ./binlog.000007 | mysql -uroot -p1qaz@WSX
```

到这里数据就已经好啦。

## 补充

```plsql
mysqldump -h192.168.75.129 -uroot -p1qaz@WSX -P3306 --single-transaction --master-data=2 --events --routines --databases test > backup.sql
```

生成了全量的备份后，直接执行 SQL 脚本。

# order by 的工作原理

日常开发中，我们经常会使用到 order by，但是你知道 order by 的工作原理吗？本文以最简单的方式带大家快速拿下 order by 的工作原理。**注意这里的 MySQL 版本为 5.7**

## 数据准备

```plsql
-- 创建用户表
CREATE TABLE `user` (
  `id` BIGINT ( 11 ) AUTO_INCREMENT COMMENT '主键id',
  `id_card` VARCHAR ( 20 ) NOT NULL COMMENT '身份证号码',
  `name` VARCHAR ( 64 ) NOT NULL COMMENT '姓名',
  `age` INT ( 4 ) NOT NULL COMMENT '年龄',
  `city` VARCHAR ( 64 ) NOT NULL COMMENT '城市',
  PRIMARY KEY ( `id`),
  INDEX idx_city ( `city` )
) ENGINE = INNODB COMMENT '员工表';

-- 插入 10 条数据
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (1, '310110190000000', 'User0', 44, 'Guangzhou');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (2, '310110190000001', 'User1', 69, 'Shenzhen');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (3, '310110190000002', 'User2', 31, 'Beijing');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (4, '310110190000003', 'User3', 45, 'Chengdu');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (5, '310110190000004', 'User4', 47, 'Shanghai');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (6, '310110190000005', 'User5', 64, 'Shenzhen');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (7, '310110190000006', 'User6', 60, 'Shanghai');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (8, '310110190000007', 'User7', 50, 'Shenzhen');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (9, '310110190000008', 'User8', 39, 'Shenzhen');
INSERT IGNORE INTO `user` (`id`, `id_card`, `name`, `age`, `city`) VALUES (10, '310110190000009', 'User9', 61, 'Guangzhou');
```

![1721050255959-f38a357f-33bb-4799-a664-5272f83a9969.png](images/1721050255959-f38a357f-33bb-4799-a664-5272f83a9969.png)

我们现在有这么一个需求：**查询前 10 个，来自深圳员工的姓名、年龄、城市，并且按照年龄小到大排序**。对应的 SQL 语句就可以这么写：

```plsql
select name,age,city from staff where city = 'shenzhen' order by age limit 10;
```

这条语句的逻辑很清楚，但是它的**底层执行流程**是怎样的呢？

## 工作原理

### explain 执行计划

我们先用**Explain**关键字查看一下执行计划

![1721113503195-aead0a99-e683-404b-88a7-f5df52b27a0d.png](images/1721113503195-aead0a99-e683-404b-88a7-f5df52b27a0d.png)

* 执行计划的**key**这个字段，表示使用到索引 idx\_city
* Extra 这个字段的 **Using index condition** 表示索引条件
* Extra 这个字段的 **Using filesort **表示用到排序

我们可以发现，这条 SQL 使用到了索引，并且也用到排序。那么它是**怎么排序**的呢？

### 全字段排序

MySQL 会给每个查询线程分配一块小**内存**，用于**排序**的，称为 **sort\_buffer**。什么时候把字段放进去排序呢，其实是通过`idx_city`索引找到对应的数据，才把数据放进去啦。

我们回顾下索引是怎么找到匹配的数据的，现在先把索引树画出来吧，**idx\_city**索引树如下：

![1721050028705-4a95a474-af70-47ff-88a6-96ecf4366e9e.png](images/1721050028705-4a95a474-af70-47ff-88a6-96ecf4366e9e.png)

idx\_city 索引树，叶子节点存储的是**主键 id**。还有一棵 id 主键聚族索引树，我们再画出聚族索引树图吧![1721050038505-d85af2e0-aa59-4c58-86d9-fbbdd06982c8.png](images/1721050038505-d85af2e0-aa59-4c58-86d9-fbbdd06982c8.png)

**我们的查询语句是怎么找到匹配数据的呢**？先通过**idx\_city**索引树，找到对应的主键 id，然后再通过拿到的主键 id，搜索**id 主键索引树**，找到对应的行数据。

加上**order by**之后，整体的执行流程就是：

1. MySQL 为对应的线程初始化**sort\_buffer**，放入需要查询的 name、age、city 字段；
2. 从**索引树 idx\_city**， 找到第一个满足 city='shenzhen’条件的主键 id，也就是图中的 id=2；
3. 到**主键 id 索引树**拿到 id=2 的这一行数据， 取 name、age、city 三个字段的值，存到 sort\_buffer；
4. 从**索引树 idx\_city** 拿到下一个记录的主键 id，即图中的 id=6；
5. 重复步骤 3、4 直到**city 的值不等于 shenzhen** 为止；
6. 前面 5 步已经查找到了所有**city 为 shenzhen** 的数据，在 sort\_buffer 中，将所有数据根据 age 进行排序；
7. 按照排序结果取前 10 行返回给客户端。

执行示意图如下：

![1721043622047-556818f1-e768-4d9f-8ebc-8a36c878bc00.png](images/1721043622047-556818f1-e768-4d9f-8ebc-8a36c878bc00.png)

将查询所需的字段全部读取到 sort\_buffer 中，就是**全字段排序**。这里面，有些小伙伴可能会有个疑问,把查询的所有字段都放到 sort\_buffer，而 sort\_buffer 是一块内存来的，如果数据量太大，sort\_buffer 放不下怎么办呢？

### 磁盘临时文件辅助排序

实际上，sort\_buffer 的大小是由一个参数控制的：**sort\_buffer\_size**。如果要排序的数据小于 sort\_buffer\_size，排序在**sort\_buffer** 内存中完成，如果要排序的数据大于 sort\_buffer\_size，则**借助磁盘文件来进行排序**

如何确定是否使用了磁盘文件来进行排序呢？可以使用以下这几个命令

```plsql
-- 打开optimizer_trace，开启统计
set optimizer_trace = "enabled=on";

-- 执行SQL语句
select name,age,city from user where city = 'shenzhen' order by age limit 10;

-- 查询输出的统计信息
select * from information_schema.optimizer_trace;
```

可以从 number\_of\_tmp\_files 中看出，是否使用了临时文件。

```json
"filesort_summary": {
  "rows": 4,
  "examined_rows": 4,
  "number_of_tmp_files": 0,
  "sort_buffer_size": 4512,
  "sort_mode": ""
}
```

number\_of\_tmp\_files 表示使用来排序的磁盘临时文件数。如果 number\_of\_tmp\_files >0，则表示使用了磁盘文件来进行排序。

使用了磁盘临时文件，整个排序过程又是怎样的呢？

1. 从**主键 Id 索引树**，拿到需要的数据，并放到 **sort\_buffer 内存**块中。当 sort\_buffer 快要满时，就对 sort\_buffer 中的数据排序，排完后，把数据临时放到磁盘一个小文件中。
2. 继续回到主键 id 索引树取数据，继续放到 sort\_buffer 内存中，排序后，也把这些数据写入到磁盘临时小文件中。
3. 继续循环，直到取出所有满足条件的数据。最后把磁盘的临时排好序的小文件，合并成一个有序的大文件。

**TPS:** 借助磁盘临时小文件排序，实际上使用的是**归并排序**算法。

小伙伴们可能会有个疑问，既然 **sort\_buffer **放不下，就需要用到临时磁盘文件，这会影响排序效率。那为什么还要把排序不相关的字段（name，city）放到 sort\_buffer 中呢？只放排序相关的 age 字段，它**不香**吗？可以了解下**rowid 排序**。

### rowid 排序

rowid 排序就是，只把查询 SQL**需要用于排序的字段和主键 id**，放到 sort\_buffer 中。那怎么确定走的是全字段排序还是 rowid 排序呢？

实际上有个参数控制的。这个参数就是 **max\_length\_for\_sort\_data**，它表示 MySQL 用于排序行数据的长度的一个参数，如果单行的长度超过这个值，MySQL 就认为单行太大，就换 rowid 排序。我们可以通过命令看下这个参数取值。

```plsql
show variables like 'max_length_for_sort_data';
```

![1721111826875-e59c6b4c-a003-4eb4-9b14-8e6f55845b19.png](images/1721111826875-e59c6b4c-a003-4eb4-9b14-8e6f55845b19.png)

**max\_length\_for\_sort\_data** 值为 1024。

而我们的示例 SQL 中 name, age, city 长度 = 64+4+64 =132 "
}
```

## 全字段排序与 rowid 排序对比

* 全字段排序：sort\_buffer 内存不够的话，就需要用到磁盘临时文件，造成**磁盘访问**。
* rowid 排序：sort\_buffer 可以放更多数据，但是需要再回到原表去取数据，比全字段排序多一次**回表**。

一般情况下，对于 InnoDB 存储引擎，会优先使**用全字段**排序。可以发现 **max\_length\_for\_sort\_data** 参数设置为 1024，这个数比较大的。一般情况下，排序字段不会超过这个值，也就是都会走**全字段**排序。


# MySQL调优实践最全!必懂!知识点一站式掌握-徐庶

# 一.索引

## ![1685538843144-1b47126c-c052-406c-b297-d4d93d9ba55c.jpeg](images/1685538843144-1b47126c-c052-406c-b297-d4d93d9ba55c.jpeg)

## 什么是索引

:::tips
💡**什么是索引？**

提到索引， 我们想到的是查询慢了 设置索引呗！但是索引为什么起作用？设置了索引为什么还是慢我们其实不是很清楚。

在关系数据库中，索引是一种数据结构，他将数据提前按照一定的规则进行排序和组织， 能够帮助快速定位到数据记录的数据，加快数据库表中数据的查找和访问速度。

像书籍的目录、文件夹、标签 、房号....  都可以帮助我们快速定位，都可以视为索引。

**能实现快速定位数据的一种存储结构，其设计思想是以空间换时间**。

:::

##  索引的种类

在MySQL中索引是在存储引擎层实现的，而不是在服务器层实现的，所以不同存储引擎具有不同的索引类型和实现。常见的索引分类如下：

* 按数据结构分类：**B+tree索引**、Hash索引、Full-text索引。
* 按物理存储分类：聚集索引、非聚集索引。
* 按字段特性分类：主键索引(PRIMARY KEY)、唯一索引(UNIQUE)、普通索引(INDEX)、全文索引(FULLTEXT)。
* 按字段个数分类：单列索引、联合索引（也叫复合索引、组合索引）。

## 常见索引数据结构和区别

```
- 二叉树、红黑树、B树 、B+树
- 区别：树的高度影响获取数据的性能（每一个树节点都是一次磁盘I/O)
```

#### ![1685543364763-54cb85a5-a824-4b46-b980-0dc0245b2c00.png](images/1685543364763-54cb85a5-a824-4b46-b980-0dc0245b2c00.png)二叉树：

特点：每个节点最多有两个子节,大在右，小在左  ，数据随机性情况下树杈越明显。

![1685362290857-b5db6cfb-1ed2-4dff-a048-54e65bbbfc80.png](images/1685362290857-b5db6cfb-1ed2-4dff-a048-54e65bbbfc80.png)![1686127709826-a8d093b1-3e0a-47f2-aee2-cd0144933cf3.png](images/1686127709826-a8d093b1-3e0a-47f2-aee2-cd0144933cf3.png)

如果数据是按顺序依次进入：

树的高度则会很高（就是一个链表结构）， 此时元素的查找效率就等于链表查询O(n)，数据检索效率将极为低下。

![1685362410423-9f0d2fd7-c4b8-49d0-880a-d7e9e4ecbc80.png](images/1685362410423-9f0d2fd7-c4b8-49d0-880a-d7e9e4ecbc80.png)![1686127737896-f85e0f98-5f64-4839-b590-2ceaca2c7fbc.png](images/1686127737896-f85e0f98-5f64-4839-b590-2ceaca2c7fbc.png)

 极端的情况下 就是一个链表结构（如下图），此时元素的查找效率就等于链表查询O(n)。

#### ![1685543364763-54cb85a5-a824-4b46-b980-0dc0245b2c00.png](images/1685543364763-54cb85a5-a824-4b46-b980-0dc0245b2c00.png)红黑树（平衡二叉树）

虽通过自旋平衡，子节点会自动分叉为2个分支，从而减少树的高度，当数据有序插入时比二叉树数据检索性能更佳.

但是如果 数据量过大，节点个数就越多，树高度也会增高（也就是树的深度越深），增加磁盘I/O次数，影响查询效率。

![1685364260410-899f3ac6-b8b2-4b91-8798-6c3ae0650ecf.gif](images/1685364260410-899f3ac6-b8b2-4b91-8798-6c3ae0650ecf.gif)

![1685370727244-9917f06b-5416-4e4c-b402-3b8f22719425.png](images/1685370727244-9917f06b-5416-4e4c-b402-3b8f22719425.png)

#### ![1685543364763-54cb85a5-a824-4b46-b980-0dc0245b2c00.png](images/1685543364763-54cb85a5-a824-4b46-b980-0dc0245b2c00.png)B-树

B树的出现可以解决树高度的问题。之所以是B树，而并不是名称中"xxx二叉树"，就是它不再限制一个父节点中只能有两个子节点，而是允许 M 个子节点（M > 2）。不仅如此，B树的一个节点可以存储多个元素，相比较于前面的那些二叉树数据结构又将整体的树高度降低了。

![1685543860080-820cb15f-005e-4c95-9342-1b9ee212cc06.png](images/1685543860080-820cb15f-005e-4c95-9342-1b9ee212cc06.png)

B 树的节点可以包含有多个字节点，所以 **B树是一棵多叉树**，它的每一个节点包含的最多子节点数量的称为B树的阶。如下图是一颗3阶的B树。

![1686139404742-42dce20d-7573-4691-a523-c25726a99255.gif](images/1686139404742-42dce20d-7573-4691-a523-c25726a99255.gif)

当一颗3阶的B树查找 7这个的元素时的流程是怎么样的？

先从根节点出发 ，判断 7在4和8之间，根据P2存储指针6的节点，判断7大于6   最后指针找到叶子节点。也就找到有匹配7的键值。

![1686140116670-212f89fe-6c14-41db-afa7-b95a9ab3e1f8.gif](images/1686140116670-212f89fe-6c14-41db-afa7-b95a9ab3e1f8.gif)

可以发现一颗3阶的B树在查找叶子节点时，由于树高度只有 3，所以查找过程最多只需要3次的磁盘I/O操作。

数据量不大时可能不太真切。但当数据量大时，节点也会随着增多；此时如果还是前面的自平衡二叉树的场景下，由于二叉树只能最多2个叶子节点的约束，也只能纵向去的去扩展子节点，树的高度会很高，意味着需要更多的操作磁盘I/O次数。而B树则可以通过横向扩展节点从而降低树的高度，所以效率自然要比二叉树效率更高。（直白说就是变矮胖了）

看到这，相信你也知道如果B树这么适合，也就没有接下来B+树的什么事了。

接着，那为什么不用B树，而用了B+树呢？

你看啊，B树其实已经满足了我们最前面所要满足的条件，减少磁盘I/O操作，同时支持按区间查找。但注意，虽然B树支持按区间查找，但并不高效。例如上面的例子中，B树能高效的通过等值查询 15 这个值，但不方便查询出一个区间内3 ~ 10区间内所有数的结果。因为当B树做范围查询时需要使用中序遍历，那么父节点和子节点也就需要不断的来回切换涉及了多个节点会给磁盘I/O带来很多负担。

#### ![1685543364763-54cb85a5-a824-4b46-b980-0dc0245b2c00.png](images/1685543364763-54cb85a5-a824-4b46-b980-0dc0245b2c00.png)B+tree索引

在MySQL中为什么会选用B+tree做索引结构呢？

B+tree 是在B树基础上的一种优化，其更适合做存储索引结构。在 B+tree 中，非叶子节点上仅存储键值，不存储数据；而所有数据记录均存储在叶子节点上，并且数据是按照顺序排列的。此外在 B+tree 中各个数据页之间是通过双向链表连接的。B+tree 的结构图如下：

![1686137513424-bd04201b-2fbb-46e8-971b-612c8cef357b.webp](images/1686137513424-bd04201b-2fbb-46e8-971b-612c8cef357b.webp)

### B树和B+树的区别，Mysql为什么要选择B+树作为默认索引的数据结构

![1686137513424-bd04201b-2fbb-46e8-971b-612c8cef357b.webp](images/1686137513424-bd04201b-2fbb-46e8-971b-612c8cef357b.webp)![1685543860080-820cb15f-005e-4c95-9342-1b9ee212cc06.png](images/1685543860080-820cb15f-005e-4c95-9342-1b9ee212cc06.png)

B+tree 结构实现数据索引具有如下优点：

a. 非叶子节点上可以存储更多的键值，相应的树的阶数（节点的子节点树）就会更大，树也就会变得更矮更胖。这样一来我们查找数据进行磁盘I/O的次数就会大大减少，数据查询的效率也会更快。

b. 所有数据记录都有序存储在叶子节点上，就会使得范围查找，排序查找，分组查找以及去重查找变得异常简单。

c. 数据页之间、数据记录之间都是通过链表链接的，有了这个结构的支持就可以方便的在数据查询后进行升序或者降序操作。

### Hash索引

Hash索引其实用的不多，最主要是因为最常见的存储引擎InnoDB不支持显示地创建Hash索引，只支持自适应Hash索引。

虽然可以使用sql语句在InnoDB显示声明Hash索引，但是其实是不生效的

![1686060089719-06591684-0765-4523-89c0-9aada91dc1b3.png](images/1686060089719-06591684-0765-4523-89c0-9aada91dc1b3.png)

对name字段建立Hash索引，但是通过show index from 表名就会发现实际还是B+树

![1686060089699-2d9db32b-569d-4d7d-a2ae-05634adb429c.png](images/1686060089699-2d9db32b-569d-4d7d-a2ae-05634adb429c.png)

在存储引擎中，Memory引擎支持Hash索引

Hash索引其实有点像Java中的HashMap底层的数据结构，他也有很多的槽，存的也是键值对，键值为索引列，值为数据的这条数据的行指针，通过行指针就可以找到数据

假设现在user表用Memory存储引擎，对name字段建立Hash索引，表中插入三条数据

![1686060089667-49ca8a48-b8f3-49a2-9e04-0161ffcae253.png](images/1686060089667-49ca8a48-b8f3-49a2-9e04-0161ffcae253.png)

Hash索引会对索引列name的值进行Hash计算，然后找到对应的槽下面，如下图所示

![1686060089633-aa383d2c-2224-40d9-bfab-b2de18802fbd.png](images/1686060089633-aa383d2c-2224-40d9-bfab-b2de18802fbd.png)

当遇到name字段的Hash值相同时，也就是Hash冲突，就会形成一个链表，比如有name=张三有两条数据，就会形成一个链表。

之后如果要查name=李四的数据，只需要对李四进行Hash计算，找到对应的槽，遍历链表，取出name=李四对应的行指针，然后根据行指针去查找对应的数据。

**Hash索引优缺点**

* hash索引只能用于等值比较，所以查询效率非常高
* 不支持范围查询，也不支持排序，因为索引列的分布是无序的

## 什么是聚簇索引与非聚集索引和区别？

按物理存储分类：InnoDB的存储方式是聚集索引，MyISAM的存储方式是非聚集索引。

![1686226684967-bf5d2cbf-ccfb-4640-a1f4-edb242add589.png](images/1686226684967-bf5d2cbf-ccfb-4640-a1f4-edb242add589.png)

![1686226761004-b46d21b0-c48f-4010-a246-b47b1f28c143.png](images/1686226761004-b46d21b0-c48f-4010-a246-b47b1f28c143.png)

#### 聚簇索引

1. 聚簇索引将数据存储在索引树的叶子节点上。
2. 聚簇索引可以减少一次查询，因为查询索引树的同时就能获取到数据。
3. 聚簇索引的缺点是，对数据进行修改或删除操作时需要更新索引树，会增加系统的开销。
4. 聚簇索引通常用于数据库系统中，主要用于提高查询效率。

#### 非聚簇索引（又称二级索引 /  辅助索引）

1. 非聚簇索引不将数据存储在索引树的叶子节点上，而是存储在数据页中。
2. 非聚簇索引在查询数据时需要两次查询，一次查询索引树，获取数据页的地址，再通过数据页的地址查询数据（**通常情况下来说是的，但如果索引覆盖的话实际上是不用回表的**）。
3. 非聚簇索引的优点是，对数据进行修改或删除操作时不需要更新索引树，减少了系统的开销。
4. 非聚簇索引通常用于数据库系统中，主要用于提高数据更新和删除操作的效率。

##

## 二级索引

在MySQL中，创建一张表时会默认为主键创建聚簇索引，B+树将表中所有的数据组织起来，即数据就是索引主键所以在InnoDB里，主键索引也被称为聚簇索引，索引的叶子节点存的是整行数据。而除了聚簇索引以外的所有索引都称为二级索引，二级索引的叶子节点内容是主键的值。

```sql
例如创建如下一张表:

CREATE TABLE users(
  id INT NOT NULL,
  name VARCHAR(20) NOT NULL,
  age INT NOT NULL,
  PRIMARY KEY(id)
);
新建一个以age字段的二级索引:

ALTER TABLE users ADD INDEX index_age(age);
MySQL会分别创建主键id的聚簇索引和age的二级索引:
```

![1686228312805-5256f72b-5055-4545-963a-95ce7aa145dc.webp](images/1686228312805-5256f72b-5055-4545-963a-95ce7aa145dc.webp)

在MySQL中主键索引的叶子节点存的是整行数据，而二级索引叶子节点内容是主键的值.

## 回表

讲完二级索引，接下来讲一讲如何使用二级索引查找数据。

这里假设对name字段创建了一个索引，并且表里就存了上面示例中的几条数据，这里我再把图拿过来

例如执行下面这条sql 则需要进行回表:

```plain
SELECT * FROM users WHERE age=35;
```

![1686228330541-4a9c644c-2572-4b8a-b2e1-c9dbaa37dfb5.webp](images/1686228330541-4a9c644c-2572-4b8a-b2e1-c9dbaa37dfb5.webp)

整个过程大致分为以下几个步骤：

*
* 从根节点开始，21 '王五' and age > 22;
```

在MySQL5.6(不包括5.6)之前，整个sql大致执行步骤如下：

* 先根据二分查找，定位到name > '王五'的第一条数据，也就是id=4的那个赵六
* 之后就会根据id=4进行回表操作，到聚簇索引中查找id=4其它字段的数据，然后判断数据中的age是否大于22，是的话就说明是我们需要查找的数据，否则就不是
* 之后顺着链表，继续遍历，然后找到一条记录就回一次表，然后判断age，如此反复下去，直至结束

所以对于图上所示，整个搜索过程会经历5次回表操作，两个赵六，两个刘七，一个王九，最后符合条件的也就是id=6的赵六那条数据，其余age不符和。

虽然这么执行没什么问题，但是不知有没有发现其实没必要进行那么多次回表，因为光从上面的索引图示就可以看出，符合name > '王五' and age > 22的数据就id=6的赵六那条数据

所以在MySQL5.6之后，对上面的age > 22判断逻辑进行了优化

前面还是一样，定位查找到id=4的那个赵六，之后就**不回表**来判断age了，因为索引列有age的值了，那么直接根据索引中age判断是否大于22，如果大于的话，再回表查询剩余的字段数据（因为是select \*），然后再顺序链表遍历，直至结束

所以这样优化之后，回表次数就成1了，相比于前面的5次，大大减少了回表的次数。

而这个优化，就被称为**索引下推**，就是为了减少回表的次数。

之所以这个优化叫索引下推，其实是跟判断age > 22逻辑执行的地方有关，这里就不过多赘述了。

## 索引合并

索引合并（index merge）是从MySQL5.1开始引入的索引优化机制，在之前的MySQL版本中，一条sql多个查询条件只能使用一个索引，但是引入了索引合并机制之后，MySQL在**某些特殊**的情况下会扫描多个索引，然后将扫描结果进行合并

结果合并会为下面三种情况：

* 取交集（intersect）
* 取并集（union）
* 排序后取并集（sort-union）

为了不耽误演示，删除之前所有的索引，然后为name和age各自分别创建一个二级索引idx\_name和idx\_age

#### 取交集（intersect）

当执行下面这条sql就会出现取交集的情况

```plain
select * from `user` where name = '赵六' and age= 22;
```

查看执行计划

![1686060427143-0d4fe61f-28b1-4407-b501-4c25a61055db.png](images/1686060427143-0d4fe61f-28b1-4407-b501-4c25a61055db.png)

type是index\_merge，并且possible\_key和key都是idx\_name和idx\_age，说明使用了索引合并，并且Extra有Using intersect(idx\_age,idx\_name)，intersect就是交集的意思。

整个过程大致是这样的，分别根据idx\_name和idx\_age取出对应的主键id，之后将主键id取交集，那么这部分交集的id一定同时满足查询name = '赵六' and age= 22的查询条件（仔细想想），之后再根据交集的id回表

不过要想使用取交集的联合索引，需要满足各自索引查出来的主键id是排好序的，这是为了方便可以快速的取交集

比如下面这条sql就无法使用联合索引

```plain
select * from `user` where name = '赵六' and age > 22;
```

![1686060427441-ebaf070f-dfb3-4163-afc8-2370954bc3cc.png](images/1686060427441-ebaf070f-dfb3-4163-afc8-2370954bc3cc.png)

只能用name这个索引，因为age > 22查出来的id是无序的，前面在讲索引的时候有说过索引列的排序规则

由此可以看出，使用联合索引条件还是比较苛刻的。

#### 取并集（union）

取并集就是将前面例子中的and换成or

```plain
select * from `user` where name = '赵六' or age = 22;
```

前面执行的情况都一样，根据条件到各自的索引上去查，之后对查询的id取并集去重，之后再回表

同样地，取并集也要求各自索引查出来的主键id是排好序的，如果查询条件换成age > 22时就无法使用取并集的索引合并

```plain
select * from `user` where name = '赵六' or age > 22;
```

#### 排序后取并集（sort-union）

虽然取并集要求各自索引查出来的主键id是排好序的，但是如果遇到没排好序的情况，mysql会自动对这种情况进行优化，会先对主键id排序，然后再取并集，这种情况就叫 排序后取并集（sort-union）。

比如上面提到的无法直接取并集的sql就符合排序后取并集（sort-union）这种情况

select \* from `user` where name = '赵六' or age > 22;

## 为什么Mysql默认 InnoDB, 而不是 MyISAM ？

**MyISAM 与 InnoDB**

众所周知，MySQL 有两种常见的存储引擎。一种是 MyISAM，一种是 InnoDB。

***一、它们是什么？***

先来看看官网对 MyISAM 的描述，只有一句话，看来官方也不想多加解释。

MyISAM is based on the older (and no longer available) ISAM storage engine but has many useful extensions.

大意：MyISAM 是一款青出于蓝而胜于蓝的存储引擎，它在 ISAM 基础上作了一些扩展和加工。关于 ISAM ，我只告诉你它是 Indexed Sequential Access Method 的缩写，翻译为“有索引的顺序访问方法”。

而对 [InnoDB](https://link.juejin.cn/?target=https%3A%2F%2Fdev.mysql.com%2Fdoc%2Frefman%2F8.0%2Fen%2Finnodb-introduction.html) 的描述，就更 professional 一些了。

:::info InnoDB is a general-purpose storage engine that balances high reliability and high performance. In MySQL 8.0, InnoDB is the default MySQL storage engine. Unless you have configured a different default storage engine, issuing a CREATE TABLE statement without an ENGINE= clause creates an InnoDB table.

:::

大意：InnoDB 是一种通用的存储引擎，在高可靠和高性能上作了均衡。MySQL 8.0 中，它是默认的存储引擎（其实在5.5之后的版本就是了），当你执行 CREATE TABLE 建表语句并且不带 “ENGINE = ”子句时，默认帮你创建的就是 InnoDB 表了。

***二、两者有什么区别？***

拿官网两者的 Features 来作一个分析对比吧：

![1685885295850-cd6ca510-c34c-4c9a-8ca9-eae76c17a224.png](images/1685885295850-cd6ca510-c34c-4c9a-8ca9-eae76c17a224.png)

![1685885420022-adfd96b6-33c8-4310-b4b3-939e298fa958.png](images/1685885420022-adfd96b6-33c8-4310-b4b3-939e298fa958.png)

1、InnoDB 是聚集索引，数据文件是和索引绑在一起的，必须要有主键，通过主键索引效率很高，但是辅助索引需要两次查询，先查询到主键，然后再通过主键查询到数据。因此，主键不应该过大，否则其他索引也会很大。而 MyISAM 是非聚集索引，数据文件是分离的，索引保存的是数据文件的指针，主键索引和辅助索引是独立的。

2、InnoDB 支持外键，而 MyISAM 不支持。对一个包含外键的 InnoDB 表转为 MYISAM 会失败。

3、InnoDB 在 MySQL 5.6 之前不支持全文索引，而 MyISAM 一直都支持，如果你用的是老版本，查询效率上 MyISAM 要高。

4、InnoDB 锁粒度是行锁，而 MyISAM 是表锁。

5、InnoDB 支持事务，MyISAM 不支持，对于 InnoDB 每一条 SQL 语言都默认封装成事务，自动提交，这样会影响速度，所以最好把多条 SQL 语言放在 begin 和 commit 之间，组成一个事务。

6、InnoDB 不保存表的具体行数，执行 select count(\*) from table 时需要全表扫描。而 MyISAM 用一个变量保存了整个表的行数，执行上述语句时只需要读出该变量即可，速度很快，但如果上述语句还包含了 where 子句，那么两者执行效率是一样的。

[https://blogs.oracle.com/mysql/post/still-using-myisam-it-is-time-to-switch-to-innodb](https://blogs.oracle.com/mysql/post/still-using-myisam-it-is-time-to-switch-to-innodb)

[https://tecadmin.net/choosing-between-innodb-myisam-and-memory-storage-engines/](https://tecadmin.net/choosing-between-innodb-myisam-and-memory-storage-engines/)

[http://dimitrik.free.fr/blog/archives/2015/12/mysql-performance-revisiting-innodb-vs-myisam-with-mysql-57.html](http://dimitrik.free.fr/blog/archives/2015/12/mysql-performance-revisiting-innodb-vs-myisam-with-mysql-57.html)

## 如果一个表没有主键索引那还会创建B+树吗？

**答案是会的！！！**

如果表没有明确的主键索引，InnoDB会使用一个隐藏的、自动生成的主键来创建索引。这个隐藏的主键索引使用的就是B+树结构。因此，在InnoDB中，即使表没有明确的主键索引，也会创建一个B+树索引。

## 索引的优缺点，什么时候该用和不该用

优点：

1. 提高检索效率

2. 降低排序成本，索引对应的字段是会有一个自动排序功能的，默认是升序asc。

 它缺点是

1. 创建索引和维护索引要耗费时间，这种时间随着数据量的增加而增加。
2. 索引需要占用物理空间，数据量越大，占用空间越大
3. 会降低表的增删改的效率，因为每次增删改索引，都需要进行动态维护

### 竟然索引有坏有好，什么时候需要索引，什么时候不需要？

适合：

1. 较频繁的作为查询条件的字段应该创建索引

不适合：

1. 字段值的唯一性太差不适合单独做索引

2. 更新非常频繁的字段不适合

3. 不会出现在where句中的字段不适合。

# 二.优化

## 1、优化方法

![1685889373587-181e5819-b6b7-44d4-bdcb-98f3e425ecab.png](images/1685889373587-181e5819-b6b7-44d4-bdcb-98f3e425ecab.png)

关于SQL优化方法，包括5点

1）创建索引减少扫描量；

2）调整索引减少计算量；

3）索引覆盖（减少不必访问的列，避免回表查询）；

4）干预执行计划；

5）SQL改写；

## 2、通过Explain干预执行计划

[画板]

### 1.Explain含义

Explain是 SQL 分析工具中非常重要的一个功能，它可以模拟优化器执行查询语句，帮助我们理解查询是如何执行的；分析查询执行计划可以帮助我们发现查询瓶颈，优化查询性能。

### 2.Explain作用

* 表的读取顺序
* SQL执行时查询操作类型
* 可以使用哪些索引
* 实际使用哪些索引
* 每张表有多少行记录被扫描
* **SQL语句性能分析**

### 3.Explain用法

```sql
drop table orders;
drop table products;
drop table users;
CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  email VARCHAR(100) NOT NULL,
  password VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE products (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  price FLOAT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE orders (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  order_date DATETIME NOT NULL,
  total_price FLOAT NOT NULL,
  product_id INT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

alter table users add index index_name_email (name,email);

INSERT INTO users (name, email, password)
VALUES ('张三', 'zhangsan@example.com', 'password123'),
('李四', 'lisi@example.com', 'password123'),
('王五', 'wangwu@example.com', 'password123'),
('赵六', 'zhaoli@example.com', 'password123'),
('钱七', 'qianqi@example.com', 'password123');

INSERT INTO products (name, price)
VALUES ('产品 1', 10.00),
('产品 2', 15.00),
('产品 3', 20.00),
('产品 4', 12.00),
('产品 5', 18.00);

INSERT INTO orders (user_id, order_date, total_price, product_id)
VALUES (1, '2023-02-18 10:00:00', 100.00, 1),
(2, '2023-02-18 11:00:00', 50.00, 2),
(3, '2023-02-18 12:00:00', 20.00, 3),
(4, '2023-02-18 13:00:00', 15.00, 4),
(5, '2023-02-18 14:00:00', 25.00, 5);
```

MySQL5.7版本之前，使用Explain Extended在Explain的基础上额外多返回filtered列与extra列；

```sql
Explain Extended select * from users;
```

MySQL5.7版本之前，使用Explain Partitions在Explain的基础上额外多返回partitions列；

```sql
Explain Partitions select * from users;
```

MySQL5.7版本引入了这两个特性，直接使用Explain关键字可以将partitions列、filtered列、extra列直接查询出来。

```sql
Explain select * from users;
```

![1681024592949-53b352d8-76bb-48c2-b08c-3b333147be4c.png](images/1681024592949-53b352d8-76bb-48c2-b08c-3b333147be4c.png)

Explain语句返回列的各列含义：

| **列名** | **含义** |
| --- | --- |
| id | 每个select都有一个对应的id号，并且是从1开始自增的 |
| select\_type | 查询语句执行的查询操作类型 |
| table | 表名 |
| partitions | 表分区情况 |
| type | 查询所用的访问类型 |
| possible\_keys | 可能用到的索引 |
| key | 实际查询用到的索引 |
| key\_len | 所使用到的索引长度 |
| ref | 使用到索引时，与索引进行等值匹配的列或者常量 |
| rows | 预计扫描的行数（索引行数或者表记录行数） |
| filtered | 表示符合查询条件的数据百分比 |
| Extra | SQL执行的额外信息 |

这些查询列大家先留一个印象，后续会详细讲解。

### 4.Explain返回列详解

接下来我们将展示Explain中每个列的信息

#### 1. id列：每个select都有一个对应的id号，并且是从1开始自增的。

* 如果id序号相同，从上往下执行。
* 如果id序号不同，序号大先执行。
* 如果两种都存在，先执行序号大，在同级从上往下执行。
* 如果显示NULL，最后执行。表示结果集，并且不需要使用它来进行查询。

```sql
explain
SELECT users.name, orders.total_price, products.price
FROM users
INNER JOIN orders ON users.id = orders.user_id
INNER JOIN products ON orders.product_id = products.id;
```

![1681026719178-e164f36f-c6ea-476b-9ebe-c8d3a86763b6.png](images/1681026719178-e164f36f-c6ea-476b-9ebe-c8d3a86763b6.png)

```sql
explain
select * from orders where product_id =  (select id from products where products.price = 10);
```

![1681111885827-f385c7dc-fd67-4213-9911-90b9b1a5b4a8.png](images/1681111885827-f385c7dc-fd67-4213-9911-90b9b1a5b4a8.png)

```sql
set session optimizer_switch='derived_merge=off'; #关闭MySQL5.7对衍生表合并优化

explain
select orders.*
from (select id from products) as temp inner join orders on temp.id = orders.product_id;

set session optimizer_switch='derived_merge=on'; #还原配置
```

![1681026768642-9a4aeb47-5788-4346-8112-5aa54d51d4a6.png](images/1681026768642-9a4aeb47-5788-4346-8112-5aa54d51d4a6.png)

```sql
explain
select id from users
union
select id from products;
```

![1681026786538-8a937cef-7daf-4409-a8a9-84364f426702.png](images/1681026786538-8a937cef-7daf-4409-a8a9-84364f426702.png)

优化器会针对子查询进行一定的优化重写SQL：

```plain
EXPLAIN select * from users WHERE id in (select user_id from orders where id = 1);
show WARNINGS;
```

#### 2.select\_type列：表示查询语句执行的查询操作类型

##### 2.1.simple：简单select，不包括union与子查询

```sql
Explain select * from users;
```

![1681025521715-b8ce528b-f4ab-44fb-a088-90fa8f8dded2.png](images/1681025521715-b8ce528b-f4ab-44fb-a088-90fa8f8dded2.png)

```sql
Explain select * from users inner join orders on users.id = orders.user_id;
```

![1681287552178-bd66eaa3-6e70-4d2a-a39f-83ff9925fad9.png](images/1681287552178-bd66eaa3-6e70-4d2a-a39f-83ff9925fad9.png)

##### 2.2.primary：复杂查询中最外层查询，比如使用union或union all时，id为1的记录select\_type通常是primary

```sql
explain
select id from users
union
select id from products;
```

![1681272527877-5ee1cd39-0abc-4406-b23a-7fbd91755d8b.png](images/1681272527877-5ee1cd39-0abc-4406-b23a-7fbd91755d8b.png)

##### 2.3.subquery：指在 select 语句中出现的子查询语句,结果不依赖于外部查询（不在from语句中）

```sql
explain
select orders.*,(select name from products where id = 1) from orders;
```

![1681029309790-04cfe1df-d34b-4a1c-81e4-0a3293e57a15.png](images/1681029309790-04cfe1df-d34b-4a1c-81e4-0a3293e57a15.png)

##### 2.4.dependent subquery：指在 select 语句中出现的查询语句，结果依赖于外部查询

```sql
explain
select orders.*,(select name from products where products.id = orders.user_id) from orders;
```

![1681047335693-594d517a-7107-4554-8b28-64401c62e334.png](images/1681047335693-594d517a-7107-4554-8b28-64401c62e334.png)

##### 2.5.derived：派生表，在FROM子句的查询语句，表示从外部数据源中推导出来的，而不是从 SELECT 语句中的其他列中选择出来的。

```sql
set session optimizer_switch='derived_merge=off'; #关闭MySQL5.7对衍生表合并优化

explain
select * from (select user_id from orders where id = 1) as temp;

set session optimizer_switch='derived_merge=on'; #还原配置
```

![1681272573191-8078286f-8374-44fe-a1a0-668f7ccb7fac.png](images/1681272573191-8078286f-8374-44fe-a1a0-668f7ccb7fac.png)

##### 2.6.union：分union与union all两种，若第二个select出现在union之后，则被标记为union；如果union被from子句的子查询包含，那么第一个select会被标记为derived；union会针对相同的结果集进行去重，union all不会进行去重处理。

```sql
explain
select * from (
select id from products where price = 10
union
select id from orders where user_id in (1,2)
union
select id from users where name = '张三' ) as temp;
```

![1681305655206-41e7f35a-3d2d-4169-9a70-cc752e4186c9.png](images/1681305655206-41e7f35a-3d2d-4169-9a70-cc752e4186c9.png)

```sql
explain
select * from (
select id from products where price = 10
union all
select id from orders where user_id in (1,2)
union all
select id from users where name = '张三' ) as temp;
```

![1681289909665-76752c8e-9661-4806-b1cf-516ec8b33bad.png](images/1681289909665-76752c8e-9661-4806-b1cf-516ec8b33bad.png)

##### 2.7.dependent union：当union作为子查询时，其中第一个union为dependent subquery，第二个union为dependent union。

```sql
explain
select * from orders where id in (
select id from products where price = 10
union
select id from orders where user_id = 2
union
select id from users where name = '张三' );
```

![1681289864894-93092296-3304-4d99-9ff7-3fbe4bc0a1a0.png](images/1681289864894-93092296-3304-4d99-9ff7-3fbe4bc0a1a0.png)

##### 2.8.union result：如果两个查询中有相同的列，则会对这些列进行重复删除，只保留一个表中的列。

```sql
explain
select id from users
union
select id from products;
```

![1681272681693-656c2b09-74ec-4876-bd22-f246659f556b.png](images/1681272681693-656c2b09-74ec-4876-bd22-f246659f556b.png)\
![1681029933432-692c9a82-c2b5-4b2e-890f-903dc58bec27.png](images/1681029933432-692c9a82-c2b5-4b2e-890f-903dc58bec27.png)

#### 3.table列：查询所涉及的表名。如果有多个表，将显示多行记录

#### 4.partitions列：表分区情况

查询语句所涉及的表的分区情况。具体来说，它会显示出查询语句在哪些分区上执行，以及是否使用了分区裁剪等信息。如果没有分区，该项为NULL。

#### 5.type列：查询所使用的访问类型

效率从高到低分别为：**system > const > eq\_ref > ref** > fulltext > ref\_or\_null \*\*> range > index > ALL，\*\*一般来说保证range级别，最好能达到ref级别。

##### 5.1.system：const类型的一种特殊场景，查询的表只有一行记录的情况，并且该表使用的存储引擎的统计数据是精确的

InnoDb存储引擎的统计数据不是精确的，虽然只有一条数据但是type类型为ALL；

```sql
DROP TABLE t;
CREATE TABLE t(i INT) ENGINE=InnoDb;
INSERT INTO t VALUES(1);
explain select * from t;
```

![1681365781705-5ee3b302-7e4c-40ed-94a8-72759b980e92.png](images/1681365781705-5ee3b302-7e4c-40ed-94a8-72759b980e92.png)

Memory存储引擎的统计数据是精确的，所以当只有一条记录的时候type类型为system。

```sql
DROP TABLE tt;
CREATE TABLE tt(i INT) ENGINE=memory;
INSERT INTO tt VALUES(1);
explain select * from tt;
```

![1681368181258-8eb20a57-c719-4756-afc6-1f0ec8a72ad2.png](images/1681368181258-8eb20a57-c719-4756-afc6-1f0ec8a72ad2.png)

##### 5.2.const：基于主键或唯一索引查看一行，当MySQL对查询某部分进行优化，并转换为一个常量时，使用这些类型访问转换成常量查询，效率高

```sql
explain
select * from orders where id = 1;
```

![1681366253574-0fa5ca6c-2d64-40f0-9a01-2454c736e53a.png](images/1681366253574-0fa5ca6c-2d64-40f0-9a01-2454c736e53a.png)

##### 5.3.eq\_ref：基于主键或唯一索引连接两个表，对于每个索引键值，只有一条匹配记录，被驱动表的类型为'eq\_ref'

```sql
explain
select users.* from users inner join orders on users.id = orders.id;
```

![1681366272461-a8f66d17-3156-448c-97c5-d9421863ebb1.png](images/1681366272461-a8f66d17-3156-448c-97c5-d9421863ebb1.png)

##### 5.4.ref：基于非唯一索引连接两个表或通过二级索引列与常量进行等值匹配，可能会存在多条匹配记录

1.关联查询，使用非唯一索引进行匹配。

```sql
explain
select users.* from users inner join orders on users.id = orders.user_id;
```

![1681366725970-346f1c6a-4c3c-4076-a06a-239a9f1c28f7.png](images/1681366725970-346f1c6a-4c3c-4076-a06a-239a9f1c28f7.png)\
2.简单查询，使用二级索引列匹配。

```sql
explain
select * from orders where user_id = 1;
```

![1681366311397-1eb1ba55-cb00-464b-b3c8-2949bd18a718.png](images/1681366311397-1eb1ba55-cb00-464b-b3c8-2949bd18a718.png)

##### 5.5.range：使用非唯一索引扫描部分索引，比如使用索引获取某些范围区间的记录

```sql
explain
select * from orders where user_id > 3;
```

![1681366328856-b4f80e75-c7d3-40c7-a2c7-21c53c900bfb.png](images/1681366328856-b4f80e75-c7d3-40c7-a2c7-21c53c900bfb.png)

##### 5.6.index：扫描整个索引就能拿到结果，一般是二级索引，这种查询一般为使用覆盖索引（需优化，缩小数据范围）

```sql
explain
select user_id from orders;
```

![1681366836249-8d05dc8f-5859-467d-ac77-d5d95a7201ef.png](images/1681366836249-8d05dc8f-5859-467d-ac77-d5d95a7201ef.png)

##### 5.7.all：扫描整个表进行匹配，即扫描聚簇索引树（需优化，添加索引优化）

```sql
explain
select * from users;
```

![1681039103901-8b407ac2-cdb5-44c1-b3e4-3f35818907a7.png](images/1681039103901-8b407ac2-cdb5-44c1-b3e4-3f35818907a7.png)

##### 5.8.NULL：MySQL在优化过程中分解语句就已经可以获取到结果，执行时甚至不用访问表或索引。

```sql
explain
select min(id) from users;
```

![1681039399639-75db39c7-cf2f-49c0-92fb-b00364a29c8d.png](images/1681039399639-75db39c7-cf2f-49c0-92fb-b00364a29c8d.png)

#### 6.possible\_keys列：表示在查询中可能使用到某个索引或多个索引；如果没有选择索引，显示NULL

#### 7.key列：表示在查询中实际使用的索引，如果没有使用索引，显示NULL。

#### 8.key\_len列：表示当优化器决定使用某个索引执行查询时，该索引记录的最大长度（主要使用在联合索引）

联合索引可以通过这个值算出具体使用了索引中的哪些列。

使用单例索引：

```sql
explain
select * from users where id = 1;
```

![1681384753103-94604447-d2b6-49bb-bc4c-23c14b1a076b.png](images/1681384753103-94604447-d2b6-49bb-bc4c-23c14b1a076b.png)

使用联合索引：

```sql
explain
select * from users where name = '张三' and email = 'zhangsan@example.com';
```

![1681043991351-f81c0cc8-6968-40b2-9e4b-f8163585d542.png](images/1681043991351-f81c0cc8-6968-40b2-9e4b-f8163585d542.png)\
计算规则：

* 字符串：

char(n)：n个字节 

varchar(n)：如果是uft-8：3n+2字节，加的2个字节存储字符串长度。如果是utf8mb4：4n+2字节。

* 数值类型：

tinyint：1字节

smaillint：2字节

int：4字节

bigint：8字节

* 时间类型：

date：3字节

timestamp：4字节

datetime：8字节\
字段如果为NULL，需要1个字节记录是否为NULL

#### ![1686491522804-98efd37f-1489-4202-8b36-51c2fdafa9c2.png](images/1686491522804-98efd37f-1489-4202-8b36-51c2fdafa9c2.png)

#### 9.ref列：表示将哪个字段或常量和key列所使用的字段进行比较。

当使用索引列等值查询时，与索引列进行等值匹配的对象信息。

1.常量：

```sql
explain
select * from users where name = '张三' and email = 'zhangsan@example.com';
```

![1681447679631-4023e7e4-924b-45d9-97bc-a3015f5e2e89.png](images/1681447679631-4023e7e4-924b-45d9-97bc-a3015f5e2e89.png)

2.字段：

```sql
explain
select users.* from users inner join orders on users.id = orders.id;
```

![1681446642630-3813f19b-6e70-49d4-82da-12f4fdb00754.png](images/1681446642630-3813f19b-6e70-49d4-82da-12f4fdb00754.png)

3.函数

```sql
explain
select users.* from users inner join orders on users.id = trim(orders.id);
```

![1681454629742-f28fd829-b9e5-4e5e-9488-9d29f3faba65.png](images/1681454629742-f28fd829-b9e5-4e5e-9488-9d29f3faba65.png)

#### 10.rows列：全表扫描时表示需要扫描表的行数估计值；索引扫描时表示扫描索引的行数估计值；值越小越好（不是结果集中的行数）

1.全表扫描

```sql
explain
select * from orders where user_id >= 3 and total_price = 25;
```

![1681449747200-d5473ed5-9cec-4ad0-b696-afc1c1427bc3.png](images/1681449747200-d5473ed5-9cec-4ad0-b696-afc1c1427bc3.png)

2.索引扫描

```sql
explain
select * from orders where user_id > 3;
```

![1681449133838-d210e8ea-6a40-4ccb-8ac3-c4d810032f1c.png](images/1681449133838-d210e8ea-6a40-4ccb-8ac3-c4d810032f1c.png)

#### 11.filtered列：表示符合查询条件的数据百分比。可以使用rows \* filtered/100计算出与\*\*explain\*\*前一个表进行连接的行数。

前一个表指 explain 中的id值比当前表id值小的表，id相同的时候指后执行的表。

```sql
explain
select users.* from users inner join orders on users.id = orders.id;
```

![1681449894480-5b14d3bf-04ee-450b-bdf8-150cfa66ec57.png](images/1681449894480-5b14d3bf-04ee-450b-bdf8-150cfa66ec57.png)

#### 12.Extra列：SQL执行查询的一些额外信息

##### 12.1.Using Index：使用非主键索引树就可以查询所需要的数据。一般是覆盖索引，即查询列都包含在辅助索引树叶子节点中，不需要回表查询。

```sql
explain
select user_id,id from orders where user_id = 1;
```

![1681044775275-6a7736f1-9b4a-4d35-ba85-dbedd53e6823.png](images/1681044775275-6a7736f1-9b4a-4d35-ba85-dbedd53e6823.png)

##### 12.2.Using where：不通过索引查询所需要的数据

```sql
explain
select * from orders where total_price = 100;

explain
select * from orders where user_id = 1 and total_price = 100;
```

![1681044854093-370ad425-71a6-4008-b7be-55467d1c9251.png](images/1681044854093-370ad425-71a6-4008-b7be-55467d1c9251.png)

##### 12.3.Using index condition：表示查询列不被索引覆盖，where 条件中是一个索引范围查找，过滤完索引后回表找到所有符合条件的数据行。

```sql
explain
select * from orders where user_id > 3;
```

![1681045567332-67e9a87a-1b04-4693-b226-f427bc53fc45.png](images/1681045567332-67e9a87a-1b04-4693-b226-f427bc53fc45.png)

##### 12.4.Using temporary：表示需要使用临时表来处理查询；

1.total\_price列无索引，需要创建一张临时表进行去重

```sql
explain
select distinct total_price from orders;
```

![1681045772656-8572b080-7051-4df2-8625-980f54c5771a.png](images/1681045772656-8572b080-7051-4df2-8625-980f54c5771a.png)\
2.name列有联合索引

```sql
explain
select distinct name from users;
```

![1681046236030-f805a8ac-1946-4600-a5b9-6bf583f5e39e.png](images/1681046236030-f805a8ac-1946-4600-a5b9-6bf583f5e39e.png)

##### 12.5.Using filesort：当查询中包含 order by 操作而且无法利用索引完成的排序操作，数据较少时从内存排序，如果数据较多需要在磁盘中排序。	需优化成索引排序。

1.total\_price列无索引，无法通过索引进行排序。需要先保存total\_price与对应的主键id，然后在排序total\_price查找数据。

```sql
explain
select total_price from orders order by total_price;
```

![1681464127193-d83100a9-f5c3-4139-a8d0-7225ec490e8f.png](images/1681464127193-d83100a9-f5c3-4139-a8d0-7225ec490e8f.png)\
2.name列有索引，因索引已经是排好序的所以直接读取就可以了。

```sql
explain
select name from users order by name;
```

![1681474747964-b0738d83-519e-4e6e-a649-d3ac167a7d5e.png](images/1681474747964-b0738d83-519e-4e6e-a649-d3ac167a7d5e.png)

##### 12.6.Select tables optimized away：使用某些聚合函数（min,max）来访问某个索引值。

```sql
explain
select min(id) from users;

explain
select min(password) from users;
```

![1681039399639-75db39c7-cf2f-49c0-92fb-b00364a29c8d.png](images/1681039399639-75db39c7-cf2f-49c0-92fb-b00364a29c8d.png)

###

## 3.索引优化最佳实践

示例表：

```abap
CREATE TABLE `employees` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(24) NOT NULL DEFAULT '' COMMENT '姓名',
  `age` int(11) NOT NULL DEFAULT '0' COMMENT '年龄',
  `position` varchar(20) NOT NULL DEFAULT '' COMMENT '职位',
  `hire_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入职时间',
  `remark` varchar(255) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`),
  KEY `idx_name_age_position` (`name`,`age`,`position`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8 COMMENT='员工记录表';

INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (2, '张三', 18, 'beijing', '2023-06-11 20:51:35', '测试');
INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (3, '张三', 23, 'shanghai', '2023-06-11 20:51:35', '测试2');
INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (1, '李四', 20, 'shanghai', '2023-06-11 20:51:35', '测试3');
INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (5, '王五', 19, 'beijing', '2023-06-12 14:32:15', NULL);
INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (4, '赵六', 22, 'shenzheng', '2023-06-12 14:33:00', NULL);
INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (6, '赵六', 24, 'beijing', '2023-06-12 14:37:50', NULL);
INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (7, '刘七', 20, 'shanghai', '2023-06-12 14:38:27', NULL);
INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (8, '刘七', 22, 'beijing', '2023-06-12 14:38:41', NULL);
INSERT INTO `test`.`employees`(`id`, `name`, `age`, `position`, `hire_time`, `remark`) VALUES (9, '王九', 9, 'shanghai ', '2023-06-12 14:40:17', NULL);

```

#### 1.全值匹配

MySQL全值匹配是指在使用复合索引时，查询条件要包含索引的所有列，才能最大程度地利用索引。

```sql
EXPLAIN SELECT * FROM employees WHERE name= '张三';
```

查看索引长度是74=(3\*24+2),可以算出联合索引中只使用了name前缀索引.

![1686058000736-c2814e2e-425f-47fa-ae6e-b8d7c1abef87.png](images/1686058000736-c2814e2e-425f-47fa-ae6e-b8d7c1abef87.png)

```sql
EXPLAIN SELECT * FROM employees WHERE name= '张三' AND age = 18;
```

查看索引长度是78=(3\*24+2)+4,可以算出联合索引中只使用了name和age前缀索引.

![1686058010089-64bd6184-680e-4c61-9c97-2076107f1ec4.png](images/1686058010089-64bd6184-680e-4c61-9c97-2076107f1ec4.png)

```sql
EXPLAIN SELECT * FROM employees WHERE name= '张三' AND age = 18 AND position ='beijing';
```

查看索引长度是140=(3*24+2)+4+(3*20+2),可以算出联合索引中只使用了完整的联合索引

![1686058015744-bb7e6ff0-5d6f-41f0-af4e-d2a7d64ff633.png](images/1686058015744-bb7e6ff0-5d6f-41f0-af4e-d2a7d64ff633.png)

#### 2.最左前缀法则

如果索引了多列，要遵守最左前缀法则。指的是查询从索引的最左前列开始并且不跳过索引中的列。

**——带头大哥不能死，中间兄弟不能断；**

```sql
-- name 74   +age 78 + position 140
EXPLAIN SELECT * FROM employees WHERE name= '张三' and age = 18 AND position = 'beijing' ;
-- 带头大哥不能死
EXPLAIN SELECT * FROM employees WHERE age = 18 AND position = 'beijing';
-- 中间兄弟不能断
EXPLAIN SELECT * FROM employees WHERE name= '张三' AND position = 'beijing';
```

![1686058025925-7e9a3892-4661-48a5-a1be-c8838d54cdb7.png](images/1686058025925-7e9a3892-4661-48a5-a1be-c8838d54cdb7.png)

#### 3.不在索引列上做任何操作（计算、函数、（自动or手动）类型转换），会导致索引失效而转向全表扫描

####

```sql
EXPLAIN SELECT * FROM employees WHERE name = '张三';
EXPLAIN SELECT * FROM employees WHERE left(name,3) = '张三';
```

![1686058087297-b1fd9fcb-7abf-4eda-99c5-d226a20e0499.png](images/1686058087297-b1fd9fcb-7abf-4eda-99c5-d226a20e0499.png)

给hire\_time增加一个普通索引：

```sql
ALTER TABLE `employees` ADD INDEX `idx_hire_time` (`hire_time`) USING BTREE ;
```

```sql
EXPLAIN select * from employees where date(hire_time) ='2018-09-30';
```

![1686058109085-eb233710-739c-4801-bc50-843f7f982bbc.png](images/1686058109085-eb233710-739c-4801-bc50-843f7f982bbc.png)

转化为日期范围查询，有可能会走索引：

```sql
EXPLAIN select * from employees where hire_time >='2018-09-30 00:00:00' and hire_time  18 AND position ='beijing';
```

![1686058217448-d2897ad2-2c54-4103-bb20-5821686b00ea.png](images/1686058217448-d2897ad2-2c54-4103-bb20-5821686b00ea.png)

#### 5.尽量使用覆盖索引（只访问索引的查询（索引列包含查询列）），减少 select \* 语句

**——\*\*\*\*覆盖索引不写星；**

```sql
EXPLAIN SELECT name,age FROM employees WHERE name= '张三' AND age = 18 AND position ='beijing';
```

![1686058263188-a7b01560-407a-418c-bedd-cb10c8ccc09d.png](images/1686058263188-a7b01560-407a-418c-bedd-cb10c8ccc09d.png)

```sql
EXPLAIN SELECT * FROM employees WHERE name= 'LiLei' AND age = 23 AND position ='manager';
```

![1686058283738-a72d9098-da92-4a83-ab1f-ed8598dbb8cf.png](images/1686058283738-a72d9098-da92-4a83-ab1f-ed8598dbb8cf.png)

#### 6.不等空值还有or，索引失效要少用；

**mysql在使用不等于（！=或者<>），not in ，not exists 的时候无法使用索引会导致全表扫描**

\*\* 大于、 = 这些，\*\***mysql内部优化器会根据检索比例、表大小等多个因素整体评估是否使用索引**

```sql
EXPLAIN SELECT * FROM employees WHERE name != '张三';
```

![1686058378015-28d40137-3453-432a-9693-9f4b04e1e224.png](images/1686058378015-28d40137-3453-432a-9693-9f4b04e1e224.png)

**is null,is not null 一般情况下也无法使用索引**

```sql
EXPLAIN SELECT * FROM employees WHERE name is null
```

![1686058392680-23337c8c-dd18-481a-bf11-71e57032e4c9.png](images/1686058392680-23337c8c-dd18-481a-bf11-71e57032e4c9.png)\
**少用or或in，用它查询时，mysql不一定使用索引，mysql内部优化器会根据检索比例、表大小等多个因素整体评估是否使用索引，详见范围查询优化**

```sql
EXPLAIN SELECT * FROM employees WHERE name = 'LiLei' or name = 'HanMeimei';
```

![1686058463446-f1bcb53c-1580-4060-87fa-662386a75717.png](images/1686058463446-f1bcb53c-1580-4060-87fa-662386a75717.png)

#### 7.Like百分写最右

**——\*\*\*\*Like百分写最右**

```sql
EXPLAIN SELECT * FROM employees WHERE name like '%三'
```

![1686058405664-a5f9809b-84b0-45f8-9e09-65a88e8ac5cd.png](images/1686058405664-a5f9809b-84b0-45f8-9e09-65a88e8ac5cd.png)

```sql
EXPLAIN SELECT * FROM employees WHERE name like '张%'
```

![1686058418486-bfec2739-f2ad-44d6-a2f9-d270e386436d.png](images/1686058418486-bfec2739-f2ad-44d6-a2f9-d270e386436d.png)

问题：解决like'%字符串%'索引不被使用的方法？

a）使用覆盖索引，查询字段必须是建立覆盖索引字段

```sql
EXPLAIN SELECT name,age,position FROM employees WHERE name like '%Lei%';
```

![1686058439870-5ea46ede-3336-4350-b78d-1bd4c5741d28.png](images/1686058439870-5ea46ede-3336-4350-b78d-1bd4c5741d28.png)

b）如果不能使用覆盖索引则可能需要借助搜索引擎

#### 8.字符串不加单引号索引失效

**——\*\*\*\*VAR引号不可丢**

```sql
EXPLAIN SELECT * FROM employees WHERE name = '1000';
EXPLAIN SELECT * FROM employees WHERE name = 1000;
```

![1686058452419-9d2c12b1-cb0a-4920-8011-cc1a350ba149.png](images/1686058452419-9d2c12b1-cb0a-4920-8011-cc1a350ba149.png)

#### 9.范围查询优化

给年龄添加单值索引

```sql
ALTER TABLE `employees` ADD INDEX `idx_age` (`age`) USING BTREE ;
```

```sql
explain select * from employees where age >=1 and age =1 and age =1001 and age  set session optimizer_trace="enabled=on",end_markers_in_json=on;  --开启trace
mysql> select * from employees where name > 'a' order by position;
mysql> SELECT * FROM information_schema.OPTIMIZER_TRACE;

查看trace字段：
{
  "steps": [
    {
      "join_preparation": {    --第一阶段：SQL准备阶段，格式化sql
        "select#": 1,
        "steps": [
          {
            "expanded_query": "/* select#1 */ select `employees`.`id` AS `id`,`employees`.`name` AS `name`,`employees`.`age` AS `age`,`employees`.`position` AS `position`,`employees`.`hire_time` AS `hire_time` from `employees` where (`employees`.`name` > 'a') order by `employees`.`position`"
          }
        ] /* steps */
      } /* join_preparation */
    },
    {
      "join_optimization": {    --第二阶段：SQL优化阶段
        "select#": 1,
        "steps": [
          {
            "condition_processing": {    --条件处理
              "condition": "WHERE",
              "original_condition": "(`employees`.`name` > 'a')",
              "steps": [
                {
                  "transformation": "equality_propagation",
                  "resulting_condition": "(`employees`.`name` > 'a')"
                },
                {
                  "transformation": "constant_propagation",
                  "resulting_condition": "(`employees`.`name` > 'a')"
                },
                {
                  "transformation": "trivial_condition_removal",
                  "resulting_condition": "(`employees`.`name` > 'a')"
                }
              ] /* steps */
            } /* condition_processing */
          },
          {
            "substitute_generated_columns": {
            } /* substitute_generated_columns */
          },
          {
            "table_dependencies": [    --表依赖详情
              {
                "table": "`employees`",
                "row_may_be_null": false,
                "map_bit": 0,
                "depends_on_map_bits": [
                ] /* depends_on_map_bits */
              }
            ] /* table_dependencies */
          },
          {
            "ref_optimizer_key_uses": [
            ] /* ref_optimizer_key_uses */
          },
          {
            "rows_estimation": [    --预估表的访问成本
              {
                "table": "`employees`",
                "range_analysis": {
                  "table_scan": {     --全表扫描情况
                    "rows": 10123,    --扫描行数
                    "cost": 2054.7    --查询成本
                  } /* table_scan */,
                  "potential_range_indexes": [    --查询可能使用的索引
                    {
                      "index": "PRIMARY",    --主键索引
                      "usable": false,
                      "cause": "not_applicable"
                    },
                    {
                      "index": "idx_name_age_position",    --辅助索引
                      "usable": true,
                      "key_parts": [
                        "name",
                        "age",
                        "position",
                        "id"
                      ] /* key_parts */
                    }
                  ] /* potential_range_indexes */,
                  "setup_range_conditions": [
                  ] /* setup_range_conditions */,
                  "group_index_range": {
                    "chosen": false,
                    "cause": "not_group_by_or_distinct"
                  } /* group_index_range */,
                  "analyzing_range_alternatives": {    --分析各个索引使用成本
                    "range_scan_alternatives": [
                      {
                        "index": "idx_name_age_position",
                        "ranges": [
                          "a  'a')",
              "attached_conditions_computation": [
              ] /* attached_conditions_computation */,
              "attached_conditions_summary": [
                {
                  "table": "`employees`",
                  "attached": "(`employees`.`name` > 'a')"
                }
              ] /* attached_conditions_summary */
            } /* attaching_conditions_to_tables */
          },
          {
            "clause_processing": {
              "clause": "ORDER BY",
              "original_clause": "`employees`.`position`",
              "items": [
                {
                  "item": "`employees`.`position`"
                }
              ] /* items */,
              "resulting_clause_is_simple": true,
              "resulting_clause": "`employees`.`position`"
            } /* clause_processing */
          },
          {
            "reconsidering_access_paths_for_index_ordering": {
              "clause": "ORDER BY",
              "steps": [
              ] /* steps */,
              "index_order_summary": {
                "table": "`employees`",
                "index_provides_order": false,
                "order_direction": "undefined",
                "index": "unknown",
                "plan_changed": false
              } /* index_order_summary */
            } /* reconsidering_access_paths_for_index_ordering */
          },
          {
            "refine_plan": [
              {
                "table": "`employees`"
              }
            ] /* refine_plan */
          }
        ] /* steps */
      } /* join_optimization */
    },
    {
      "join_execution": {    --第三阶段：SQL执行阶段
        "select#": 1,
        "steps": [
        ] /* steps */
      } /* join_execution */
    }
  ] /* steps */
}

结论：全表扫描的成本低于索引扫描，所以mysql最终选择全表扫描

mysql> select * from employees where name > 'zzz' order by position;
mysql> SELECT * FROM information_schema.OPTIMIZER_TRACE;

查看trace字段可知索引扫描的成本低于全表扫描，所以mysql最终选择索引扫描

mysql> set session optimizer_trace="enabled=off";    --关闭trace
```

## 5、SQL优化

[画板]

#### 1.1. 准备工作：

##### 1.1.1. 创建student表：

```sql
DROP TABLE IF EXISTS student;
CREATE TABLE student (
  id int(10) NOT NULL AUTO_INCREMENT COMMENT '序号',
  student_id INT NOT NULL COMMENT '学号',
  name varchar(20) COMMENT '姓名',
  department varchar(20) COMMENT '院系',
  remarks varchar(400) COMMENT '备注',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

##### 1.1.2. 创建scores表：

```sql
DROP TABLE IF EXISTS scores;
CREATE TABLE scores (
   id INT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '序号',
   student_id INT NOT NULL COMMENT '学号',
   course_name VARCHAR(50) NOT NULL COMMENT '课程名称',
   score INT NOT NULL COMMENT '分数',
   remarks varchar(400) COMMENT '备注'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

##### 1.1.3. 添加索引：

```sql
ALTER TABLE student ADD index idx_name_department (name, department);
```

##### 1.1.4. 插入数据：

```sql
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('刘零',1,'美术','备注0');
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('郑一',2,'土木','备注1');
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('吴二',3,'数学','备注2');
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('张三',4,'中文','备注3');
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('李四',5,'英语','备注4');
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('王五',6,'美术','备注5');
INERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('钱六',7,'土木','备注6');
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('孙七',8,'数学','备注7');
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('赵八',9,'英语','备注8');
INSERT INTO `student` (`name`,`student_id`,`department`,`remarks`) values ('周九',10,'数学','备注9');
```

```sql
BEGIN
	DECLARE v_name VARCHAR(20);
  DECLARE v_department VARCHAR(200);
	DECLARE i INT DEFAULT 0;
	DECLARE n INT DEFAULT 100000;
	DECLARE v_max_id INT DEFAULT 1;
	set autocommit = 0;
	select max(id) into v_max_id from student;
	REPEAT
		set i = i + 1;
		set v_max_id = v_max_id + 1;
		set v_name = CONCAT('mock_name',i);
		set v_department = CONCAT('mock_department',i);
		INSERT INTO `student` (`student_id`,`name`,`department`,`remarks`) values (v_max_id,v_name,v_department,'mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks');

		INSERT INTO `scores` (`student_id`,`course_name`,`score`,`remarks`) values (v_max_id,CONCAT('mock_Chinese',i),RAND()*(100-50)+50,'mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks');
		INSERT INTO `scores` (`student_id`,`course_name`,`score`,`remarks`) values (v_max_id,CONCAT('mock_Math',i),RAND()*(100-50)+50,'mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks');
		INSERT INTO `scores` (`student_id`,`course_name`,`score`,`remarks`) values (v_max_id,CONCAT('mock_English',i),RAND()*(100-50)+50,'mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks');

		UNTIL i = n
	END REPEAT;
	COMMIT;
	set autocommit = 1;
END
```

#### 1.2. SQL优化最佳实践：

##### 1.2.1. 避免使用select \*

阿里规范：

![1679833438373-bb9be90a-ea5e-4ea6-9c76-25cf88bd9dde.png](images/1679833438373-bb9be90a-ea5e-4ea6-9c76-25cf88bd9dde.png)

分析：

查看执行计划，select \* 走全表扫描，没有用到任何索引，查询效率非常低；查询列都是索引列那么这些列被称为覆盖索引。这种情况下查询的相关字段都能走索引，索引查询的效率相对较高。

```sql
EXPLAIN select * from student where name like 'mock_name%';--不走索引
EXPLAIN select name, department from student where name like 'mock_name%';--走索引
```

通过show warnings语句查看查询列\*号替换成表所有字段。

```sql
EXPLAIN select * from student where name like 'mock_name%';--替换成表对应的字段
SHOW WARNINGS;
```

![1679907093052-e96f1904-b7cf-444c-abdb-f86952d8f13a.png](images/1679907093052-e96f1904-b7cf-444c-abdb-f86952d8f13a.png)

总结：

* 查询时需要先将星号解析成表的所有字段然后在查询，**增加查询解析器的成本**；
* select  \* 查询一般**不走覆盖索引**会产生大量的回表查询；
* 在实际应用中我们通常只需要使用某几个字段，其他不需要使用的字段也查出来**浪费CPU、内存资源**；
* 文本数据、大字段数据数据传输**增加网络消耗**。

![1679895428685-931f82f5-ce79-410a-a0cd-4104b5a96150.jpeg](images/1679895428685-931f82f5-ce79-410a-a0cd-4104b5a96150.jpeg)![1680414456643-db561b76-ec69-430a-9b3d-7bee93b2a498.jpeg](images/1680414456643-db561b76-ec69-430a-9b3d-7bee93b2a498.jpeg)

[画板]

##### 1.2.2. 小表驱动大表

小表驱动大表就是指用数据量较小、索引比较完备的表，然后使用其索引和条件对大表进行数据筛选，从而减少数据计算量，提高查询效率。比如说student表有30条数据，scores表有80w条数据。

```sql

EXPLAIN
select * from student left join scores on student.id = scores.student_id;
```

![1680182182469-d69c3714-7715-41f9-9e91-6dd2ad551cb8.png](images/1680182182469-d69c3714-7715-41f9-9e91-6dd2ad551cb8.png)

```sql
EXPLAIN
select * from scores left join student on student.id = scores.student_id;
```

![1680182212063-2213e902-f8ee-465d-bf8d-420a97dc49c3.png](images/1680182212063-2213e902-f8ee-465d-bf8d-420a97dc49c3.png)

Join Buffer（连接缓冲区）是优化器用于处理连接查询操作时的临时缓冲区。简单来说当我们需要比较两个或多个表的数据进行Join操作时，Join Buffer可以帮助MySQL临时存储结果，以减少磁盘读取和CPU负担，提高查询效率。需要注意的是每个join都有一个单独的缓冲区。

Block nested-loop join（BNL算法）会将驱动表数据加载到join buffer里面，然后再批量与非驱动表进行匹配；如果驱动表数据量较大，join buffer无法一次性装载驱动表的结果集，将会分阶段与被驱动表进行批量数据匹配，会增加被驱动表的扫描次数，从而降低查询效率。所以开发中要遵守小表驱动大表的原则。

分阶段匹配过程如下：

1、先把student表前15条数据读到join buffer中。

2、然后用scores表去匹配join buffer中的前15条。

3、记录下匹配结果。

4、清空join buffer。

5、再把student表后15条读取join buffer中。

6、然后用scores表去匹配join buffer中的后15条。

7、记录下匹配结果。

![1680182275517-453a9fad-190b-4aee-b52a-857b6d8ee3c9.jpeg](images/1680182275517-453a9fad-190b-4aee-b52a-857b6d8ee3c9.jpeg)

##### 1.2.3. 用连接查询代替子查询

mysql需要在两张表以上获取数据的方式有两种：第一种通过连表查询获取，第二种通过子查询获取。

模拟一个真实场景，同样student表有30条数据，scores表有80w条数据，我们想查看学号小于15的学员各科分数信息：

```sql
ALTER TABLE scores ADD index idx_student_id (student_id);

EXPLAIN
SELECT
	(SELECT student.NAME FROM student WHERE student.id = scores.student_id),
	scores.course_name,
	scores.score
FROM
	scores;
```

因为子查询需要执行两次数据库查询，一次是外部查询，一次是嵌套子查询。因此，使用连接查询可以减少数据库查询的次数，提高查询的效率。

连接查询可以更好地利用数据库索引，提高查询的性能。子查询通常会使用临时表或内存表，而连接查询可以直接利用表上的索引。这意味着连接查询可以更快地访问表中的数据，减少查询的资源消耗。

对于大型数据集，使用连接查询通常比使用子查询更高效。子查询通常需要扫描整个表，而连接查询可以利用索引加速读取操作。

```sql
EXPLAIN
SELECT
	student.NAME,
	scores.course_name,
	scores.score
FROM
	student inner JOIN scores ON student.id = scores.student_id;
```

使用连接查询可以更快地执行查询操作，减少数据库的负载，提高查询的性能和效率。

##### 1.2.4. 提升group by的效率

* 创建索引：如果你使用group by的列没有索引，那么查询可能会变得很慢。因此，可以创建一个或多个适当的索引来加速查询。

```sql
select remarks from scores group by remarks;
```

添加索引前：

![1680009924139-fd0faa83-2ea0-4df5-8222-cbe3e5fd3517.png](images/1680009924139-fd0faa83-2ea0-4df5-8222-cbe3e5fd3517.png)

添加索引后：

![1680009975989-b2c20052-c6f8-4103-8cb7-506e379b9540.png](images/1680009975989-b2c20052-c6f8-4103-8cb7-506e379b9540.png)

* 调整查询：查询的写法也会影响group by的效率。可以尝试不使用子查询或临时表，或者可以使用JOIN或EXISTS来代替IN子查询。
* 限制结果集的数量：如果你只需要查看一小部分结果，可以在查询中添加LIMIT子句，以便只返回一定数量的结果。

##### 1.2.5. 批量操作

批量插入或批量删除数据，比如说现在需要将1w+数据插入到数据库，大家是一条一条处理还是批量操作呢？建议是批量操作，逐个处理会频繁的与数据库交互，损耗性能。

反例：

```java
for(Order order: list){

     orderMapper.insert(order):

}
```

在循环中逐条插入数据。

```sql
insert into order(id,code,user_id)  values(123,'001',100)
```

该操作需要多次请求数据库，才能完成这批数据的插入。

但众所周知，我们在代码中，每次远程请求数据库，是会消耗一定性能的。而如果我们的代码需要请求多次数据库，才能完成本次业务功能，势必会消耗更多的性能。

那么如何优化呢？

正例：

```java
orderMapper.insertBatch(List users):
```

提供一个批量插入数据的方法。

```sql
insert into order(id,code,user_id)  values(123,'001',100),(124,'002',100),(125,'003',101);
```

这样只需要远程请求一次数据库，sql性能会得到提升，数据量越多，提升越大。

但需要注意的是，不建议一次批量操作太多的数据，如果数据太多数据库响应也会很慢。批量操作需要把握一个度，建议每批数据尽量控制在500以内。如果数据多于500，则分多批次处理。

##### 1.2.6. 使用limit

* 提高查询效率：一个查询返回成千上万的数据行，不仅占用了大量的系统资源，也会占用更多的网络带宽，影响查询效率。使用LIMIT可以限制返回的数据行数，减轻了系统负担，提高了查询效率。
* 避免过度提取数据：对于大型数据库系统，从数据库中提取大量的数据可能会导致系统崩溃。使用LIMIT可以限制提取的数据量，避免过度提取数据，保护系统不受影响。
* 优化分页查询：分页查询需要查询所有的数据才能进行分页处理，这会浪费大量的系统资源和时间。使用LIMIT优化分页查询可以只查询需要的数据行，缩短查询时间，减少资源的浪费。
* 简化查询结果：有时我们只需要一小部分数据来得出决策，而不是整个数据集。使用LIMIT可以使结果集更加精简和易于阅读和理解。

限制行数非常有用，因为它可以提高查询性能、减少处理需要的时间，并且只返回我们关心的列。

**百万级表Limit翻页越往后越慢咋办**

为什么 offset 偏大之后 limit 查找会变慢？这需要了解 limit 操作是如何运作的，以下面这句查询为例：

```javascript
select * from table_name limit 10000,10
```

这句 SQL 的执行逻辑是

* 1.从数据表中读取第N条数据添加到数据集中
* 2.重复第一步直到 N = 10000 + 10
* 3.根据 offset 抛弃前面 10000 条数
* 4.返回剩余的 10 条数据

**第一次优化**

根据数据库这种查找的特性，就有了一种想当然的方法，利用自增索引（假设为id）：

```javascript
select * from table_name where (id >= 10000) limit 10
```

**第二次优化**

说起数据库查询优化，第一时间想到的就是索引，所以便有了第二次优化：先查找出需要数据的索引列（假设为 id），再通过索引列查找出需要的数据。

```javascript
Select * From table_name Where id in (Select id From table_name where ( user = xxx )) limit 10000, 10;

select * from table_name where( user = xxx ) limit 10000,10
```

相比较结果是（500w条数据）：第一条花费平均耗时约为第二条的 1/3 左右。

同样是较大的 offset，第一条的查询更为复杂，为什么性能反而得到了提升？

这涉及到 mysql 主索引的数据结构 b+Tree ，这里不展开，基本原理就是：

* 子查询只用到了索引列，没有取实际的数据，所以不涉及到磁盘IO，所以即使是比较大的 offset 查询速度也不会太差。
* 利用子查询的方式，把原来的基于 user 的搜索转化为基于主键（id）的搜索，主查询因为已经获得了准确的索引值，所以查询过程也相对较快。

**第三次优化**

在数据量大的时候 in 操作的效率就不怎么样了，我们需要把 in 操作替换掉，使用 join 就是一个不错的选择。

```javascript
select * from table_name inner join ( select id from table_name where (user = xxx) limit 10000,10) b using (id)
```

##### 1.2.7. 用union all代替union

* union all：获取所有数据但是数据不去重，包含重复数据；
* union：获取所有数据且数据去重，不包含重复数据；

```sql
select id,name,department from student
union all
select id,student_id,score from scores
```

![1680010654025-dbaa938f-f592-4991-91a5-26b979fb21ed.png](images/1680010654025-dbaa938f-f592-4991-91a5-26b979fb21ed.png)

```sql
select id,name,department from student
union
select id,student_id,score from scores
```

![1680010615392-70b04309-469c-4e6e-907e-171a3bc5d171.png](images/1680010615392-70b04309-469c-4e6e-907e-171a3bc5d171.png)

那么union all与union如果当然它业务数据容许出现重复的记录，我们更推荐使用union all，因为union去重数据需要遍历、排序和比较，它更耗时，更消耗cpu资源，但是数据结果最完整。

##### 1.2.8. join的表不宜过多

* 查询效率下降：多表JOIN查询数据对比时间边长
* 系统负载增加：JOIN操作需要进行大量的计算，因此会导致系统负载增加。
* 维护难度加大：在一个连接了多个表的查询中，如果需要修改其中一个表的结构或内容，就可能会需要同时修改其他表的结构或内容。

因此，在数据库设计时，应该尽量减少JOIN操作的使用频率，并且简化表之间的关系，以提高查询效率和系统的性能。\
除上述优化之外，通常在建表还需要注意以下内容：

* 控制索引数量
* 选择合理的字段类型

### 2. 总结

SQL优化是提高数据库性能的重要方法，在实际开发中我们的SQL要尽量遵守以下几点原则，避免留下技术债：

1. 减少数据扫描
2. 返回更少数据
3. 减少交互次数
4. 减少服务器CPU及内存开销

#


# 史上最全MySQL各种锁详解（含实战案例+排查优化）

# **一、前言：为什么需要锁？**

在并发访问数据库时，多个事务同时读写数据会引发一系列问题（脏读、不可重复读、幻读、超卖等）。锁的核心作用是**协调并发事务对共享资源的访问**，通过控制资源的访问顺序，保证数据的一致性、完整性，是数据库并发控制的核心机制。

本笔记基于MySQL 8.0版本，全面拆解锁的分类、实现原理、实战案例、排查工具及优化策略，兼顾理论深度与生产实操，适配面试与工作需求。

![1768275300074-8df60fea-7f10-4ded-8bc5-ca427ded2026.png](images/1768275300074-8df60fea-7f10-4ded-8bc5-ca427ded2026.png)

# **二、按锁的粒度分类（核心分类方式）**

锁的粒度指锁定资源的范围，粒度越小，并发度越高（锁冲突概率低），但锁管理开销越大；反之则并发度低，开销小。MySQL支持三种粒度的锁：全局锁、表级锁、行级锁。

## **2.1 全局锁：锁定整个MySQL实例**

### 核心定义

全局锁是粒度最大的锁，锁定整个MySQL实例（所有数据库、所有表）。锁定期间，整个实例只读（SELECT除外，DML、DDL、创建/删除数据库等写操作全部阻塞）。

### 常用命令

```plain
-- 加全局锁（Flush tables with read lock）
FLUSH TABLES WITH READ LOCK;

-- 释放全局锁（两种方式）
UNLOCK TABLES; -- 主动释放
quit; -- 断开会话，自动释放
```

### 核心使用场景：全库逻辑备份

场景：运维需要对全库进行逻辑备份（如mysqldump），加全局锁确保备份期间数据一致（避免备份过程中数据被修改）。

注意：InnoDB引擎支持事务的一致性快照（--single-transaction参数），备份时无需加全局锁（利用MVCC实现无锁备份），全局锁更适用于MyISAM等不支持事务的引擎。

### 坑点：阻塞所有写操作，影响业务

生产环境中，全局锁会导致所有写操作（下单、更新数据等）阻塞，仅适合低峰期或只读实例使用。InnoDB备份优先用：mysqldump -u root -p --single-transaction 数据库名 > 备份文件.sql

## **2.2 表级锁：锁定整张表**

表级锁是粒度中等的锁，锁定整张表。特点：**锁管理开销小、加锁快**，但并发度低（同一时间仅一个事务能写表）。MySQL中所有引擎都支持表级锁。

常见表级锁：表锁（读锁/写锁）、元数据锁（MDL锁）、意向锁（IS/IX，表级锁，协调表锁与行锁）。

### 2.2.1 表锁（Table Lock）：读锁/写锁

#### 核心特性

* **表级读锁（Shared Lock，S锁）：多个事务可同时加读锁，读锁之间兼容；读锁阻塞写锁（加读锁后，其他事务无法加写锁）。**
* **表级写锁（Exclusive Lock，X锁）：仅一个事务可加写锁，写锁之间互斥、写锁阻塞读锁（加写锁后，其他事务无法加读/写锁）。**

#### 常用命令

```plain
-- 加表级读锁
LOCK TABLES 表名 READ;

-- 加表级写锁
LOCK TABLES 表名 WRITE;

-- 释放表锁（两种方式）
UNLOCK TABLES; -- 主动释放
quit; -- 断开会话，自动释放
```

#### 使用场景

适合读多写少、写操作耗时短的场景（如统计报表生成、批量更新小表）。InnoDB引擎中，表锁并发度低，优先用行级锁；MyISAM引擎默认用表锁。

### 2.2.2 元数据锁（MDL锁）：保护表结构

#### 核心定义

MDL锁（Metadata Lock）是MySQL 5.5+引入的表级锁，自动添加、自动释放，无需手动操作。核心作用：**保护表结构（元数据）的一致性**，避免“查询过程中表结构被修改”（如查询时删字段）。

#### MDL锁的自动添加规则

* **执行SELECT、INSERT、UPDATE、DELETE时，自动加****MDL读锁****（多个事务可同时加，互不阻塞）；**
* **执行****ALTER TABLE****、DROP TABLE、RENAME TABLE等DDL操作时，自动加****MDL写锁****（仅一个事务可加，写锁与读锁、写锁与写锁互斥）。**

#### 核心坑点：长事务导致MDL写锁阻塞（完整闭环：复现→排查→解决→预防）

##### 步骤1：复现MDL阻塞

场景：生产库中t\_user表有一个长事务（执行了SELECT，持有MDL读锁），持续10分钟未提交。此时运维执行ALTER TABLE t_user ADD COLUMN phone VARCHAR(20)（需加MDL写锁），会被长事务的MDL读锁阻塞。后续所有对t\_user表的查询/更新（需加MDL读锁）都会排队阻塞，导致业务雪崩。

复现步骤：

```plain
-- 会话1（长事务，持有MDL读锁）
START TRANSACTION;
SELECT * FROM t_user; -- 执行后不提交，持有MDL读锁

-- 会话2（运维，执行DDL）
ALTER TABLE t_user ADD COLUMN phone VARCHAR(20); -- 被阻塞

-- 会话3（业务查询，被阻塞）
SELECT * FROM t_user; -- 排队等待MDL读锁，阻塞
```

##### 步骤2：排查MDL阻塞

执行show processlist;，查看进程状态：

```plain
Id | User | Host       | db   | Command | Time | State                                   | Info
---|------|------------|------|---------|------|----------------------------------------|----------------------------------------
10 | root | localhost  | test | Sleep   | 600  |                                        | NULL（会话1的长事务，Sleep状态但持有锁）
11 | root | localhost  | test | Query   | 300  | Waiting for table metadata lock         | ALTER TABLE t_user ADD COLUMN phone...（会话2）
12 | root | localhost  | test | Query   | 200  | Waiting for table metadata lock         | SELECT * FROM t_user（会话3）
```

排查结论：进程10是长事务，持有t\_user表的MDL读锁，阻塞了进程11（DDL）和进程12（查询）。

##### 步骤3：解决方案

1. **优先沟通：找到业务方，确认进程10的长事务用途，督促其提交/回滚；**
2. **紧急处理：若无法终止长事务，执行****kill 10;****（终止进程10，事务回滚，释放MDL读锁）；**
3. **后续优化：用****pt-online-schema-change****工具（无锁改表）替代ALTER TABLE，避免MDL锁阻塞。**

##### 步骤4：预防措施

* **生产环境禁止长事务，设置****innodb_transaction_timeout=300****（5分钟超时）；**
* **DDL操作优先在低峰期执行；**
* **MySQL 8.0+版本补充特性：引入更多ONLINE DDL特性，部分DDL操作（如快速加列）仅在开始和结束瞬间持有MDL写锁，中间会降级为MDL读锁，大幅降低阻塞影响。**

## **2.3 行级锁：InnoDB的核心锁（并发之王）**

表级锁虽然开销小，但并发度低，无法满足电商订单、秒杀等高并发场景的需求。而InnoDB引擎独有的行级锁，通过最小化锁定粒度（仅锁定单条数据行），能大幅提升并发性能，成为高并发场景的核心选择。接下来详细拆解行级锁的实现与实战。

行级锁是InnoDB引擎独有的锁，粒度最小（锁定单条数据行），特点是：**并发度高、锁冲突概率低**，但锁管理开销大、可能产生死锁。仅在事务中生效（BEGIN/COMMIT之间），事务结束后自动释放。

生产核心坑点：行级锁的实现依赖索引！无索引或索引失效时，InnoDB无法利用索引过滤数据，会被迫进行全表扫描，访问每条记录时都会加锁（含所有间隙），其效果等同于表锁，但开销甚至比直接加表锁更大，必须重点规避。

关键补充：从源码角度看，InnoDB并没有像SQL Server那样显式的“锁升级（Lock Escalation）”机制（即达到一定阈值自动转为表锁）。上述“行锁变表锁”的本质是无索引导致全表扫描加锁，而非显式锁升级。

### 2.3.1 行级锁的类型（基于锁属性）

行级锁按属性分为共享锁（S锁/读锁）和排他锁（X锁/写锁），与表级锁的S/X锁逻辑一致，但锁定粒度为行：

* **共享锁（S锁）\*\*\*\*：允许事务读取数据，多个事务可同时持有同一行的S锁（读-读兼容）；S锁阻塞X锁（读-写互斥）。 用法：****SELECT ... LOCK IN SHARE MODE;****（事务内执行，提交/回滚后释放）**
* **排他锁（X锁）\*\*\*\*：允许事务修改/删除数据，仅一个事务可持有同一行的X锁（写-写互斥）；X锁阻塞S锁和其他X锁（写-读、写-写均互斥）。 用法：****SELECT ... FOR UPDATE;**** 或\*\*\*\* ****DML****（INSERT/UPDATE/DELETE）自动加X锁（事务内生效）**

### 2.3.2 行锁算法（基于锁定范围）

InnoDB通过三种锁算法实现行级锁，核心目的是平衡“数据一致性”和“并发性能”，解决幻读等并发问题：

#### 1. 记录锁（Record Lock）：锁定单条记录

* **定义：锁定表中****具体的一条行记录****，仅对存在的记录生效。**
* **适用场景：唯一索引（主键、唯一键）的等值查询（如****WHERE id=1****）。**
* **实战案例：t\_user表id为主键，事务A执行****SELECT * FROM t_user WHERE id=1 FOR UPDATE****，仅锁定id=1的行，其他行不受影响。**

#### 2. 间隙锁（Gap Lock）：锁定索引间隙（防止插入）

核心价值：解决幻读问题！幻读是指同一事务内多次查询同一范围，其他事务插入新行导致查询结果行数变化，间隙锁通过锁定间隙阻止插入，从而避免幻读。

* **定义：锁定“两个索引之间的间隙”（或首行之前、末行之后的间隙），不锁定具体行记录，核心作用是****防止其他事务插入新行****；补充：当事务A持有间隙锁时，事务B插入数据会被阻塞，此时事务B会在内存中生成“插入意向锁（Insert Intention Lock）”并进入等待状态。理解插入意向锁对排查SHOW ENGINE INNODB STATUS中的死锁日志至关重要。**
* **适用场景：非唯一索引的等值查询、范围查询；**
* **关键补充（Supremum pseudo-record）：当查询范围超过当前表中最大值时，InnoDB会锁定（max\_id, +∞）的间隙（最大伪记录区间），防止其他事务插入更大ID的记录，彻底避免幻读。**
* **实战案例：t\_user表age为普通索引（值：10,24,32,45），事务A执行****SELECT * FROM t_user WHERE age BETWEEN 20 AND 30 FOR UPDATE****，会锁定间隙（10,24）；若执行****SELECT * FROM t_user WHERE age > 45 FOR UPDATE****，会锁定（45, +∞）的最大伪记录间隙，此时无法插入age=50的行。**

#### 3. 临键锁（Next-Key Lock）：记录锁+间隙锁

定义：临键锁=记录锁+间隙锁，锁定“左开右闭”的区间（如(10,24]），是InnoDB的默认行锁算法（REPEATABLE READ隔离级别下）。

核心规则（关键修正，必记）：

* **唯一索引的等值查询****：临键锁****降级为记录锁\*\*\*\*（仅锁定匹配行，不锁间隙）；**
* **唯一索引的范围查询\*\*\*\*：仍为临键锁（锁定范围+间隙）；**
* **非唯一索引的等值/范围查询\*\*\*\*：均为临键锁。**

记忆口诀：唯一等值降记录，唯一范围仍临键，非唯一全是临键锁。

### 行级锁实战案例（完整闭环）

#### 实战案例1：用行锁解决库存超卖问题（复现→分析→解决→验证）

场景：电商秒杀场景，t\_stock表存储商品库存（id主键，goods\_id商品ID，stock库存数量），需避免多个用户同时下单导致库存为负。

##### 步骤1：复现超卖问题

准备数据：

```plain
CREATE TABLE t_stock (
idINT PRIMARY KEY AUTO_INCREMENT,
  goods_id INTNOTNULLUNIQUE,
  stock INTNOTNULLDEFAULT0
);
INSERTINTO t_stock (goods_id, stock) VALUES (1001, 1); -- 初始库存1
```

用两个会话同时执行无锁代码：

问题代码（无锁，会超卖）：

```plain
-- 会话1（用户A下单）
STARTTRANSACTION;
SELECT stock FROM t_stock WHERE goods_id=1001;  -- 查到stock=1
UPDATE t_stock SET stock=stock-1WHERE goods_id=1001;  -- 执行后stock=0
-- 暂不提交

-- 会话2（用户B下单，同时执行）
STARTTRANSACTION;
SELECT stock FROM t_stock WHERE goods_id=1001;  -- 未提交读隔离级别下也查到stock=1
UPDATE t_stock SET stock=stock-1WHERE goods_id=1001;  -- 执行后stock=-1
COMMIT;
```

复现结果：两个会话都执行成功，stock变为-1，超卖问题产生。

##### 步骤2：问题分析

无锁情况下，多个事务可同时读取并修改同一行数据，缺乏并发控制，导致库存计数错误。需通过排他锁（X锁）锁定目标行，确保同一时间仅一个事务能修改。

##### 步骤3：解决方案（加X锁，避免并发修改）

```plain
-- 会话1（用户A下单）
STARTTRANSACTION;
-- 加X锁锁定该商品行，其他事务需等待锁释放
SELECT stock FROM t_stock WHERE goods_id=1001FORUPDATE;
IF stock > 0 THEN
UPDATE t_stock SET stock=stock-1WHERE goods_id=1001;
-- 生成订单...
COMMIT;
ELSE
-- 库存不足，提示用户
ROLLBACK;
ENDIF;

-- 会话2（用户B下单，同时执行）
STARTTRANSACTION;
SELECT stock FROM t_stock WHERE goods_id=1001FORUPDATE;  -- 被会话1的X锁阻塞
-- 会话1提交后，会话2查询到stock=0，执行ELSE逻辑，回滚
ROLLBACK;
```

##### 步骤4：验证结果

执行后查询t\_stock：SELECT stock FROM t_stock WHERE goods_id=1001;，stock=0，无超卖；会话2被阻塞直到会话1提交，确保了数据一致性。

关键：goods\_id需建立索引（如唯一索引），否则无索引导致全表扫描加锁，效果等同于表锁，所有商品秒杀都会阻塞。

#### 实战案例2：无索引导致全表扫描加锁（复现→分析→解决→验证）

场景：t\_user表（id主键，age无索引），事务A执行更新操作未指定索引，导致全表扫描加锁（效果等同于表锁），阻塞其他事务。

##### 步骤1：复现问题

准备数据：

```plain
CREATE TABLE t_user (
idINT PRIMARY KEY AUTO_INCREMENT,
nameVARCHAR(20) NOTNULL,
  age INTNOTNULL
);
INSERTINTO t_user (name, age) VALUES ('张三',25), ('李四',30);
```

会话1（事务A，无索引更新）：

```plain
-- 事务A（无索引，全表扫描加锁）
START TRANSACTION;
UPDATE t_user SET name='李四' WHERE age=25;  -- age无索引，全表扫描，所有行加X锁
-- 未提交...
```

会话2（事务B，更新其他行）：

```plain
-- 事务B（被阻塞）
START TRANSACTION;
UPDATE t_user SET name='王五' WHERE id=10;  -- 即使按主键更新，也被全表锁阻塞
COMMIT;
```

复现结果：事务B长时间阻塞，无法执行。

##### 步骤2：问题分析

age字段无索引，事务A执行UPDATE时触发全表扫描，InnoDB会对表中所有行加X锁（含所有间隙），其效果等同于表锁，但开销更大，导致所有对t\_user表的更新都被阻塞。注意：这并非显式锁升级，而是无索引导致的全表扫描加锁。

##### 步骤3：解决方案

为age字段建立索引，确保行锁仅锁定匹配行：ALTER TABLE t_user ADD INDEX idx_age(age);

##### 步骤4：验证结果

重新执行事务A和事务B：

```plain
-- 事务A（有索引，仅锁age=25的行）
STARTTRANSACTION;
UPDATE t_user SETname='李四'WHERE age=25;
-- 未提交

-- 事务B（正常执行，不阻塞）
STARTTRANSACTION;
UPDATE t_user SETname='王五'WHEREid=10;
COMMIT;
```

验证结果：事务B正常执行，无阻塞，仅匹配行被锁定。

#### 实战案例3：转账场景死锁（复现→排查→解决→验证）

##### 步骤1：复现死锁

准备数据：t\_account表（id主键，user\_id用户ID，balance余额）

```plain
CREATE TABLE t_account (
idINT PRIMARY KEY AUTO_INCREMENT,
  user_id INTNOTNULLUNIQUE,
  balance INTNOTNULLDEFAULT0
);
INSERTINTO t_account (user_id, balance) VALUES (1, 1000), (2, 1000);
```

同时执行两个会话的转账SQL：

```plain
-- 会话1（事务A：用户1给用户2转账100元）
STARTTRANSACTION;
UPDATE t_account SET balance=balance-100WHERE user_id=1;  -- 持有user_id=1的X锁
UPDATE t_account SET balance=balance+100WHERE user_id=2;  -- 等待user_id=2的X锁
COMMIT;

-- 会话2（事务B：用户2给用户1转账50元）
STARTTRANSACTION;
UPDATE t_account SET balance=balance-50WHERE user_id=2;  -- 持有user_id=2的X锁
UPDATE t_account SET balance=balance+50WHERE user_id=1;  -- 等待user_id=1的X锁
COMMIT;
```

复现结果：MySQL检测到死锁，终止其中一个事务（如事务B），提示“Deadlock found when trying to get lock; try restarting transaction”。

##### 步骤2：死锁排查（解读死锁日志）

执行SHOW ENGINE INNODB STATUS;，查看死锁日志核心部分：

```plain
------------------------
LATEST DETECTED DEADLOCK
------------------------
2025-12-29 10:00:00 0x7f8b12345678
TRANSACTION 12345, ACTIVE 2 sec starting index read
mysql tables in use 1, locked 1
LOCK WAIT 2 lock struct(s), heap size 1136, 1 row lock(s)
MySQL thread id 8, OS thread handle 140245678901234, query id 123 localhost root updating
UPDATE t_account SET balance=balance+100 WHERE user_id=2
TRANSACTION 67890, ACTIVE 1 sec starting index read
mysql tables in use 1, locked 1
LOCK WAIT 2 lock struct(s), heap size 1136, 1 row lock(s)
MySQL thread id 9, OS thread handle 140245678901235, query id 124 localhost root updating
UPDATE t_account SET balance=balance+50 WHERE user_id=1
WE ROLL BACK TRANSACTION 67890; -- 回滚事务B
```

日志解读：

* **事务12345（线程8）：持有user\_id=1的X锁，等待user\_id=2的X锁；**
* **事务67890（线程9）：持有user\_id=2的X锁，等待user\_id=1的X锁；**
* **形成循环等待，MySQL回滚其中一个事务（通常是执行时间短的）。**

##### 步骤3：死锁解决方案

1. **统一锁顺序\*\*\*\*：所有事务按相同顺序锁定行（如按user\_id升序），避免循环等待。修改后代码： \`-- 事务A、B均先锁user\_id小的行 -- 事务A（用户1→用户2转账） START TRANSACTION; UPDATE t\_account SET balance=balance-100 WHERE user\_id=1;  -- 1**innodb_lock_wait_timeout****（默认50秒）设置锁等待超时时间，避免永久阻塞；**
3. **死锁排查\*\*\*\*：用****SHOW ENGINE INNODB STATUS****查看死锁日志，分析事务持有/等待的锁资源。**

##### 步骤4：验证结果

修改后重新执行两个事务：事务B会先等待事务A释放user\_id=1的X锁，事务A提交后，事务B获取锁继续执行，无死锁产生。

# **三、按并发控制策略分类：悲观锁 vs 乐观锁**

悲观锁和乐观锁是两种核心的并发控制思想，并非MySQL提供的具体锁类型，而是基于锁机制或无锁机制实现的策略。悲观锁基于“冲突大概率发生”的假设，乐观锁基于“冲突小概率发生”的假设。

## **3.1 悲观锁（Pessimistic Locking）**

### 核心思想

认为并发事务之间的冲突是大概率事件，因此在**操作数据前先锁定资源**，确保整个操作过程中资源独占，避免冲突。

### 实现方式

依赖MySQL的锁机制：行级锁（S锁/X锁）、表级锁。例如：

* **行级悲观锁：****SELECT ... FOR UPDATE****（X锁）、****SELECT ... LOCK IN SHARE MODE****（S锁）；**
* **表级悲观锁：****LOCK TABLES 表名 WRITE****（表级X锁）。**

### 适用场景

写多读少、冲突概率高的场景（如银行转账、订单状态修改、高并发秒杀的库存更新）。

## **3.2 乐观锁（Optimistic Locking）**

悲观锁虽然能保证强一致性，但锁等待会降低并发度；而乐观锁基于“低冲突”假设，通过无锁操作提升并发，两者无绝对优劣，需结合业务场景选择。接下来详细拆解乐观锁的实现与实战。

### 核心思想

认为并发事务之间的冲突是小概率事件，因此**操作数据前不锁定资源**，直接执行操作，仅在提交事务时校验数据是否被其他事务修改（若修改则重试，未修改则提交）。

### 实现方式（无锁机制，应用层实现）

乐观锁不依赖MySQL的锁机制，由应用层通过逻辑实现，常见三种方式：

#### 1. 版本号机制（最常用）

在表中新增version字段（版本号，初始为0），每次更新数据时版本号+1，提交时校验版本号是否与查询时一致（一致则更新，不一致则重试）。

```plain
-- 1. 表结构设计（新增version字段）
CREATETABLE t_product (
idINT PRIMARY KEY AUTO_INCREMENT,
nameVARCHAR(50) NOTNULL,
  price DECIMAL(10,2) NOTNULL,
versionINTNOTNULLDEFAULT0-- 版本号
);

-- 2. 乐观锁更新逻辑（查询→更新→校验版本号）
STARTTRANSACTION;
-- 步骤1：查询数据，获取当前版本号
SELECT price, versionFROM t_product WHEREid=1; -- 假设查询到price=100, version=0

-- 步骤2：更新数据，仅当版本号匹配时才更新
UPDATE t_product
SET price=90, version=version+1
WHEREid=1ANDversion=0; -- 校验版本号，一致则更新

-- 步骤3：判断更新结果，无记录更新则说明数据被修改，重试
IF ROW_COUNT() = 0 THEN
ROLLBACK; -- 回滚，重试逻辑（应用层实现）
ELSE
COMMIT; -- 提交成功
ENDIF;
```

#### 2. 时间戳机制

与版本号机制类似，新增update_time字段（时间戳），提交时校验时间戳是否与查询时一致。缺点：高并发下可能因时间戳精度问题导致校验失效（如同一毫秒更新），优先用版本号。

#### 3. MVCC（广义乐观锁）

InnoDB的MVCC（多版本并发控制）机制，通过保存数据的多个版本，实现“无锁读”（普通SELECT无需加锁），本质是广义的乐观锁（读操作不阻塞写，写操作不阻塞读）。

### 适用场景

读多写少、冲突概率低的场景（如商品浏览量统计、用户点赞、低并发的库存查询）。

## **3.3 乐观锁 vs 悲观锁 对比表**

图例：✅ 优势 | ❌ 劣势

| **对比维度** | **乐观锁 (Optimistic)** | **悲观锁 (Pessimistic)** |
| :--- | :--- | :--- |
| 核心思想 | "冲突是小概率事件"，先操作，提交时校验 | "冲突大概率发生"，操作前先独占资源 |
| 实现机制 | CAS 算法、版本号机制 (Version)、时间戳、MVCC (广义) | 数据库锁机制 (S锁/X锁)、SELECT...FOR UPDATE |
| 优点 | 吞吐量高，无锁等待，无死锁风险 ✅ | 强一致性保证，逻辑简单，避免脏数据 ✅ |
| 缺点 | 高冲突下重试导致 CPU 飙升，存在 ABA 问题 ❌ | 并发度低，锁开销大，可能产生死锁 ❌ |
| 适用场景 | 读多写少 (如：浏览量、点赞、低并发库存) | 写多读少 (如：银行转账、强一致性订单状态) |

# **四、按锁属性/状态分类：意向锁（IS/IX锁）**

共享锁（S锁）、排他锁（X锁）已在“行级锁”章节详细讲解，而意向锁是协调表级锁与行级锁的核心机制——表级锁与行级锁并存时，若需判断表中是否存在行锁，无意向锁则需全表遍历，效率极低。接下来补充意向锁的完整知识体系。

## **4.1 意向共享锁（IS锁）与意向排他锁（IX锁）**

### 核心定义与设计初衷

意向锁是InnoDB引擎自动添加的**表级锁**，用于协调表级锁与行级锁的关系，解决“表锁与行锁冲突检查时全表遍历”的性能问题。其设计初衷是：当事务需要对表中某行加S锁或X锁时，先向表中添加对应的意向锁，后续其他事务请求表级锁时，只需判断表中是否存在对应的意向锁，即可快速确定是否存在行锁冲突，无需遍历表中所有行。

意向锁的两种核心类型（均由InnoDB自动管理，无需手动添加或释放）：

* **意向共享锁（Intention Shared Lock，IS锁）\*\*\*\*：事务准备对表中某行加S锁时，InnoDB会自动先为该表加IS锁。例如，事务执行****SELECT * FROM t_user WHERE id=1 LOCK IN SHARE MODE****前，会先给t\_user表加IS锁。**
* **意向排他锁（Intention Exclusive Lock，IX锁）\*\*\*\*：事务准备对表中某行加X锁时，InnoDB会自动先为该表加IX锁。例如，事务执行****UPDATE t_user SET name='张三' WHERE id=1****前，会先给t\_user表加IX锁。**

### 关键特性：为何意向锁是表级锁？

意向锁的核心价值是“快速判断表中是否存在行锁”，若将其设计为行级锁，当其他事务请求表级锁时，仍需遍历表中所有行检查是否存在行锁，无法解决“全表遍历”的性能问题。而表级锁的设计，能让锁冲突检查仅通过一次表级状态判断完成，大幅提升效率。

对比示例：假设事务A已对t\_user表id=1的行加X锁（自动关联IX锁），此时事务B请求表级写锁（LOCK TABLES t\_user WRITE）：

* **无意向锁场景：MySQL需遍历t\_user全表的每一行，检查是否存在行锁（数据量越大效率越低，百万级表可能耗时数秒）；**
* **有意向锁场景：MySQL直接检查t\_user表的IX锁状态（存在），立即判定冲突，拒绝事务B的表级写锁请求（耗时微秒级）。**

### 核心兼容规则（含IS/IX与行级锁、表级锁交互）

图例：✅ 兼容 | ❌ 互斥 核心口诀：意向锁之间全兼容；意向锁只与表级锁互斥（意向排他互斥表级读/写，意向共享互斥表级写）。

| **当前锁 \ 请求锁** | **IS 锁 (意向共享)** | **IX 锁 (意向排他)** | **S 锁 (表级读)** | **X 锁 (表级写)** | **S 锁 (行级读)** | **X 锁 (行级写)** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| IS 锁 | ✅ 兼容 | ✅ 兼容 | ✅ 兼容 | ❌ 互斥 | ✅ 兼容 | ❌ 互斥 |
| IX 锁 | ✅ 兼容 | ✅ 兼容 | ❌ 互斥 | ❌ 互斥 | ✅ 兼容 | ❌ 互斥 |
| S 锁 (表级) | ✅ 兼容 | ❌ 互斥 | ✅ 兼容 | ❌ 互斥 | ✅ 兼容 | ❌ 互斥 |
| X 锁 (表级) | ❌ 互斥 | ❌ 互斥 | ❌ 互斥 | ❌ 互斥 | ❌ 互斥 | ❌ 互斥 |

关键补充：意向锁不直接阻塞行级锁，行级锁之间的冲突由行锁本身决定（如行级S锁与X锁互斥）；意向锁仅用于快速判断表级锁与行级锁的冲突。

### 实战场景：IS/IX锁的核心作用体现

#### 场景1：长事务行锁与表级备份锁的协调

生产环境中，事务A（长事务）执行SELECT * FROM t_order WHERE order_id=1001 FOR UPDATE（对行加X锁，自动加IX锁），持续10分钟未提交。此时运维需执行全表备份，执行LOCK TABLES t_order READ（表级S锁）。

执行逻辑：

1. **备份请求检查t\_order表的意向锁状态，发现存在IX锁；**
2. **根据兼容规则，表级S锁与IX锁互斥，备份请求被阻塞；**
3. **运维通过****show processlist****定位到长事务A，督促业务方提交事务；**
4. **事务A提交后，IX锁自动释放，备份请求成功获取表级S锁，执行备份。**

#### 场景2：多事务行锁与DDL锁的冲突协调

事务B执行SELECT * FROM t_user WHERE id=5 LOCK IN SHARE MODE（加行级S锁，自动加IS锁），事务C执行SELECT * FROM t_user WHERE id=8 LOCK IN SHARE MODE（加行级S锁，自动加IS锁）。此时开发执行ALTER TABLE t_user ADD COLUMN email VARCHAR(50)（需加MDL写锁，本质是表级排他锁）。

执行逻辑：

1. **DDL请求检查t\_user表意向锁，发现存在IS锁；**
2. **MDL写锁与IS锁互斥，DDL请求被阻塞；**
3. **事务B、C提交后，IS锁释放；**
4. **DDL请求获取MDL写锁，完成表结构修改并释放锁。**

### 核心注意事项

* **自动管理，无需手动操作\*\*\*\*：IS/IX锁由InnoDB自动添加和释放，事务结束（提交/回滚）后，意向锁随同行级锁一同释放，用户无需执行****LOCK****或****UNLOCK****命令。**

**不直接阻塞数据读写**：意向锁仅用于锁冲突的“预判断”，不直接锁定数据。例如，表中存在IS锁时，其他事务仍可正常执行SELECT、UPDATE、DELETE等数据操作（只要不涉及表级锁冲突）；即使表中有IX锁，不同事务也能对表中不同行加行级锁并正常操作，仅当请求表级锁时才会触发冲突检查。

# **五、锁相关排查工具与命令（实战必备）**

生产环境中，锁阻塞、死锁是常见问题，掌握以下排查工具能快速定位问题根源。所有命令基于MySQL 8.0版本，可直接在客户端执行。

## **5.1 查看当前数据库进程与锁等待状态**

### 核心命令：show processlist;

作用：查看当前MySQL所有连接进程的状态，包括进程ID、执行命令、等待状态、执行SQL等，快速定位阻塞进程。

```plain
-- 查看所有进程（精简版）
show processlist;

-- 查看完整进程信息（含完整SQL）
show full processlist;
```

关键状态解读（锁相关）：

* **Waiting for table metadata lock\*\*\*\*：MDL锁等待（通常由长事务持有MDL读锁，阻塞DDL操作）；**
* **Waiting for row lock\*\*\*\*：行级锁等待（如事务A持有X锁，事务B请求同一行X锁）；**
* **Sleep\*\*\*\*：进程处于空闲状态，但可能持有锁（长事务常见状态）。**

排查示例：通过State字段筛选出“Waiting for table metadata lock”的进程，记录其Id（阻塞源进程），再查看对应的Info字段（执行的SQL），定位长事务所属业务。

## **5.2 查看InnoDB引擎锁详细信息**

### 核心命令：show engine innodb status;

作用：输出InnoDB引擎的详细状态，包括死锁日志、锁结构、事务信息等，是排查死锁的核心工具。

```plain
show engine innodb status;
```

关键信息模块（重点关注）：

#### 1. LATEST DETECTED DEADLOCK（最新死锁日志）

包含死锁发生时间、参与死锁的事务、持有/等待的锁资源、被回滚的事务等信息。示例解读：

```plain
LATEST DETECTED DEADLOCK
------------------------
2025-12-29 14:30:00 0x7f8b12345678
TRANSACTION 12345, ACTIVE 2 sec starting index read
mysql tables in use 1, locked 1
LOCK WAIT 2 lock struct(s), heap size 1136, 1 row lock(s)
MySQL thread id 8, OS thread handle 140245678901234, query id 123 localhost root updating
UPDATE t_account SET balance=balance+100 WHERE user_id=2  -- 事务1等待的操作
TRANSACTION 67890, ACTIVE 1 sec starting index read
mysql tables in use 1, locked 1
LOCK WAIT 2 lock struct(s), heap size 1136, 1 row lock(s)
MySQL thread id 9, OS thread handle 140245678901235, query id 124 localhost root updating
UPDATE t_account SET balance=balance+50 WHERE user_id=1  -- 事务2等待的操作
WE ROLL BACK TRANSACTION 67890; -- 被回滚的事务
```

解读要点：确定两个事务的“持有锁”和“等待锁”，判断是否存在循环等待，进而优化锁顺序。

#### 2. TRANSACTIONS（当前活跃事务）

查看当前未提交的活跃事务，包括事务持有锁数量、执行时间等，可定位长事务（执行时间过长的事务）。

## **5.3 查询锁相关系统表（精准定位锁资源）**

MySQL 8.0提供多个系统表用于精准查询锁信息，需注意：**MySQL 8.0已移除information\_schema库下的innodb\_locks和innodb\_lock\_waits表**，取而代之的是performance\_schema库下的data\_locks和data\_lock\_waits表（8.0新特性），新表提供更详细的锁关联信息，可精准查询锁的类型、持有/等待进程、关联表和索引等内容。

```plain
-- 重要提示：MySQL 8.0 新特性（旧表innodb_locks已移除）
-- 1. 查看当前所有锁信息（替代原innodb_locks）
SELECT * FROM performance_schema.data_locks;

-- 2. 查看锁等待关系（替代原innodb_lock_waits）
-- 核心字段：blocking_engine_transaction_id（阻塞事务ID）、requesting_engine_transaction_id（请求事务ID）
SELECT
  blocking_engine_transaction_id AS blocking_trx_id,  -- 阻塞方事务ID
  requesting_engine_transaction_id AS requesting_trx_id, -- 请求方事务ID
  blocking_lock_id,  -- 阻塞方锁ID
  requesting_lock_id -- 请求方锁ID
FROM performance_schema.data_lock_waits;

-- 3. 结合进程表，定位阻塞源对应的SQL（适配8.0新表）
SELECT
  p.id,  -- 进程ID
  p.user,
  p.host,
  p.db,
  p.info,  -- 执行的SQL
  l.lock_type,  -- 锁类型（TABLE/ROW）
  l.lock_mode,  -- 锁模式（X/S/IS/IX等）
  l.lock_table  -- 锁定的表
FROM
  information_schema.processlist p
JOIN
  performance_schema.data_locks l ON p.id = SUBSTRING_INDEX(l.lock_id, ':', 1)
WHERE
  p.state LIKE 'Waiting for%'; -- 筛选等待锁的进程
```

使用场景：当show processlist无法精准定位锁资源时，通过系统表可获取更详细的锁关联信息，快速找到阻塞根源。

# **六、生产环境锁优化策略（避坑指南）**

锁问题的核心优化思路：**减少锁持有时间、缩小锁粒度、避免锁冲突、合理选择锁策略**。结合前文案例，总结以下实战优化方案：

## **6.1 核心优化原则：缩小锁粒度**

* **必须为查询条件字段建索引\*\*\*\*：行级锁依赖索引，无索引或索引失效会导致全表扫描加锁（效果等同于表锁）。例如，更新/删除操作的WHERE条件字段（如goods\_id、user\_id）必须建立索引（主键/唯一索引/普通索引）。**
* **避免全表扫描和全表更新\*\*\*\*：禁止执行无WHERE条件的UPDATE/DELETE（如UPDATE t\_user SET status=1），此类操作会对表中所有行加X锁，导致并发阻塞。**
* **使用精准查询条件\*\*\*\*：尽量用唯一索引的等值查询（如WHERE id=100），使临键锁降级为记录锁，减少锁定范围；避免非唯一索引的范围查询（如WHERE age>30），此类查询会产生间隙锁/临键锁，扩大锁定范围。**

## **6.2 关键优化：减少锁持有时间**

* **控制事务大小，避免长事务\*\*\*\*：事务中仅包含核心操作（如锁定数据、更新数据），非核心操作（如日志记录、通知推送、调用外部接口）移到事务外。例如，订单创建事务仅包含“扣减库存+生成订单”，后续的短信通知单独执行。**
* **及时提交/回滚事务\*\*\*\*：禁止事务长时间处于未提交状态（如事务开启后等待用户输入），设置innodb\_transaction\_timeout=300（5分钟超时），自动回滚超时未提交的事务。**
* **避免在事务中执行慢查询\*\*\*\*：慢查询会延长事务执行时间，导致锁持有时间增加。优化慢查询（如添加索引、优化SQL结构），避免事务内执行耗时超过1秒的查询。**

## **6.3 避免锁冲突：统一锁顺序+合理设计业务**

* **统一事务的锁顺序\*\*\*\*：多个事务操作同一组表/行时，按固定顺序锁定资源，避免循环等待导致死锁。例如，转账场景中，所有事务均按user\_id升序锁定账户（先锁user\_id小的账户）。**
* **避免并发更新同一行数据\*\*\*\*：高并发场景（如秒杀、点赞），避免多个事务同时更新同一行（如库存表的同一条记录）。可通过“分库分表”（如库存按商品ID哈希分表）或“乐观锁”（版本号机制）替代悲观锁，减少冲突。**
* **读写分离，降低读锁冲突\*\*\*\*：高读并发场景，采用“主从复制+读写分离”架构，读请求路由到从库，写请求路由到主库。从库通过MVCC实现无锁读，避免读请求对主库写锁的阻塞。**

## **6.4 合理选择锁策略与MySQL特性**

* **按业务场景选择悲观/乐观锁\*\*\*\*：读多写少、低冲突场景（如商品浏览量）用乐观锁（版本号）；写多读少、高冲突场景（如银行转账）用悲观锁（行级X锁）。**
* **利用MySQL 8.0 ONLINE DDL特性\*\*\*\*：执行表结构修改（如加列、改字段类型）时，优先使用MySQL 8.0的ONLINE DDL特性，部分操作（如快速加列）仅在开始和结束瞬间持有MDL写锁，中间降级为读锁，大幅降低阻塞影响。**
* **避免使用表级锁\*\*\*\*：InnoDB引擎优先使用行级锁，避免手动执行LOCK TABLES（表级锁）。若需批量更新小表，可在低峰期执行，或用行级锁分批更新（如按ID分段更新）。**
* **合理设置隔离级别\*\*\*\*：默认隔离级别为REPEATABLE READ（支持间隙锁/临键锁，避免幻读）；若业务无需避免幻读，可降低隔离级别为READ COMMITTED，此时InnoDB会禁用间隙锁（仅保留记录锁），减少锁冲突（注意：需接受不可重复读）。**

## **6.5 运维监控：提前预警锁问题**

* **监控锁等待指标\*\*\*\*：通过Prometheus+Grafana等监控工具，监控MySQL的锁相关指标，如锁等待次数、锁等待时间、长事务数量等，设置阈值预警（如锁等待时间超过5秒报警）。**
* **定期审计慢查询和长事务\*\*\*\*：开启MySQL慢查询日志（slow\_query\_log=1），定期分析慢查询；通过information\_schema.innodb\_trx表定期排查长事务，及时优化业务代码。**

# **七、总结**

MySQL锁是并发控制的核心，掌握锁的类型、实现原理和实战排查优化，是保障高并发业务稳定运行的关键。本笔记核心要点总结：

* **锁粒度选择\*\*\*\*：高并发优先用行级锁（InnoDB独有），低并发/小表可用表级锁，全库备份可用全局锁（InnoDB优先用--single-transaction无锁备份）。**
* **行锁关键规则\*\*\*\*：行锁依赖索引，无索引导致全表扫描加锁；唯一等值降记录锁，唯一范围仍临键锁，非唯一全是临键锁；间隙锁（含最大伪记录区间）解决幻读。**
* **锁问题排查\*\*\*\*：show processlist定位阻塞进程，show engine innodb status查看死锁日志，information\_schema系统表精准查询锁资源。**
* **优化核心\*\*\*\*：缩小锁粒度、减少锁持有时间、统一锁顺序、按场景选锁策略，结合MySQL 8.0特性（ONLINE DDL、读写分离）提升并发性能。**

锁的使用没有绝对最优方案，需结合业务场景（并发量、冲突概率、一致性要求）灵活选择，最终实现“数据一致性”与“并发性能”的平衡。

**觉得有用的兄弟，****点个赞，收藏起来****，万一下次面试就用上了呢！**


# MySQL中NULL和NOTNULL一定不走索引？

在 MySQL 中，字段是否允许为 NULL 以及字段的定义方式会直接影响查询条件 IS NULL 和 IS NOT NULL 是否使用索引。此外，字段中 NULL 值的分布占比也会显著影响查询性能和优化器的决策。

本文通过实验分析了字段定义为 NOT NULL 和允许为 NULL 时的查询行为，并结合 NULL 值分布占比的测试结果，总结了优化器的决策逻辑和相关结论。

***

### 一、实验背景

#### 1. 测试目标

* 验证字段定义为 NOT NULL 时，IS NULL 和 IS NOT NULL 查询是否走索引。
* 验证字段允许为 NULL 时，IS NULL 和 IS NOT NULL 查询是否走索引。
* 探讨字段中 NULL 值分布占比对查询性能和索引使用的影响。

#### 2. 测试表结构

创建测试表 staffs，初始字段定义为 NOT NULL，并插入测试数据。

```plsql
CREATE TABLE staffs (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(24) NOT NULL DEFAULT '' COMMENT '姓名',
  age INT NOT NULL DEFAULT 0 COMMENT '年龄',
  pos VARCHAR(20) NOT NULL DEFAULT '' COMMENT '职位',
  add_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入职时间'
) CHARSET utf8 COMMENT '员工记录表';

-- 为 name、age、pos 添加联合索引
ALTER TABLE staffs ADD INDEX idx_staffs_nameAgePos (name, age, pos);

-- 插入测试数据
INSERT INTO staffs (name, age, pos) VALUES ('z3', 22, 'manager');
INSERT INTO staffs (name, age, pos) VALUES ('July', 23, 'dev');
INSERT INTO staffs (name, age, pos) VALUES ('2000', 23, 'dev');
```

表数据如下：

```plsql
SELECT * FROM staffs;
+----+------+-----+---------+---------------------+
| id | name | age | pos     | add_time            |
+----+------+-----+---------+---------------------+
|  1 | z3   |  22 | manager | 2024-12-17 16:47:45 |
|  2 | July |  23 | dev     | 2024-12-17 16:47:45 |
|  3 | 2000 |  23 | dev     | 2024-12-17 16:47:45 |
+----+------+-----+---------+---------------------+
```

***

### 二、测试过程与结果

#### 1. 字段定义为 NOT NULL 时的查询行为

##### 查询 1：IS NULL

```plsql
EXPLAIN SELECT * FROM staffs WHERE name IS NULL;
```

**结果**：

* 查询条件 IS NULL 被认为是 **Impossible WHERE**，即不可能成立的条件。
* 执行计划显示：

```plsql
+----+-------------+-------+------------+------+---------------+------+---------+------+------+----------+------------------+
| id | select_type | table | partitions | type | possible_keys | key  | key_len | ref  | rows | filtered | Extra            |
+----+-------------+-------+------------+------+---------------+------+---------+------+------+----------+------------------+
|  1 | SIMPLE      | NULL  | NULL       | NULL | NULL          | NULL | NULL    | NULL | NULL |     NULL | Impossible WHERE |
+----+-------------+-------+------------+------+---------------+------+---------+------+------+----------+------------------+
```

* **原因**：字段 name 定义为 NOT NULL，因此不可能有 NULL 值，MySQL 优化器直接跳过扫描，返回空集。

##### 查询 2：IS NOT NULL

```plsql
EXPLAIN SELECT * FROM staffs WHERE name IS NOT NULL;
```

**结果**：

* 查询条件 IS NOT NULL 没有走索引，而是进行了全表扫描。
* 执行计划显示：

```plsql
+----+-------------+--------+------------+------+-----------------------+------+---------+------+------+----------+-------------+
| id | select_type | table  | partitions | type | possible_keys         | key  | key_len | ref  | rows | filtered | Extra       |
+----+-------------+--------+------------+------+-----------------------+------+---------+------+------+----------+-------------+
|  1 | SIMPLE      | staffs | NULL       | ALL  | idx_staffs_nameAgePos | NULL | NULL    | NULL |    3 |    66.67 | Using where |
+----+-------------+--------+------------+------+-----------------------+------+---------+------+------+----------+-------------+
```

* **原因**：字段 name 定义为 NOT NULL，所有记录都符合 IS NOT NULL 条件，优化器认为全表扫描成本更低，因此未使用索引。

##### 查询 3：覆盖索引优化

```plsql
EXPLAIN SELECT name FROM staffs WHERE name IS NOT NULL;
```

**结果**：

* 查询条件 IS NOT NULL 使用了覆盖索引。
* 执行计划显示：

```plsql
----+-------------+--------+------------+-------+-----------------------+-----------------------+---------+------+------+----------+--------------------------+
| id | select_type | table  | partitions | type  | possible_keys         | key                   | key_len | ref  | rows | filtered | Extra                    |
+----+-------------+--------+------------+-------+-----------------------+-----------------------+---------+------+------+----------+--------------------------+
|  1 | SIMPLE      | staffs | NULL       | index | idx_staffs_nameAgePos | idx_staffs_nameAgePos | 140     | NULL |    3 |    66.67 | Using where; Using index |
+----+-------------+--------+------------+-------+-----------------------+-----------------------+---------+------+------+----------+--------------------------+
```

* **原因**：查询只涉及索引字段 name，无需回表操作，因此优化器选择使用覆盖索引。

***

#### 2. 修改字段为允许 NULL 后的查询行为

将字段 name 修改为允许 NULL，并更新部分数据。

```plsql
ALTER TABLE staffs MODIFY name VARCHAR(24) DEFAULT NULL COMMENT '姓名';

-- 更新部分数据
UPDATE staffs SET name = NULL WHERE id = 2;

-- 查看表数据
SELECT * FROM staffs;
----+------+-----+---------+---------------------+
| id | name | age | pos     | add_time            |
+----+------+-----+---------+---------------------+
|  1 | z3   |  22 | manager | 2024-12-17 16:47:45 |
|  2 | NULL |  23 | dev     | 2024-12-17 16:47:45 |
|  3 | 2000 |  23 | dev     | 2024-12-17 16:47:45 |
+----+------+-----+---------+---------------------+
```

##### 查询 1：IS NULL

```plsql
EXPLAIN SELECT * FROM staffs WHERE name IS NULL;
```

**结果**：

* 查询条件 IS NULL 使用了索引。
* 执行计划显示：

```plsql
+----+-------------+--------+------------+------+-----------------------+-----------------------+---------+-------+------+----------+-----------------------+
| id | select_type | table  | partitions | type | possible_keys         | key                   | key_len | ref   | rows | filtered | Extra                 |
+----+-------------+--------+------------+------+-----------------------+-----------------------+---------+-------+------+----------+-----------------------+
|  1 | SIMPLE      | staffs | NULL       | ref  | idx_staffs_nameAgePos | idx_staffs_nameAgePos | 75      | const |    1 |   100.00 | Using index condition |
+----+-------------+--------+------------+------+-----------------------+-----------------------+---------+-------+------+----------+-----------------------+
```

* **原因**：字段 name 允许为 NULL，且存在 NULL 值，优化器选择使用索引扫描匹配 NULL 值的记录。

##### 查询 2：IS NOT NULL

```plsql
EXPLAIN SELECT * FROM staffs WHERE name IS NOT NULL;
```

**结果**：

* 查询条件 IS NOT NULL 使用了索引。
* 执行计划显示：

```plsql
+----+-------------+--------+------------+-------+-----------------------+-----------------------+---------+------+------+----------+-----------------------+
| id | select_type | table  | partitions | type  | possible_keys         | key                   | key_len | ref  | rows | filtered | Extra                 |
+----+-------------+--------+------------+-------+-----------------------+-----------------------+---------+------+------+----------+-----------------------+
|  1 | SIMPLE      | staffs | NULL       | range | idx_staffs_nameAgePos | idx_staffs_nameAgePos | 75      | NULL |    2 |   100.00 | Using index condition |
+----+-------------+--------+------------+-------+-----------------------+-----------------------+---------+------+------+----------+-----------------------+
```

* **原因**：字段 name 允许为 NULL，优化器通过索引扫描匹配非 NULL 值的记录。

***

### 三、实验结论

1. **字段定义为\*\*\*\* ****NOT NULL**** \*\*\*\*时**：
   * 查询 IS NULL 被认为是 **Impossible WHERE**，不会走索引。
   * 查询 IS NOT NULL 通常不走索引，而是全表扫描。
   * 如果查询只涉及索引字段（覆盖索引场景），IS NOT NULL 查询可以走索引。
2. **字段允许为 NULL 时**：
   * 查询 IS NULL 和 IS NOT NULL 都可以走索引。
   * NULL 值分布占比会显著影响查询性能和索引使用。
3. **NULL 值分布占比的影响**：
   * 当 NULL 值占比较小时，IS NULL 查询更倾向于使用索引。
   * 当非 NULL 值占比较小时，IS NOT NULL 查询更倾向于使用索引。

***

### 四、优化建议

1. **合理设计字段属性**：
   * 如果字段不会存储 NULL 值，建议定义为 NOT NULL，以减少 NULL 值处理的开销。
   * 如果字段需要存储 NULL 值，确保查询条件能够充分利用索引。
2. **定期更新统计信息**：
   * 使用 ANALYZE TABLE 更新表的统计信息，确保优化器的成本估算更准确。

通过结合 NULL 值分布占比的分析，可以更好地理解 MySQL 优化器的行为，并设计合理的表结构和索引策略以提升查询性能。

### 五、 NULL 值分布占比对查询的影响

#### 1. 测试环境准备

创建测试表 test，并为 name 和 code 字段分别添加二级索引。

```plsql
CREATE TABLE test (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) DEFAULT NULL,
  code INT DEFAULT NULL
);

CREATE INDEX idx_name ON test(name);
CREATE INDEX idx_code ON test(code);
```

插入 150 万条数据，分别测试以下两种情况：

1. **name**** \*\*\*\*字段绝大多数为非 NULL，少量为 NULL**。
2. **code**** \*\*\*\*字段绝大多数为 NULL，少量为非 NULL**。

```plsql
DELIMITER //

-- 插入数据，name 字段绝大多数为非 NULL
CREATE PROCEDURE insert_data_name()
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i name 字段（绝大多数为非 NULL）

1. **查询\*\*\*\* ****name IS NULL**

```plsql
EXPLAIN SELECT * FROM test WHERE name IS NULL;
```

**结果**：走索引 idx_name。\ **原因**：name 字段中 NULL 值占比小，扫描行数较少，优化器认为使用索引成本更低。

2. **查询\*\*\*\* ****name IS NOT NULL**

```plsql
EXPLAIN SELECT * FROM test WHERE name IS NOT NULL;
```

**结果**：不走索引，进行全表扫描。\ **原因**：name 字段中非 NULL 值占比大，扫描行数接近全表，优化器认为全表扫描成本更低。

***

##### 2.2 code 字段（绝大多数为 NULL）

1. **查询\*\*\*\* ****code IS NOT NULL**

```plsql
EXPLAIN SELECT * FROM test WHERE code IS NOT NULL;
```

**结果**：走索引 idx_code。\ **原因**：code 字段中非 NULL 值占比小，扫描行数较少，优化器认为使用索引成本更低。

2. **查询\*\*\*\* ****code IS NULL**

```plsql
EXPLAIN SELECT * FROM test WHERE code IS NULL;
```

**结果**：走索引 idx_code。\ **原因**：优化器统计的 rows 值不准确，错误地认为使用索引扫描行数较少。

***

#### 3、原理分析

##### 1. NULL 在 B+ 树中的存储方式

* 在 MySQL 的二级索引中，NULL 被认为小于任何值，因此键值为 NULL 的行记录被存储在 B+ 树的最左侧。
* 查找 IS NULL 时，优化器会从 B+ 树的最左侧开始扫描，直到遇到非 NULL 值为止。

##### 2. 优化器的成本计算

* 优化器会根据统计信息估算扫描行数和成本，决定是否使用索引。
* 如果查询条件筛选出的行数占总行数的比例较大（如 IS NOT NULL 查询），优化器可能选择全表扫描。
* 如果统计信息不准确（如 rows 值估算错误），优化器可能错误地选择使用索引。

##### 3. 回表操作的影响

* 二级索引的叶子节点存储的是索引键值和主键值，查询 SELECT * 时需要通过主键值回表获取完整数据。
* 如果扫描的二级索引行数较多，回表次数也会增加，可能导致性能下降。

***

#### 4、优化建议

##### 1. 避免优化器误判

* 如果优化器误判导致查询性能下降，可以通过强制使用索引来验证：

```plsql
SELECT * FROM test FORCE INDEX (idx_name) WHERE name IS NULL;
```

##### 2. 减少回表操作

* 如果查询只需要索引字段，可以避免 SELECT *，改为只查询需要的字段：

```plsql
SELECT name FROM test WHERE name IS NULL;
```

##### 3. 使用覆盖索引

* 如果查询的字段都包含在索引中，可以通过覆盖索引优化查询性能：

```plsql
ALTER TABLE test ADD INDEX idx_name_code (name, code);
SELECT name, code FROM test WHERE name IS NULL;
```

##### 4. 更新统计信息

* 定期使用 ANALYZE TABLE 更新表的统计信息，确保优化器的成本估算更准确：

```plsql
ANALYZE TABLE test;
```

***

#### 5、总结

通过测试可以得出以下结论：

1. **字段中 NULL 值占比对索引使用有重要影响**：
   * NULL 值占比小，IS NULL 查询走索引，IS NOT NULL 查询可能全表扫描。
   * NULL 值占比大，IS NOT NULL 查询走索引，IS NULL 查询可能全表扫描。
2. **优化器的成本计算可能出现误判**：
   * 统计信息不准确时，优化器可能错误地选择使用索引。
3. **回表操作可能导致性能下降**：
   * 二级索引扫描行数过多时，回表成本可能高于全表扫描。

在实际开发中，可以通过强制索引、覆盖索引等方式优化查询性能，同时定期更新统计信息，避免优化器误判。


# 图解MySQL索引失效

在工作中，为了提高查询速度，我们通常会考虑为字段建立索引。然而，索引并不是万无一失的。即使建立了索引，并不意味着所有查询语句都能利用索引进行扫描。

如果不加注意，某些查询语句可能会导致索引失效，进而导致全表扫描。虽然查询结果可能正确，但性能却会显著下降。

今天，我们将探讨六种常见的索引失效场景，以帮助大家更好地优化查询性能。

![1740056605348-9a3a3b72-b974-4a61-9de6-bd441da7ec58.png](images/1740056605348-9a3a3b72-b974-4a61-9de6-bd441da7ec58.png)

# 索引存储结构（工欲善其事必先利其器）

在讲解失效场景之前，需要知道**索引的存储结构**，才能更好的理解索引失效的问题。

索引的存储结构与 MySQL 所使用的存储引擎密切相关，因为存储引擎负责将数据持久化到磁盘，不同的引擎采用不同的索引数据结构。

MySQL 的默认存储引擎为 InnoDB，它使用 B+ 树作为索引的数据结构。选择 B+ 树作为索引结构的原因在于其高效的查找和插入性能。

在创建表时，InnoDB 存储引擎会默认创建主键索引，即聚簇索引，而其他的索引则为二级索引。

与 InnoDB 不同，MyISAM 存储引擎支持多种索引数据结构，包括 B+ 树索引、R 树索引和全文索引。

在 MyISAM 中，创建表时默认使用 B+ 树作为主键索引。

尽管 InnoDB 和 MyISAM 都支持 B+ 树索引，但它们的数据存储结构实现不同：

* **InnoDB**：B+ 树索引的叶子节点直接保存数据本身。
* **MyISAM**：B+ 树索引的叶子节点保存数据的物理地址。

接下来，将通过实例展示这两种存储引擎在索引存储结构上的区别。

这里有一张 t\_user 表，其中 id 字段为主键索引，其他都是普通字段。

![1740031673415-b7b4cbde-a602-402e-93e0-790ff58cd27d.png](images/1740031673415-b7b4cbde-a602-402e-93e0-790ff58cd27d.png)

## MyISAM 存储引擎

B+ 树索引的叶子节点保存数据的物理地址，即用户数据的指针

![1740031730722-2a23c448-2170-44c7-b135-e1a37d175aa9.png](images/1740031730722-2a23c448-2170-44c7-b135-e1a37d175aa9.png)

## InnoDB 存储引擎

B+ 树索引的叶子节点保存数据本身

![1740031994033-a85c76c1-3ce1-4aae-9c7f-3fd89243bf8d.jpeg](images/1740031994033-a85c76c1-3ce1-4aae-9c7f-3fd89243bf8d.jpeg)

InnoDB 存储引擎根据索引类型的不同，可分为**聚簇索引**和**二级索引**（上图展示了聚簇索引）。

它们的主要区别在于

* **聚簇索引**的叶子节点直接存储实际数据，包含所有完整的用户数据；
* **二级索引**的叶子节点则存储主键值，而非实际数据。

这种结构差异对数据检索性能有重要影响。

如果将 name 字段设置为普通索引，那么这个二级索引长下图这样

![1740033141687-8dfee1f9-f26b-42bf-9353-06b5f0f6da72.png](images/1740033141687-8dfee1f9-f26b-42bf-9353-06b5f0f6da72.png)

```plsql
CREATE TABLE t_user (
  id INT PRIMARY KEY,
  name VARCHAR(255),
  age INT,
  address VARCHAR(255)
);

INSERT INTO t_user (id, name, age, address) VALUES
(1, '张某', 26, '北京市海淀区'),
(2, '林某', 18, '深圳市南山区'),
(3, '陈某', 30, '广州市海珠区'),
(4, '周某', 34, '深圳市南山区'),
(5, '曾某', 25, '上海市松江区'),
(6, '黄某', 28, '深圳市宝安区'),
(7, '谢某', 38, '北京市海淀区'),
(8, '钟某', 23, '广州市海珠区'),
(9, '吴某', 28, '上海市浦东新区');

ALTER TABLE t_user ADD INDEX idx_name (name);
```

了解了InnoDB存储引擎的聚簇索引和二级索引的存储结构后，我们来看几个查询示例，以理解查询过程中如何选择索引类型。

### 主键索引查询

当我们使用主键索引字段进行查询时，如果数据在聚簇索引的叶子节点上，查询则会在B+树中直接找到对应的节点并读取数据。例如：

```plsql
// id字段为主键索引
SELECT * FROM t_user WHERE id=1;
```

### 二级索引查询（回表与覆盖索引）

使用二级索引字段查询时，若数据在聚簇索引的叶子节点上，查询需要检索两个B+树：

1. 首先在二级索引的B+树中找到叶子节点并获取主键值；
2. 然后使用主键值在聚簇索引的B+树中找到对应节点，读取数据。

这个过程称为“**回表**”，例如：

```plsql
// name字段为二级索引
SELECT * FROM t_user WHERE name="林某";
```

如果查询数据在二级索引的叶子节点上，则只需在二级索引的B+树中找到节点并直接读取数据，这称为“**覆盖索引**”。例如：

```plsql
// name字段为二级索引
SELECT id FROM t_user WHERE name="林某";
```

以上查询示例展示了如何通过索引列进行条件查询，但这并不意味着每次查询都能有效利用索引。

接下来，我们将探讨哪些情况下会导致索引失效，从而出现全表扫描的现象。

**（**所有演示都基于 **MySQL ****8.2****）**

# 索引失效场景

## 对索引使用左或者左右模糊匹配

在使用LIKE关键字进行模糊匹配时，如LIKE '%xx'或LIKE '%xx%'，都会导致索引失效，从而引发全表扫描。

例如，以下查询用于查找名称以「林」结尾的用户：

```plsql
// name字段为二级索引
SELECT * FROM t_user WHERE name LIKE '%林';
```

![1740034430544-d88f2fe3-931d-4991-be39-35b4b064ae1c.png](images/1740034430544-d88f2fe3-931d-4991-be39-35b4b064ae1c.png)

在这个查询的执行计划中，type=ALL表示全表扫描，表明未使用索引。相反，如果查询名称以「林」开头的用户：

```plsql
// name字段为二级索引
SELECT * FROM t_user WHERE name LIKE '林%';
```

![1740034408120-11da7ced-273c-4a6c-8fe3-b3bdf3024caa.png](images/1740034408120-11da7ced-273c-4a6c-8fe3-b3bdf3024caa.png)

此时，执行计划中的type=range表示使用了索引，key=index_name则确认了实际使用了索引。

那么，**为什么使用****LIKE****进行左模糊匹配会导致无法使用索引呢？**

这是因为B+树索引是根据索引值有序存储的，仅能支持前缀比较。

![1740034728564-2274c115-81e0-4b8b-8177-e07f14d5c081.png](images/1740034728564-2274c115-81e0-4b8b-8177-e07f14d5c081.png)

举个例子，假设我们查询以「林」为前缀的名称。查询过程如下：

```
1. 比较首节点的索引值：若「林」的拼音在某些节点中 介于「陈」和「周」之间，则继续查找下一个节点。
2. 依此类推，直到找到符合前缀的叶子节点，并读取相应数据。
```

如果查询条件是LIKE '%林'，因无法确定从哪个索引值开始比较，导致必须进行全表扫描。

## 对索引使用函数

在使用MySQL时，我们常常依赖内置函数来获取所需的查询结果。

然而，需要特别注意的是，如果在查询条件中对索引字段**使用了函数，这通常会导致索引失效，从而导致全表扫描**。

例如，以下查询语句中，length(name)函数被应用于name字段。

在执行计划中，如果显示type=ALL，这意味着数据库必须扫描整个表来满足查询条件：

```plsql
-- name字段为二级索引
SELECT * FROM t_user WHERE LENGTH(name) = 2;
```

![1740035475585-864cf8c7-d973-41a3-aec5-6507a26e299c.png](images/1740035475585-864cf8c7-d973-41a3-aec5-6507a26e299c.png)

那么，**为什么在对索引使用函数时会出现这种情况呢？**

关键在于，索引存储的是字段的原始值，而不是经过函数处理后的计算结果，这使得数据库无法有效利用索引。

不过，从MySQL 8.0版本开始，数据库引入了函数索引这一特性，允许我们针对函数计算结果建立索引。也就是说，索引的值可以是某个函数计算后的结果，这样就可以通过索引来快速查询所需数据。

例如，我们可以使用以下语句创建一个名为idx_name_length的索引，该索引对应于length(name)的计算结果：

```plsql
ALTER TABLE t_user ADD KEY idx_name_length ((LENGTH(name)));
```

![1740035407553-dd01ec54-91c2-4ce1-a67b-24a73fa9a3c6.png](images/1740035407553-dd01ec54-91c2-4ce1-a67b-24a73fa9a3c6.png)

在这种情况下，当我们使用类似的查询时，数据库将能够利用索引来加速查询过程。

## 对索引进行表达式计算

在查询条件中进行表达式计算通常会导致无法使用索引。

举个例子，以下查询语句在执行计划中显示为类型 ALL，表明使用了全表扫描：

```plsql
EXPLAIN SELECT * FROM t_user WHERE id + 1 = 10;
```

![1740035749126-083343b9-57a0-43d0-9bcd-d738c5e51803.png](images/1740035749126-083343b9-57a0-43d0-9bcd-d738c5e51803.png)

然而，如果将查询条件修改为 WHERE id = 10 - 1，则可以利用索引进行查询。

![1740035775582-79d074dd-f86f-4c04-9737-ddaae19e741a.png](images/1740035775582-79d074dd-f86f-4c04-9737-ddaae19e741a.png)

**为什么表达式计算会使索引失效呢？**

原因与对索引使用函数类似，索引中保存的是字段的原始值，而不是经过计算的结果，因此数据库必须先取出字段所有的值，然后逐个进行计算，从而导致全表扫描。

## 对索引隐式类型转换

如果索引字段是字符串类型，但是在条件查询中，输入的参数是整型的话，查看执行计划结果可以发现这条语句会走全表扫描。

在t_user表中，我增加了一个phone字段，该字段为二级索引，类型为VARCHAR。

```plsql
-- 增加 phone 字段并设置为二级索引
ALTER TABLE t_user
ADD COLUMN phone VARCHAR(30),
ADD INDEX idx_phone (phone);

-- 更新 phone 字段的数据示例
UPDATE t_user SET phone = CONCAT('1880000000', id);
```

在进行条件查询时，如果使用整型作为输入参数，如执行以下SQL：

```plsql
SELECT * FROM t_user WHERE phone = 18800000001;
```

![1740036645483-01557175-150e-4452-9f44-1c8deb8a59e8.png](images/1740036645483-01557175-150e-4452-9f44-1c8deb8a59e8.png)

则执行计划显示类型为ALL，这意味着会进行全表扫描。

然而，如果索引字段是整型，即使查询条件中使用字符串类型的参数，索引依然能够正常生效。例如，执行以下SQL：

```plsql
EXPLAIN SELECT * FROM t_user WHERE id = '1';
```

![1740036666448-be97f80d-187d-4c6b-88b5-e5eb34349e10.png](images/1740036666448-be97f80d-187d-4c6b-88b5-e5eb34349e10.png)

在这种情况下，查询仍然会走索引扫描。

这引发了一个问题：**为何第一个例子导致索引失效，而第二个例子却没有？**

要理解这一点，我们首先需要掌握MySQL的数据类型转换规则，它决定了在比较字符串和数字时，哪个会被转换。

用一个简单的方法来测试这一规则：选择 SELECT "10" > 9。

* 如果MySQL会自动将字符串转换为数字，那么这相当于执行 SELECT 10 > 9，结果应该是1，因为数字10确实大于9。
* 如果MySQL会将数字转换为字符串，那么这相当于执行 SELECT "10" > "9"。在这种情况下，字符串比较是逐位进行的，按照ASCII码进行比较。首先比较字符“1”和“9”，由于“1”的ASCII码小于“9”，所以结果应该是0。

![1740037362766-9af1b5e9-b46f-405e-b40a-6f60aebc9f0c.png](images/1740037362766-9af1b5e9-b46f-405e-b40a-6f60aebc9f0c.png)

根据测试结果，可以知道**MySQL在比较时，会将字符串转换为数字**。

**回到第一个查询：**

```plsql
SELECT * FROM t_user WHERE phone = 18800000001;
```

这里phone字段是字符串，因此MySQL会将其自动转换为数字，相当于执行：

```plsql
SELECT * FROM t_user WHERE phone = 18800000001;
等同于:
SELECT * FROM t_user WHERE CAST(phone AS SIGNED) = 18800000001;
```

如上所示，**CAST****函数在****phone****字段上被应用**，这就导致了对索引的使用失效。

**而在第二个例子中：**

```plsql
SELECT * FROM t_user WHERE id = '1';
```

id字段是整型，字符串参数也需要转换为数字，相当于执行：

```plsql
SELECT * FROM t_user WHERE id = '1';
等同于:
SELECT * FROM t_user WHERE id = CAST('1' AS SIGNED);
```

在这种情况下，**CAST****函数应用于输入参数**，确保了索引的有效使用，从而实现索引扫描。

## 联合索引非最左匹配

在数据库索引中，对主键字段建立的索引称为**聚簇索引**，而对普通字段建立的索引则称为**二级索引**。

当**多个普通字段组合**在一起创建索引时，称为**联合索引**（或组合索引）。

创建联合索引时，字段的顺序至关重要。例如，联合索引 (a, b, c) 与 (c, b, a) 在使用时会有显著不同。为了有效利用联合索引，必须遵循最左匹配原则，即查询条件必须从最左边的字段开始匹配。

例如，对于 (a, b, c) 的联合索引 ，以下查询能够成功匹配联合索引：

* WHERE a=3
* WHERE a=3 AND b=5 AND c=4
* WHERE a=3 AND b=5

然而，若查询条件不符合最左匹配原则，索引将失效，如以下查询：

* WHERE b=5
* WHERE c=4
* WHERE b=5 AND c=4

还有一种特殊情况是 WHERE a=3 AND c=4。特殊之处在于不同版本的 MySQL，处理方法有所不同。

* 在 MySQL 5.5 中，虽然会使用索引定位到主键，但仍需回表读取数据。
* 而自 MySQL 5.6 以来，引入的**索引下推功能**使得条件判断在存储引擎层进行，从而减少了回表次数，提高了性能。

```plsql
CREATE TABLE test_index (
    id INT AUTO_INCREMENT PRIMARY KEY,
    a INT,
    b INT,
    c INT,
    d INT,
    e INT,
    f INT,
    INDEX idx_abc (a, b, c)
);

INSERT INTO test_index (a, b, c, d, e, f) VALUES
(1, 10, 100, 5, 15, 25),
(2, 20, 200, 6, 16, 26),
(3, 5, 4, 7, 17, 27),
(4, 40, 400, 8, 18, 28),
(5, 50, 500, 9, 19, 29),
(6, 60, 600, 10, 20, 30),
(7, 70, 700, 11, 21, 31),
(8, 80, 800, 12, 22, 32),
(9, 90, 900, 13, 23, 33);
```

```plsql
// 联合索引 (a, b, c)
SELECT * FROM test_index WHERE a = 3 and c = 2;
```

![1740049981230-6b56c4a8-cf21-4204-a70a-7688fb92991a.png](images/1740049981230-6b56c4a8-cf21-4204-a70a-7688fb92991a.png)

例如，通过执行计划中的 Extra=Using index condition 可以确认索引下推的使用。

**为什么联合索引不遵循最左匹配原则就会失效？**

**联合索引内部的排序是基于第一列。只有当第一列的数据相同，才会依据第二列排序。**

因此，若希望利用联合索引中尽可能多的列，查询条件中的各列必须从最左侧开始连续匹配。

## WHERE 子句中的 OR

如果在 WHERE 子句中，OR 前的条件列是索引列，而 OR 后的条件列不是索引列，将会面临全表扫描的问题。

举个例子，考虑以下查询语句：

```plsql
// id 是主键且为索引列，age 是普通列
SELECT * FROM t_user WHERE id = 1 OR age = 18;
```

![1740040257048-aa5689f4-0a8b-4246-8155-8f18c87ce8ae.png](images/1740040257048-aa5689f4-0a8b-4246-8155-8f18c87ce8ae.png)

执行计划显示，该查询会执行全表扫描，因为 OR 的逻辑是，只需满足任一条件即可。

因此，当有一个条件不使用索引时，索引的存在毫无意义。

**解决这个问题很简单**：将 age 字段设置为索引。这样，查询将会充分利用索引，避免全表扫描。

```plsql
ALTER TABLE t_user ADD INDEX idx_age (age);
```

![1740040388383-20ed59b6-7932-4ddc-97a4-07ec44cda3ee.png](images/1740040388383-20ed59b6-7932-4ddc-97a4-07ec44cda3ee.png)

优化后，如果执行计划变为“type=index merge”，则意味着数据库分别对 id 和 age 条件进行了索引扫描，并将结果合并，从而提高了查询效率。

通过这种方式，可以显著提升查询性能，减少数据库的负载。

# 总结

在数据库优化中，索引的有效使用至关重要。

1. 使用模糊匹配（如 LIKE %xx 或 LIKE %xx%）时，索引将失效。
2. 在查询条件中对索引列应用函数会导致索引失效。
3. 对索引列进行表达式计算同样无法使用索引。
4. 当字符串与数字进行比较时，MySQL会自动将字符串转换为数字，这种隐式类型转换会导致索引失效。
5. 联合索引的使用必须遵循最左匹配原则，否则会导致索引失效。
6. 在 WHERE 子句中，如果 OR 前的条件是索引列而 OR 后的条件不是，索引也会失效。


# MySQL自增id用完怎么办？

MySQL 里有很多自增的 id，每个自增 id 都是定义了初始值，然后不停地往上加步长。虽然自然数是没有上限的，但是在计算机里，只要定义了表示这个数的字节长度，那它就有上限。比如，无符号整型 (unsigned int) 是 4 个字节，上限就是2的32次方。

既然自增 id 有上限，就有可能被用完。但是，自增 id 用完了会怎么样呢？

今天这篇文章，我们就来看看 MySQL 里面的几种自增 id，一起分析一下它们的值达到上限以后，会出现什么情况。

### 表定义自增值 ID

说到自增 id，你第一个想到的应该就是表结构定义里的自增字段，表定义的自增值达到上限后的逻辑是：再申请下一个 id 时，得到的值保持不变。

我们可以通过下面这个语句序列验证一下：

```java
create table t(
    id int unsigned auto_increment primary key
) auto_increment=4294967295;

insert into t values(null);

// 成功插入一行 4294967295
show create table t;
/* CREATE TABLE `t` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4294967295;
*/

insert into t values(null);
//Duplicate entry '4294967295' for key 'PRIMARY'
```

可以看到，第一个 insert 语句插入数据成功后，这个表的 AUTO_INCREMENT 没有改变（还是 4294967295），就导致了第二个 insert 语句又拿到相同的自增 id 值，再试图执行插入语句，报主键冲突错误。

2的32次方不是一个特别大的数，对于一个频繁插入删除数据的表来说，是可能会被用完的。因此在建表的时候你需要考察你的表是否有可能达到这个上限，如果有可能，就应该创建成 8 个字节的 bigint unsigned。

### InnoDB 系统自增 row\_id

如果你创建的 InnoDB 表没有指定主键，那么 InnoDB 会给你创建一个不可见的，长度为 6 个字节的 row\_id。

InnoDB 维护了一个全局的 dict\_sys.row\_id 值，所有无主键的 InnoDB 表，每插入一行数据，都将当前的 dict\_sys.row\_id 值作为要插入数据的 row\_id，然后把 dict\_sys.row\_id 的值加 1。

实际上，在代码实现时 row\_id 是一个长度为 8 字节的无符号长整型 (bigint unsigned)。但是，InnoDB 在设计时，给 row\_id 留的只是 6 个字节的长度，这样写到数据表中时只放了最后 6 个字节，所以 row\_id 能写到数据表中的值，就有两个特征：

* row\_id 写入表中的值范围，是从 0 到 2^48-1；
* 当 dict\_sys.row\_id=2^48时，如果再有插入数据的行为要来申请 row\_id，拿到以后再取最后 6 个字节的话就是 0。

也就是说，写入表的 row\_id 是从 0 开始到 2^48-1。**达到上限后，下一个值就是 0**，**然后继续循环**。

当然，2^48-1 这个值本身已经很大了，但是如果一个 MySQL 实例跑得足够久的话，还是可能达到这个上限的。在 InnoDB 逻辑里，申请到 row\_id=N 后，就将这行数据写入表中；如果表中已经存在 row\_id=N 的行，新写入的行就会覆盖原有的行。

要验证这个结论的话，你可以通过 gdb 修改系统的自增 row\_id 来实现。注意，用 gdb 改变量这个操作是为了便于我们复现问题，只能在测试环境使用。

* 命令

```java
mysql > create table `t_2`(a int) engine = innodb;

gdb -p  -ex 'p dict_sys.row_id=1' --batch

gdb -p 10674 -ex 'p dict_sys.row_id=1' --batch

mysql> insert into `t_2` value(1);

gdb -p  -ex 'p dict_sys.row_id=281474976710656' --batch

gdb -p 10674 -ex 'p dict_sys.row_id=281474976710656' --batch

mysql> insert into `t_2` value(2);

mysql> insert into `t_2` value(3);

mysql> select * from `t_2`;
```

* row\_id 用完的效果验证

![1686210870831-c41e1d5d-918c-4485-9f03-132c86d6ff9d.png](images/1686210870831-c41e1d5d-918c-4485-9f03-132c86d6ff9d.png)

可以看到，在我用 gdb 将 dict\_sys.row\_id 设置为 2^48之后，再插入的 a=2 的行会出现在表 t 的第一行，因为这个值的 row\_id=0。之后再插入的 a=3 的行，由于 row\_id=1，就覆盖了之前 a=1 的行，因为 a=1 这一行的 row\_id 也是 1。

从这个角度看，我们还是应该在 InnoDB 表中主动创建自增主键。因为，表自增 id 到达上限后，再插入数据时报主键冲突错误，是更能被接受的。

毕竟覆盖数据，就意味着数据丢失，影响的是数据可靠性；报主键冲突，是插入失败，影响的是可用性。而一般情况下，可靠性优先于可用性。

### x\_id

我和你介绍 redo log 和 binlog 相配合的时候，提到了它们有一个共同的字段叫作 Xid。它在 MySQL 中是用来对应事务的。

那么，Xid 在 MySQL 内部是怎么生成的呢？

MySQL 内部维护了一个全局变量 global\_query\_id，每次执行语句的时候将它赋值给 Query\_id，然后给这个变量加 1。如果当前语句是这个事务执行的第一条语句，那么 MySQL 还会同时把 Query\_id 赋值给这个事务的 Xid。

而 global\_query\_id 是一个纯内存变量，重启之后就清零了。所以你就知道了，在同一个数据库实例中，不同事务的 Xid 也是有可能相同的。

但是 MySQL 重启之后会重新生成新的 binlog 文件，这就保证了，同一个 binlog 文件里，Xid 一定是惟一的。

虽然 MySQL 重启不会导致同一个 binlog 里面出现两个相同的 Xid，但是如果 global\_query\_id 达到上限后，就会继续从 0 开始计数。从理论上讲，还是就会出现同一个 binlog 里面出现相同 Xid 的场景。

因为 global\_query\_id 定义的长度是 8 个字节，这个自增值的上限是 2^64-1。要出现这种情况，必须是下面这样的过程：

1. 执行一个事务，假设 Xid 是 A；
2. 接下来执行 2^64次查询语句，让 global\_query\_id 回到 A；
3. 再启动一个事务，这个事务的 Xid 也是 A。

不过，2^64这个值太大了，大到你可以认为这个可能性只会存在于理论上。

### Innodb trx\_id

Xid 和 InnoDB 的 trx\_id 是两个容易混淆的概念。

Xid 是由 server 层维护的。InnoDB 内部使用 Xid，就是为了能够在 InnoDB 事务和 server 之间做关联。但是，InnoDB 自己的 trx\_id，是另外维护的。

其实，你应该非常熟悉这个 trx\_id。它就是在我们在第 8 篇文章\[《事务到底是隔离的还是不隔离的？》]中讲事务可见性时，用到的事务 id（transaction id）。

InnoDB 内部维护了一个 max\_trx\_id 全局变量，每次需要申请一个新的 trx\_id 时，就获得 max\_trx\_id 的当前值，然后并将 max\_trx\_id 加 1。

InnoDB 数据可见性的核心思想是：每一行数据都记录了更新它的 trx\_id，当一个事务读到一行数据的时候，判断这个数据是否可见的方法，就是通过事务的一致性视图与这行数据的 trx\_id 做对比。

对于正在执行的事务，你可以从 information\_schema.innodb\_trx 表中看到事务的 trx\_id。

我在上一篇文章的末尾留给你的思考题，就是关于从 innodb\_trx 表里面查到的 trx\_id 的。现在，我们一起来看一个事务现场：

![1686212114725-93a4332c-ec62-4363-a03e-cac96101f4cd.png](images/1686212114725-93a4332c-ec62-4363-a03e-cac96101f4cd.png)\ session B 里，我从 innodb\_trx 表里查出的这两个字段，第二个字段 trx\_mysql\_thread\_id 就是线程 id。显示线程 id，是为了说明这两次查询看到的事务对应的线程 id 都是 5，也就是 session A 所在的线程。

可以看到，T2 时刻显示的 trx\_id 是一个很大的数；T4 时刻显示的 trx\_id 是 1289，看上去是一个比较正常的数字。这是什么原因呢？

实际上，在 T1 时刻，session A 还没有涉及到更新，是一个只读事务。而对于只读事务，InnoDB 并不会分配 trx\_id。也就是说：

1. 在 T1 时刻，trx\_id 的值其实就是 0。而这个很大的数，只是显示用的。一会儿我会再和你说说这个数据的生成逻辑。
2. 直到 session A 在 T3 时刻执行 insert 语句的时候，InnoDB 才真正分配了 trx\_id。所以，T4 时刻，session B 查到的这个 trx\_id 的值就是 1289。

需要注意的是，除了显而易见的修改类语句外，如果在 select 语句后面加上 for update，这个事务也不是只读事务。

那么，**T2 时刻查到的这个很大的数字是怎么来的呢？**

其实，这个数字是每次查询的时候由系统临时计算出来的。它的算法是：把当前事务的 trx 变量的指针地址转成整数，再加上 2^48。使用这个算法，就可以保证以下两点：

1. 因为同一个只读事务在执行期间，它的指针地址是不会变的，所以不论是在 innodb\_trx 还是在 innodb\_locks 表里，同一个只读事务查出来的 trx\_id 就会是一样的。
2. 如果有并行的多个只读事务，每个事务的 trx 变量的指针地址肯定不同。这样，不同的并发只读事务，查出来的 trx\_id 就是不同的。

那么，**为什么还要再加上 2^48呢？**

在显示值里面加上 2^48，目的是要保证只读事务显示的 trx\_id 值比较大，正常情况下就会区别于读写事务的 id。但是，trx\_id 跟 row\_id 的逻辑类似，定义长度也是 8 个字节。因此，在理论上还是可能出现一个读写事务与一个只读事务显示的 trx\_id 相同的情况。不过这个概率很低，并且也没有什么实质危害，可以不管它。

另一个问题是，**只读事务不分配 trx\_id，有什么好处呢？**

* 一个好处是，这样做可以减小事务视图里面活跃事务数组的大小。因为当前正在运行的只读事务，是不影响数据的可见性判断的。所以，在创建事务的一致性视图时，InnoDB 就只需要拷贝读写事务的 trx\_id。
* 另一个好处是，可以减少 trx\_id 的申请次数。在 InnoDB 里，即使你只是执行一个普通的 select 语句，在执行过程中，也是要对应一个只读事务的。所以只读事务优化后，普通的查询语句不需要申请 trx\_id，就大大减少了并发事务申请 trx\_id 的锁冲突。

由于只读事务不分配 trx\_id，一个自然而然的结果就是 trx\_id 的增加速度变慢了。

但是，max\_trx\_id 会持久化存储，重启也不会重置为 0，那么从理论上讲，只要一个 MySQL 服务跑得足够久，就可能出现 max\_trx\_id 达到 2^48-1 的上限，然后从 0 开始的情况。

当达到这个状态后，MySQL 就会持续出现一个脏读的 bug，我们来复现一下这个 bug。

首先我们需要把当前的 max\_trx\_id 先修改成 2^48-1。注意：这个 case 里使用的是可重复读隔离级别。具体的操作流程如下：

![1686212148301-2097eafb-2389-4b0a-9626-f5aca4927afa.png](images/1686212148301-2097eafb-2389-4b0a-9626-f5aca4927afa.png)

由于我们已经把系统的 max\_trx\_id 设置成了 2^48-1，所以在 session A 启动的事务 TA 的低水位就是 2^48-1。

在 T2 时刻，session B 执行第一条 update 语句的事务 id 就是 2^48-1，而第二条 update 语句的事务 id 就是 0 了，这条 update 语句执行后生成的数据版本上的 trx\_id 就是 0。

在 T3 时刻，session A 执行 select 语句的时候，判断可见性发现，c=3 这个数据版本的 trx\_id，小于事务 TA 的低水位，因此认为这个数据可见。

但，这个是脏读。

由于低水位值会持续增加，而事务 id 从 0 开始计数，就导致了系统在这个时刻之后，所有的查询都会出现脏读的。

并且，MySQL 重启时 max\_trx\_id 也不会清 0，也就是说重启 MySQL，这个 bug 仍然存在。

那么，**这个 bug 也是只存在于理论上吗？**

假设一个 MySQL 实例的 TPS 是每秒 50 万，持续这个压力的话，在 17.8 年后，就会出现这个情况。如果 TPS 更高，这个年限自然也就更短了。但是，从 MySQL 的真正开始流行到现在，恐怕都还没有实例跑到过这个上限。不过，这个 bug 是只要 MySQL 实例服务时间够长，就会必然出现的。

### thread\_id

接下来，我们再看看线程 id（thread\_id）。其实，线程 id 才是 MySQL 中最常见的一种自增 id。平时我们在查各种现场的时候，show processlist 里面的第一列，就是 thread\_id。

thread\_id 的逻辑很好理解：系统保存了一个全局变量 thread\_id\_counter，每新建一个连接，就将 thread\_id\_counter 赋值给这个新连接的线程变量。

thread\_id\_counter 定义的大小是 4 个字节，因此达到 2^32-1 后，它就会重置为 0，然后继续增加。但是，你不会在 show processlist 里看到两个相同的 thread\_id。

这，是因为 MySQL 设计了一个唯一数组的逻辑，给新线程分配 thread\_id 的时候，逻辑代码是这样的：

```bash
do {
  new_id= thread_id_counter++;
} while (!thread_ids.insert_unique(new_id).second);
```

这个代码逻辑简单而且实现优雅，相信你一看就能明白。

### 总结

数据库系统作为一个可能需要 7\*24 小时全年无休的服务，考虑这些边界是非常有必要的。

每种自增 id 有各自的应用场景，在达到上限后的表现也不同：

1. 表的自增 id 达到上限后，再申请时它的值就不会改变，进而导致继续插入数据时报主键冲突的错误。
2. row\_id 达到上限后，则会归 0 再重新递增，如果出现相同的 row\_id，后写的数据会覆盖之前的数据。

当然，在 MySQL 里还有别的自增 id，比如 x\_id、thread\_id、table\_id等等，如果用完了又会发生什么呢？大家可以一起在评论区咱们一起聊聊。下期再会~


# MySQLInnoDB的MVCC实现机制

> MySQL 中InnoDB中实现了事务（多版本并发控制MVCC+锁）， 其中通过MVCC解决隔离性问题。具体而言，**MVCC就是为了实现读-写冲突不加锁**，而这个读指的就是**快照读**, 而非当前读，当**前读实际上是一种加锁的操作，是悲观锁的实现**; 本文带你理解InnoDB中MVCC的实现机制。
>

## 前提概要
### 什么是MVCC?
> MVCC，全称Multi-Version Concurrency Control，即多版本并发控制。MVCC是一种并发控制的方法，一般在数据库管理系统中，实现对数据库的并发访问，在编程语言中实现事务内存。
>

MVCC在MySQL InnoDB中的实现主要是为了提高数据库并发性能，用更好的方式去处理读-写冲突，做到即使有读写冲突时，也能做到不加锁，非阻塞并发读

### 什么是当前读和快照读？
> 在学习MVCC多版本并发控制之前，我们必须先了解一下，什么是MySQL InnoDB下的当前读和快照读?
>

+ **当前读**

像select lock in share mode(共享锁), select for update ; update, insert ,delete(排他锁)这些操作都是一种当前读，为什么叫当前读？就是它读取的是记录的最新版本，读取时还要保证其他并发事务不能修改当前记录，会对读取的记录进行加锁

+ **快照读**

像不加锁的select操作就是快照读，即不加锁的非阻塞读；快照读的前提是隔离级别不是串行级别，串行级别下的快照读会退化成当前读；之所以出现快照读的情况，是基于提高并发性能的考虑，快照读的实现是基于多版本并发控制，即MVCC,可以认为MVCC是行锁的一个变种，但它在很多情况下，避免了加锁操作，降低了开销；既然是基于多版本，即快照读可能读到的并不一定是数据的最新版本，而有可能是之前的历史版本

> 说白了**MVCC就是为了实现读-写冲突不加锁**，而这个读指的就是**快照读**, 而非当前读，当**前读实际上是一种加锁的操作，是悲观锁的实现**
>

### 当前读，快照读和MVCC的关系
> 当前读，快照读和MVCC之间是什么关系呢？
>

+ 准确的说，MVCC多版本并发控制指的是 “维持一个数据的多个版本，使得读写操作没有冲突” 这么一个概念。仅仅是一个理想概念
+ 而在MySQL中，实现这么一个MVCC理想概念，我们就需要MySQL提供具体的功能去实现它，而快照读就是MySQL为我们实现MVCC理想模型的其中一个具体非阻塞读功能。而相对而言，当前读就是悲观锁的具体功能实现
+ 要说的再细致一些，快照读本身也是一个抽象概念，再深入研究。MVCC模型在MySQL中的具体实现则是由 **4个隐式字段**，**undo日志** ，**Read View** 等去完成的，具体可以看下面的MVCC实现原理

### MVCC能解决什么问题，好处是？
#### 数据库并发场景?
有三种, 分别为：

+ **读-读**：不存在任何问题，也不需要并发控制
+ **读-写**：有线程安全问题，可能会造成事务隔离性问题，可能遇到脏读，幻读，不可重复读
+ **写-写**：有线程安全问题，可能会存在更新丢失问题，比如第一类更新丢失，第二类更新丢失

#### MVCC带来的好处是？
多版本并发控制（MVCC）是一种用来解决读-写冲突的无锁并发控制，也就是为事务分配单向增长的时间戳，为每个修改保存一个版本，版本与事务时间戳关联，读操作只读该事务开始前的数据库的快照。 所以MVCC可以为数据库解决以下问题

在并发读写数据库时，可以做到在读操作时不用阻塞写操作，写操作也不用阻塞读操作，提高了数据库并发读写的性能 同时还可以解决脏读，幻读，不可重复读等事务隔离问题，但不能解决更新丢失问题

### 小结一下
总之，MVCC就是因为大牛们，不满意只让数据库采用悲观锁这样性能不佳的形式去解决读-写冲突问题，而提出的解决方案，所以在数据库中，因为有了MVCC，所以我们可以形成两个组合：

+ **MVCC + 悲观锁** MVCC解决读写冲突，悲观锁解决写写冲突
+ **MVCC + 乐观锁** MVCC解决读写冲突，乐观锁解决写写冲突

这种组合的方式就可以最大程度的提高数据库并发性能，并解决读写冲突，和写写冲突导致的问题

## MVCC的实现原理
> MVCC的目的就是多版本并发控制，在数据库中的实现，就是为了解决读写冲突，它的实现原理主要是依赖记录中的 **4个隐式字段**，**undo日志** ，**Read View** 来实现的。
>

### 隐式字段
每行记录除了我们自定义的字段外，还有数据库隐式定义的DB_TRX_ID,DB_ROLL_PTR,DB_ROW_ID等字段

+ **DB_ROW_ID** 6byte, 隐含的自增ID（隐藏主键），如果数据表没有主键，InnoDB会自动以DB_ROW_ID产生一个聚簇索引
+ **DB_TRX_ID** 6byte, 最近修改(修改/插入)事务ID：记录创建这条记录/最后一次修改该记录的事务ID
+ **DB_ROLL_PTR** 7byte, 回滚指针，指向这条记录的上一个版本（存储于rollback segment里）
+ **DELETED_BIT** 1byte, 记录被更新或删除并不代表真的删除，而是删除flag变了

![1729411583287-abf7dbac-91b8-459d-860e-6abd056b89c0.jpeg](images/1729411583287-abf7dbac-91b8-459d-860e-6abd056b89c0.jpeg)

如上图，DB_ROW_ID是数据库默认为该行记录生成的唯一隐式主键；DB_TRX_ID是当前操作该记录的事务ID； 而DB_ROLL_PTR是一个回滚指针，用于配合undo日志，指向上一个旧版本；delete flag没有展示出来。

### undo日志
InnoDB把这些为了回滚而记录的这些东西称之为undo log。这里需要注意的一点是，由于查询操作（SELECT）并不会修改任何用户记录，所以在查询操作执行时，并不需要记录相应的undo log。undo log主要分为3种：

+ **Insert undo log** ：插入一条记录时，至少要把这条记录的主键值记下来，之后回滚的时候只需要把这个主键值对应的记录删掉就好了。
+ **Update undo log**：修改一条记录时，至少要把修改这条记录前的旧值都记录下来，这样之后回滚时再把这条记录更新为旧值就好了。
+ **Delete undo log**：删除一条记录时，至少要把这条记录中的内容都记下来，这样之后回滚时再把由这些内容组成的记录插入到表中就好了。
    - 删除操作都只是设置一下老记录的DELETED_BIT，并不真正将过时的记录删除。
    - 为了节省磁盘空间，InnoDB有专门的purge线程来清理DELETED_BIT为true的记录。为了不影响MVCC的正常工作，purge线程自己也维护了一个read view（这个read view相当于系统中最老活跃事务的read view）;如果某个记录的DELETED_BIT为true，并且DB_TRX_ID相对于purge线程的read view可见，那么这条记录一定是可以被安全清除的。

对MVCC有帮助的实质是**update undo log** ，undo log实际上就是存在rollback segment中旧记录链，它的执行流程如下：

1. **比如有个事务插入persion表插入了一条新记录，记录如下，name为Jerry, age为24岁，隐式主键是1，事务ID和回滚指针，我们假设为NULL**

![1729167745367-dedf82f7-a96d-4661-8130-4c691ac34c92.png](images/1729167745367-dedf82f7-a96d-4661-8130-4c691ac34c92.png)

1. **现在来了一个事务1对该记录的name做出了修改，改为Tom**
    1. 在事务1修改该行(记录)数据时，数据库会先对该行加排他锁
    2. 然后把该行数据拷贝到undo log中，作为旧记录，即在undo log中有当前行的拷贝副本
    3. 拷贝完毕后，修改该行name为Tom，并且修改隐藏字段的事务ID为当前事务1的ID, 我们默认从1开始，之后递增，回滚指针指向拷贝到undo log的副本记录，即表示我的上一个版本就是它
    4. 事务提交后，释放锁	

![1729411112337-04d35703-7c00-45d7-a903-be3564277b60.jpeg](images/1729411112337-04d35703-7c00-45d7-a903-be3564277b60.jpeg)

1. **又来了个事务2修改person表的同一个记录，将age修改为30岁**
    1. 在事务2修改该行数据时，数据库也先为该行加锁
    2. 然后把该行数据拷贝到undo log中，作为旧记录，发现该行记录已经有undo log了，那么最新的旧数据作为链表的表头，插在该行记录的undo log最前面
    3. 修改该行age为30岁，并且修改隐藏字段的事务ID为当前事务2的ID, 那就是2，回滚指针指向刚刚拷贝到undo log的副本记录
    4. 事务提交，释放锁

![1729411108230-0a15d363-cdd3-4642-b620-6916fd91c7e6.jpeg](images/1729411108230-0a15d363-cdd3-4642-b620-6916fd91c7e6.jpeg)

从上面，我们就可以看出，不同事务或者相同事务的对同一记录的修改，会导致该记录的undo log成为一条记录版本线性表，即链表，undo log的链首就是最新的旧记录，链尾就是最早的旧记录（当然就像之前说的该undo log的节点可能是会purge线程清除掉，向图中的第一条insert undo log，其实在事务提交之后可能就被删除丢失了，不过这里为了演示，所以还放在这里）

### Read View(读视图)
> 什么是Read View，说白了Read View就是事务进行快照读操作的时候生产的读视图(Read View)，在该事务执行的快照读的那一刻，会生成数据库系统当前的一个快照，记录并维护系统当前活跃事务的ID(**当每个事务开启时(执行 SQL 的时候**)，都会被分配一个ID, 这个ID是递增的，所以最新的事务，ID值越大)
>

所以我们知道 Read View主要是用来做可见性判断的, 即当我们某个事务执行快照读的时候，对该记录创建一个Read View读视图，把它比作条件用来判断当前事务能够看到哪个版本的数据，即可能是当前最新的数据，也有可能是该行记录的undo log里面的某个版本的数据。

Read View遵循一个可见性算法，主要是将要被修改的数据的最新记录中的DB_TRX_ID（即当前事务ID）取出来，与系统当前其他活跃事务的ID去对比（由Read View维护），如果DB_TRX_ID跟Read View的属性做了某些比较，不符合可见性，那就通过DB_ROLL_PTR回滚指针去取出Undo Log中的DB_TRX_ID再比较，即遍历链表的DB_TRX_ID（从链首到链尾，即从最近的一次修改查起），直到找到满足特定条件的DB_TRX_ID, 那么这个DB_TRX_ID所在的旧记录就是当前事务能看见的最新老版本

> 那么这个判断条件是什么呢？
>

我们可以把Read View简单的理解成有四个全局属性

> + **trx_list** 未提交事务ID列表，用来维护Read View生成时刻系统正活跃的事务ID
> + **up_limit_id** 记录trx_list列表中事务ID最小的ID
> + **low_limit_id** ReadView生成时刻系统尚未分配的下一个事务ID，也就是目前已出现过的事务ID的最大值+1
> + **create_trx_id** 创建当前read view的事务ID
>

#### 比较规则
+ 首先比较 DB_TRX_ID == create_trx_id，如果等于代表当前 read view 是当前事务创建，能看到DB_TRX_ID 所在的记录。
+ 然后比较 DB_TRX_ID = low_limit_id，如果大于等于则代表DB_TRX_ID 所在的记录在Read View生成后才出现的（**未开始的事务**），那对当前事务肯定不可见，如果小于则进入下一个判断
+ 判断DB_TRX_ID 是否在活跃事务之中（**进行中的事务，可能存在已提交事务，因为存在事务处理速度差异**），如果在，则代表我Read View生成时刻，你这个事务还在活跃，还没有Commit，你修改的数据，当前事务也是看不见的；如果不在，则说明，你这个事务在Read View生成之前就已经Commit了，你修改的结果，当前事务是能看见的

### 整体流程
我们在了解了隐式字段，undo log， 以及Read View的概念之后，就可以来看看MVCC实现的整体流程是怎么样了

整体的流程是怎么样的呢？我们可以模拟一下

当事务2对某行数据执行了快照读，数据库为该行数据生成一个Read View读视图，假设当前事务ID为2，此时还有事务1和事务3在活跃中，事务4在事务2快照读前一刻提交更新了，所以Read View记录了系统当前活跃事务1，3的ID，维护在一个列表上，假设我们称为trx_list

| 事务1 | 事务2 | 事务3 | 事务4 |
| --- | --- | --- | --- |
| 事务开始 | 事务开始 | 事务开始 | 事务开始 |
| … | … | … | 修改且已提交 |
| 进行中 | 快照读 | 进行中 |  |
| … | … | … |  |

Read View不仅仅会通过一个列表**trx_list**来维护事务2执行快照读那刻系统正活跃的事务ID，

还会有两个属性**up_limit_id**（记录trx_list列表中事务ID最小的ID），**low_limit_id**(记录trx_list列表中下一个事务ID，也就是目前已出现过的事务ID的最大值+1)；

所以在这里例子中up_limit_id就是1，low_limit_id就是4 + 1 = 5，trx_list集合的值是1,3，Read View如下图

![1729167745766-8998d590-20e7-4356-b988-89669c435f87.png](images/1729167745766-8998d590-20e7-4356-b988-89669c435f87.png)

我们的例子中，只有事务4修改过该行记录，并在事务2执行快照读前，就提交了事务，所以当前该行当前数据的undo log如下图所示；

我们的事务2在快照读该行记录的时候，就会拿**该行记录的DB_TRX_ID**去跟**up_limit_id,low_limit_id和活跃事务ID列表(trx_list)进行比较**，判断当前事务2能看到该记录的版本是哪个。

![1729411101293-d6fa16ae-ed24-4be7-ac91-6ea27097f95d.jpeg](images/1729411101293-d6fa16ae-ed24-4be7-ac91-6ea27097f95d.jpeg)

所以先拿该记录DB_TRX_ID字段记录的事务ID 4去跟Read View的的up_limit_id比较

+ 判断 4 是否小于up_limit_id(1)，所以**不符合条件**
+ 继续判断 4 是否大于等于 low_limit_id(5)，也**不符合条件**
+ 最后判断 4 是否处于trx_list中的活跃事务, 发现事务ID为4的事务不在当前活跃事务列表中, 符合**可见性条件**
+ 所以事务 4 修改后提交的最新结果对事务2快照读时是可见的

因此事务2 能读到的最新数据记录是事务4所提交的版本，而事务4提交的版本也是全局角度上最新的版本。

![1729411094372-e4c23636-997d-4ecb-bcb4-4fdba40c848c.jpeg](images/1729411094372-e4c23636-997d-4ecb-bcb4-4fdba40c848c.jpeg)

也正是Read View生成时机的不同，从而造成RC,RR级别下快照读的结果的不同

## MVCC相关问题
### RR是如何在RC级的基础上解决不可重复读的？
当前读和快照读在RR级别下的区别：

表1:

![1729167746027-4e11ba99-a738-4947-a6b2-754a97b472fe.png](images/1729167746027-4e11ba99-a738-4947-a6b2-754a97b472fe.png)

表2:

![1729167746087-b436b11f-ed5c-4d88-b3f4-14392f990b9d.png](images/1729167746087-b436b11f-ed5c-4d88-b3f4-14392f990b9d.png)

而在表2这里的顺序中，事务B在事务A提交后的快照读和当前读都是实时的新数据400，这是为什么呢？

这里与上表的唯一区别仅仅是表1的事务B在事务A修改金额前快照读过一次金额数据，而表2的事务B在事务A修改金额前没有进行过快照读。

**所以我们知道事务中快照读的结果是非常依赖该事务首次出现快照读的地方，即某个事务中首次出现快照读的地方非常关键，它有决定该事务后续快照读结果的能力**

**我们这里测试的是更新，同时删除和更新也是一样的，如果事务B的快照读是在事务A操作之后进行的，事务B的快照读也是能读取到最新的数据的**

### RC,RR级别下的InnoDB快照读有什么不同？
正是Read View生成时机的不同，从而造成RC,RR级别下快照读的结果的不同

+ 在RR级别下的某个事务的对某条记录的第一次快照读会创建一个快照及Read View, 将当前系统活跃的其他事务记录起来，此后在调用快照读的时候，还是使用的是同一个Read View，所以只要当前事务在其他事务提交更新之前使用过快照读，那么之后的快照读使用的都是同一个Read View，所以对之后的修改不可见；
+ 即RR级别下，快照读生成Read View时，Read View会记录此时所有其他活动事务的快照，这些事务的修改对于当前事务都是不可见的。而早于Read View创建的事务所做的修改均是可见
+ 而在RC级别下的，事务中，每次快照读都会新生成一个快照和Read View, 这就是我们在RC级别下的事务中可以看到别的事务提交的更新的原因

**总之在RC隔离级别下，是每个快照读都会生成并获取最新的Read View；而在RR隔离级别下，则是同一个事务中的第一个快照读才会创建Read View, 之后的快照读获取的都是同一个Read View**。

+ 版权声明：本文为CSDN博主「SnailMann」的原创文章，遵循CC 4.0 BY-SA版权协议，转载请附上原文出处链接及本声明。
+ 原文链接：https: //blog.csdn.net/SnailMann/article/details/94724197


# 7种MySQL亿级_千万级大表快速删除数据方案：锁影响与性能分析

![1745238005775-ad97e767-4a35-41af-a793-bba576ae26a7.png](images/1745238005775-ad97e767-4a35-41af-a793-bba576ae26a7.png)

以下是MySQL大表删除方案，重点分析每种方案的**锁定影响**、**执行时间**和**系统负载**，从最优到次优排序：

## 1. TRUNCATE TABLE（全表清空）
```plsql
TRUNCATE TABLE huge_table;
```

**锁定分析**：

+ **锁定程度**：表级锁，阻塞所有读写
+ **锁定时间**：极短（通常几秒）
+ **执行效率**：即时操作，与表大小关系不大
+ **系统影响**：最小，几乎不产生redo/undo日志

**使用场景**：

+ 需要删除表中**全部数据**且保留表结构
+ 不需要事务回滚能力
+ 可接受短暂的表不可用

**注意事项**：无法指定条件删除，是DDL操作，不可回滚

## 2. DROP PARTITION（分区删除）
```plsql
ALTER TABLE huge_table DROP PARTITION p_202301;
```

**锁定分析**：

+ **锁定程度**：表元数据锁，主要影响DDL操作
+ **锁定时间**：极短（通常几秒，即使分区包含数千万行）
+ **执行效率**：几乎与分区数据量无关，主要是文件系统操作
+ **系统影响**：最小，不生成事务日志

**使用场景**：

+ 表已经是分区表
+ 删除条件与分区键完全匹配
+ 例如：按月分区的表删除整月数据

**注意事项**：

+ 要求表已经是分区表
+ 只能按分区边界删除，不能部分删除分区内容

## 3. 快速表重建法（零锁/最小锁方案）
```plsql
-- 1. 创建新表（不锁原表）
CREATE TABLE huge_table_new LIKE huge_table;

-- 2. 批量插入要保留的数据（不锁定原表读取）
INSERT INTO huge_table_new
SELECT * FROM huge_table WHERE keep_condition LIMIT 1000000;
-- 继续更多批次...

-- 3. 创建索引（不锁原表）
ALTER TABLE huge_table_new ADD INDEX...

-- 4. 原子切换表（极短时间锁定）
RENAME TABLE huge_table TO huge_table_old,
             huge_table_new TO huge_table;
```

**锁定分析**：

+ **锁定程度**：仅在RENAME期间短暂锁定（毫秒级）
+ **锁定时间**：几乎可忽略
+ **执行效率**：高（只复制需要保留的数据）
+ **系统影响**：中等（需要额外存储空间）

**使用场景**：

+ 删除比例大于50%的数据
+ 要求几乎零停机时间
+ 可以接受额外的磁盘空间使用

## 4. 普通批量删除（高系统负载）
```plsql
-- 基本批量删除循环
DELETE FROM huge_table
WHERE delete_condition
LIMIT 10000;
```

**锁定分析**：

+ **锁定程度**：行级锁，可能导致锁升级
+ **锁定时间**：每批次短时间锁定，总体较长
+ **执行效率**：低（需要扫描所有数据，记录日志）
+ **系统影响**：高（大量I/O，redo/undo日志，索引维护）

**使用场景**：

+ 必须在线删除且无法使用其他方案
+ 删除比例较小（ 0 DO
        START TRANSACTION;
        DELETE FROM huge_table
        WHERE delete_condition
        ORDER BY id  -- 确保按索引删除
        LIMIT p_batch_size;

        SET v_rows_affected = ROW_COUNT();
        SET v_total_deleted = v_total_deleted + v_rows_affected;

        COMMIT;

        -- 允许其他事务执行
        DO SLEEP(0.1);
    END WHILE;

    SET v_end_time = NOW();

    SELECT
        CONCAT('已删除 ', v_total_deleted, ' 行数据') AS Total_Deleted,
        CONCAT('执行时间: ', TIMESTAMPDIFF(SECOND, v_start_time, v_end_time), ' 秒') AS Execution_Time;
END;
```

## 5. 使用pt-archiver专业工具（低影响）
```powershell
pt-archiver \
  --source h=localhost,D=database,t=huge_table,u=root,p=password \
  --where "create_time 之后删除:秒级 | 转换:中之后:极低 | 初始投入 | 长期数据管理 |

## 最佳实践建议
1. **短期快速删除**：
    - 单次操作选择表重建法或pt-archiver工具
    - 已分区表直接使用DROP PARTITION
2. **长期策略**：
    - 投资将大表转换为分区表
    - 使用pt-online-schema-change工具实现低影响转换
    - 建立自动化分区管理流程
3. **风险控制**：
    - 始终在操作前备份
    - 先在测试环境验证
    - 监控复制延迟和系统资源
    - 在业务低峰期执行

每种方案都有其适用场景和权衡，选择时应考虑：业务可接受的停机时间、系统当前负载、操作紧急程度以及长期数据管理需求。通常，长期来看，分区表策略提供最佳的总体拥有成本和性能。


# MySQL数据库备份的3种方式

先问大家一个问题，在生产环境中什么最重要？服务器的硬件坏了可以维修或者换新, 软件问题可以修复或重新安装, 但是如果数据没了呢？这可能是最恐怖的事情了吧, 我感觉在生产环境中应该没有什么比数据跟更为重要，那么我们该如何保证数据不丢失、或者丢失后可以快速恢复呢？大家看完本文就能对`MySQL`中实现数据备份和恢复能有一定的了解。

### 为什么需要备份数据？

> 其实在`前言`中也大概说明了为什么要备份数据, 但是我们还是应该具体了解一下为什么要备份数据 在生产环境中我们数据库可能会遭遇各种各样的不测从而导致数据丢失, 大概分为以下几种.

* 硬件故障
* 软件故障
* 自然灾害
* 黑客攻击
* 误操作 (**占比最大**)

所以, 为了在数据丢失之后能够恢复数据, 我们就需要定期的备份数据, 备份数据的策略要根据不同的应用场景进行定制, 大致有几个参考数值, 我们可以根据这些数值从而定制符合特定环境中的数据备份策略

* 能够容忍丢失多少数据
* 恢复数据需要多长时间
* 需要恢复哪一些数据

### 数据的备份类型

> 数据的备份类型根据其自身的特性主要分为以下几组

* 完全备份
* 部分备份：完全备份指的是**备份整个数据集( 即整个数据库 )**、部分备份指的是**备份部分数据集(例如: 只备份一个表)**

而部分备份又分为以下两种

* 增量备份
* 差异备份：增量备份指的是**备份自上一次备份以来(增量或完全)以来变化的数据**; 特点: 节约空间、还原麻烦 差异备份指的是**备份自上一次完全备份以来变化的数据** 特点: 浪费空间、还原比增量备份简单

示意图

![1729747473648-79904806-4c41-4325-8155-c62c4abb4eb1.png](images/1729747473648-79904806-4c41-4325-8155-c62c4abb4eb1.png)

### **MySQL备份数据的方式**

> 在`MySQl`中我们备份数据一般有几种方式

* 热备份：热备份指的是当数据库进行备份时, **数据库的读写操作均不是受影响**
* 温备份：温备份指的是当数据库进行备份时, **数据库的读操作可以执行, 但是不能执行写操作**
* 冷备份：冷备份指的是当数据库进行备份时, **数据库不能进行读写操作, 即数据库要下线**

`MySQL`中进行不同方式的备份还要考虑存储引擎是否支持

* MyISAM  热备 × 温备 √  冷备 √
* InnoDB   热备 √  温备 √  冷备 √

我们在考虑完数据在备份时, 数据库的运行状态之后还需要考虑对于`MySQL`数据库中数据的备份方式

* 物理备份：物理备份一般就是**通过****tar****,****cp****等命令直接打包复制数据库的数据文件**达到备份的效果
* 逻辑备份：逻辑备份一般就是**通过特定工具从数据库中导出数据并另存备份**(逻辑备份会丢失数据精度)

### 备份需要考虑的问题

> 定制备份策略前, 我们还需要考虑一些问题 **我们要备份什么?** 一般情况下, 我们需要备份的数据分为以下几种

* 数据
* 二进制日志, InnoDB事务日志
* 代码(存储过程、存储函数、触发器、事件调度器)
* 服务器配置文件

**备份工具** 这里我们列举出常用的几种备份工具 `mysqldump` : 逻辑备份工具, 适用于所有的存储引擎, 支持温备、完全备份、部分备份、对于**InnoDB**存储引擎支持热备 `cp, tar 等归档复制工具`: 物理备份工具, 适用于所有的存储引擎, 冷备、完全备份、部分备份 `lvm2 snapshot`: 几乎热备, 借助文件系统管理工具进行备份 `mysqlhotcopy`: 名不副实的的一个工具, 几乎冷备, 仅支持**MyISAM**存储引擎 `xtrabackup`: 一款非常强大的**InnoDB/XtraDB**热备工具, 支持完全备份、增量备份, 由`percona`提供

### 设计合适的备份策略

> 针对不同的场景下, 我们应该制定不同的备份策略对数据库进行备份, 一般情况下, 备份策略一般为以下三种

* \*\*直接cp，tar复制数据库文件：\*\*数据量较小, 直接复制数据库文件
* \*\*mysqldump：\*\*数据量一般, 先使用mysqldump对数据库进行完全备份
* \*\*xtrabackup：\*\*数据量很大，而又不过分影响业务运行，使用`xtrabackup`进行完全备份后, 定期使用`xtrabackup`进行增量备份或差异备份

### 实战演练

#### 使用cp进行全量备份

> 我们这里使用的是使用yum安装的`mysql-8.0.37`的版本

**查看数据库的信息**

```sql
[root@localhost ~]# mysql -uroot -p'1qaz@WSX'   #登录MySQL
mysql> show databases;    #查看当前的数据库, 我们的数据库为employees
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| sys                |
| test               |
+--------------------+
5 rows in set (0.00 sec)

mysql> use sys;
Database changed

mysql> select count(*) from user_login_logs;   #user_login_logs的行数为20000
+----------+
| count(*) |
+----------+
|    20000 |
+----------+
1 row in set (0.01 sec)
```

**向数据库施加读锁**

```plsql
mysql> flush tables with read lock;    #向所有表施加读锁
Query OK, 0 rows affected (0.00 sec)
```

**备份数据文件**

```shell
[root@localhost ~]# mkdir /opt/backup   									 #创建文件夹存放备份数据库文件
[root@localhost ~]# cp -a /var/lib/mysql/* /opt/backup     #保留权限的拷贝源数据文件
[root@localhost ~]# ls /opt/backup                         #查看目录下的文件
```

![1729753476484-a1c65365-71ab-4968-b237-07d9a0c79f02.png](images/1729753476484-a1c65365-71ab-4968-b237-07d9a0c79f02.png)

**模拟数据丢失并恢复**

```sql
[root@localhost ~]# rm -rf /var/lib/mysql/*    #删除数据库的所有文件
[root@localhost ~]# service mysqld stop        #停止MySQL
[root@localhost ~]# cp -a /opt/backup/* /var/lib/mysql/    #将备份的数据文件拷贝回去
[root@localhost ~]# service mysqld start  #启动MySQL#重新连接数据并查看

[root@localhost ~]# mysql -uroot -p'1qaz@WSX'   #登录MySQL
mysql> show databases;    #数据库已恢复
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| sys                |
| test               |
+--------------------+
5 rows in set (0.00 sec)

mysql> use sys;
Database changed

mysql> select count(*) from user_login_logs;    #表的行数没有变化
+----------+
| count(*) |
+----------+
|    20000 |
+----------+
1 row in set (0.01 sec)
```

**备份完成后，需要解锁:    UNLOCK TABLES;**

#### 使用mysqldump备份

> 通过mysqldump进行备份

**mysqldump****命令介绍**

> `mysqldump`是一个客户端的逻辑备份工具, 可以生成一个重现创建原始数据库和表的SQL语句, 可以支持所有的存储引擎, 对于InnoDB支持热备
>
> [官方文档介绍](https://cloud.tencent.com/developer/tools/blog-entry?target=http%3A%2F%2Fdev.mysql.com%2Fdoc%2Frefman%2F5.7%2Fen%2Fmysqldump.html\&source=article\&objectId=2096467)

```sql
#备份全部数据库
mysqldump -uroot -1qaz@WSX --all-databases > backup_all_databases.sql
    mysqldump
        -uroot -1qaz@WSX                   登录MySQL的用户名/密码
        --all-databases
        > backup_all_databases.sql        备份文件的名称，可加保存路径

#备份一个数据库
mysqldump -uroot -1qaz@WSX --databases database_test1 > backup_database_test1.sql

#备份多个数据库
mysqldump -uroot -1qaz@WSX --databases database_test1 database_test2 > backup_database_test1_test2.sql
     mysqldump
        -uroot -1qaz@WSX                           登录MySQL的用户名/密码
        --databases
        database_test1 database_test2             要备份的数据库，多个以空格间隔
        > backup_*.sql                            备份文件的名称，可加保存路径

#备份库中的部分表
mysqldump -uroot -1qaz@WSX database_test1 table_test1 table_test2 > backup_tables.sql
     mysqldump
        -uroot -1qaz@WSX                   登录MySQL的用户名/密码
        database_test1                    要备份表所在的库名
        table_test1 >                     要备份的表名，可以有多个，以空格分割
        backup_tables.sql                 备份文件的名称，可加保存路径

查看备份文件中的内容
  #查看其中一个备份文件
  cat backup_tables.sql | grep -v "^--" |grep -v "^/" |grep -v "^$"
       cat
        backup_database_test1.sql                       要查看的文件
        | grep -v "^--" |grep -v "^/" |grep -v "^$"      过滤不显示的信息(grep为搜索，-v表示忽略)
```

**查看数据库的信息**

```sql
mysql> show databases;    #查看当前的数据库, 我们的数据库为employees
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| sys                |
| test               |
+--------------------+
5 rows in set (0.00 sec)

mysql> use sys;
Database changed

mysql> select count(*) from user_login_logs;   #user_login_logs的行数为20000
+----------+
| count(*) |
+----------+
|    20000 |
+----------+
1 row in set (0.01 sec)
```

**使用****mysqldump****备份数据库**

```sql
[root@node1 ~]# mysqldump -uroot -p'1qaz@WSX' sys user_login_logs > backup_user_login_logs.sql   #备份数据库到 backup_user_login_logs.sql文件中
mysql> drop table user_login_logs;   #删除目标表
Query OK, 0 rows affected (0.03 sec)

[root@node1 ~]# mysql -uroot -p'1qaz@WSX' sys  show databases;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| sys                |
| test               |
+--------------------+
5 rows in set (0.00 sec)

mysql> use sys;
Database changed

mysql> select count(*) from user_login_logs;    #表的行数没有变化,数据已恢复
+----------+
| count(*) |
+----------+
|    20000 |
+----------+
1 row in set (0.01 sec)
```

| 其他恢复单库，多库，多表方法类似，大家参考单表恢复流程即可。

#### 使用Xtrabackup备份

> 为了更好地演示, 我们这次使用`mariadb-5.5`的版本, 使用`xtrabackup`使用InnoDB能够发挥其最大功效, 并且InnoDB的每一张表必须使用单独的表空间, 我们需要在配置文件中添加 `innodb_file_per_table = ON` 来开启

**下载安装****xtrabackup**

```powershell

[root@localhost software]# yum  -y install openssl-devel libaio libaio-devel automake autoconf bison libtool ncurses-devel libgcrypt-devel libev-devel libcurl-devel zlib-devel vim-common libcurl-devel libudev-devel
[root@localhost software]# yum  -y install https://repo.percona.com/yum/percona-release-latest.noarch.rpm
[root@localhost software]# yum install epel-release
[root@localhost software]# yum install zstd
[root@localhost software]# percona-release enable-only tools
[root@localhost software]# yum  -y install percona-xtrabackup-80
[root@localhost software]# xtrabackup --version
```

**xtrabackup****介绍**

> `Xtrabackup`是由`percona`提供的`mysql`数据库备份工具，据官方介绍，这也是世界上惟一一款开源的能够对innodb和xtradb数据库进行热备的工具。特点：

1. 备份过程快速、可靠；
2. 备份过程不会打断正在执行的事务；
3. 能够基于压缩等功能节约磁盘空间和流量；
4. 自动实现备份检验；
5. 还原速度快；

**xtrabackup****实现完全备份**

> 我们这里使用`xtrabackup`的前端配置工具`innobackupex`来实现对数据库的完全备份 使用`innobackupex`备份时, 会调用`xtrabackup`备份所有的**InnoDB**表, 复制所有关于表结构定义的相关文件(.frm)、以及**MyISAM**、**MERGE**、**CSV**和**ARCHIVE**表的相关文件, 同时还会备份触发器和数据库配置文件信息相关的文件, 这些文件会被保存至一个以时间命名的目录.

**备份全恢复过程**

```plsql
# 如果权限有问题，需要打开权限。
mysql> use mysql;
mysql> GRANT BACKUP_ADMIN ON *.* TO 'root'@'%';
mysql> FLUSH PRIVILEGES;

mkdir -p /opt/software/xtrabackup/backup/base

# 第一次全量备份（20000数据）
xtrabackup -uroot -p'1qaz@WSX' --backup --target-dir=/opt/software/xtrabackup/backup/base --no-server-version-check

# 全量备份第一次增量备份（16000数据）
xtrabackup -uroot -p'1qaz@WSX' --backup --target-dir=/opt/software/xtrabackup/backup/inc1 --incremental-basedir=/opt/software/xtrabackup/backup/base --no-server-version-check

# 全量备份第二次增量备份（15000数据）
xtrabackup -uroot -p'1qaz@WSX' --backup --target-dir=/opt/software/xtrabackup/backup/inc2 --incremental-basedir=/opt/software/xtrabackup/backup/inc1 --no-server-version-check

# 预准备完成备份，此选项--apply-log-only 阻止回滚未完成的事务，此步骤必须先执行
xtrabackup -uroot -p'1qaz@WSX'  --prepare --apply-log-only --target-dir=/opt/software/xtrabackup/backup/base

# 合并第1次增量备份到完全备份
xtrabackup -uroot -p'1qaz@WSX' --prepare --apply-log-only --target-dir=/opt/software/xtrabackup/backup/base --incremental-dir=/opt/software/xtrabackup/backup/inc1

# 合并第2次增量备份到完全备份：最后一次还原不需要加选项--apply-log-only
xtrabackup -uroot -p'1qaz@WSX' --prepare --target-dir=/opt/software/xtrabackup/backup/base --incremental-dir=/opt/software/xtrabackup/backup/inc2

# 清空源数据，只有清空源数据才能备份
rm -rf /var/lib/mysql/*

# 还原数据库,当然也可以使用mv命令
xtrabackup -uroot -p'1qaz@WSX' --copy-back --target-dir=/opt/software/xtrabackup/backup/base

# 授权
chown -R mysql:mysql /var/lib/mysql

# 停止MySQL
systemctl stop mysqld

# 启动MySQL
systemctl start mysqld

# 这时候在检查数据就已经完全恢复了
```

**单个恢复过程**

```sql
# 第一次全量备份（20000数据）
xtrabackup -uroot -p'1qaz@WSX' --backup --target-dir=/opt/software/xtrabackup/backup/base --no-server-version-check

# 全量备份第一次增量备份（16000数据）
xtrabackup -uroot -p'1qaz@WSX' --backup --target-dir=/opt/software/xtrabackup/backup/inc1 --incremental-basedir=/opt/software/xtrabackup/backup/base --no-server-version-check

# 全量备份第二次增量备份（15000数据）
xtrabackup -uroot -p'1qaz@WSX' --backup --target-dir=/opt/software/xtrabackup/backup/inc2 --incremental-basedir=/opt/software/xtrabackup/backup/inc1 --no-server-version-check

# 如果此时只想恢复base版本
xtrabackup -uroot -p'1qaz@WSX'  --prepare  --target-dir=/opt/software/xtrabackup/backup/base

# 清空源数据，只有清空源数据才能备份
rm -rf /var/lib/mysql/*

# 还原数据库,当然也可以使用mv命令
xtrabackup -uroot -p'1qaz@WSX' --copy-back --target-dir=/opt/software/xtrabackup/backup/base

# 授权
chown -R mysql:mysql /var/lib/mysql

# 停止MySQL
systemctl stop mysqld

# 启动MySQL
systemctl start mysqld

# 这时候在检查数据就已经完全到base版本了，如果需要恢复第一次增量就先准备好备份文件，在恢复。
```

### 总结

| 备份命令 | 备份速度 | 恢复速度 | 介绍 | 功能 | 适用场景 |
| --- | --- | --- | --- | --- | --- |
| cp | 快 | 快 | 一般、灵活性低 | 很弱 | 少量数据备份 |
| mysqldump | 慢 | 慢 | 一般、可无视存储引擎的差异 | 一般 | 中小型数据量的备份 |
| xtrabackup | 较快 | 较快 | 实现innodb热备、对存储引擎有要求 | 强大 | 较大规模的备份 |


# MySQLNULL值的5大致命陷阱及解决方案

在日常开发中，MySQL 数据库字段允许 NULL 值是一个常见的设计，但它也可能引发许多意想不到的问题。NULL 值的特殊性经常让开发者在查询、统计和逻辑判断中踩坑，甚至导致程序异常。

本文将通过详细的案例，分析 NULL 值可能引发的 5 大问题，并提供实用的解决方案和最佳实践，帮助你彻底掌握 NULL 值的处理方法。

***

## 数据准备：快速复现问题

为了验证 NULL 值引发的问题，我们需要先创建测试表并插入测试数据。以下是完整的 SQL 代码：

```plsql
CREATE TABLE person (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) DEFAULT NULL,
  mobile VARCHAR(20) DEFAULT NULL
);

CREATE TABLE employee (
  id INT AUTO_INCREMENT PRIMARY KEY,
  salary INT DEFAULT NULL
);

INSERT INTO person (name, mobile) VALUES
('Alice', '1234567890'),
('Bob', '9876543210'),
(NULL, '1234567890'),
('Alice', NULL),
('Java', '1111111111'),
('Python', '2222222222'),
('C++', '3333333333'),
(NULL, NULL),
('Java', NULL),
(NULL, '4444444444');

INSERT INTO employee (salary) VALUES
(1000),
(2000),
(NULL);
```

***

## NULL 值引发的 5 大问题

### 一、COUNT/DISTINCT 数据丢失

#### 问题描述

COUNT 是 MySQL 中常用的统计函数，但当字段值为 NULL 时，COUNT(column) 会忽略这些记录，导致统计结果不准确。例如：

```plsql
SELECT COUNT(*) AS total_count, COUNT(name) AS name_count FROM person;
```

执行结果如下：

| **total\_count** | **name\_count** |
| --- | --- |
| 10 | 7 |

可以看到，COUNT(name) 忽略了 name 字段为 NULL 的记录，导致统计结果丢失。

#### 解决方案

* **使用\*\*\*\* ****COUNT(*)**：统计所有记录，包括字段值为 NULL 的行。
* **扩展知识**：避免使用 COUNT(常量)，如 COUNT(1)，因为它的行为与 COUNT(*) 一致，但可读性较差。

***

#### 问题描述

当使用 COUNT(DISTINCT column1, column2) 时，如果任意一个字段值为 NULL，即使另一列有不同的值，查询结果也会忽略这些记录。例如：

```plsql
SELECT COUNT(DISTINCT name, mobile) AS distinct_count FROM person;
```

执行结果如下：

| **distinct\_count** |
| --- |
| 5 |

尽管 mobile 列中有多个不同的值，但由于 name 或 mobile 中存在 NULL，导致部分记录被忽略。

#### 解决方案

* **避免字段值为 NULL**：在表设计时，尽量设置字段为 NOT NULL，并为其指定默认值。
* **使用替代函数**：通过 IFNULL(column, default_value) 将 NULL 转换为默认值，例如：

```plsql
SELECT COUNT(DISTINCT IFNULL(name, ''), IFNULL(mobile, '')) AS distinct_count FROM person;
```

***

### 二、NULL 对比结果为未知（false）

#### 问题描述

在使用非等于查询（<> 或 !=）时，NULL 值的记录会被忽略。例如：

```plsql
SELECT * FROM person WHERE name != 'Java';
```

执行结果如下：

| **id** | **name** | **mobile** |
| --- | --- | --- |
| 1 | Alice | 1234567890 |
| 2 | Bob | 9876543210 |
| 4 | Alice | NULL |
| 6 | Python | 2222222222 |
| 7 | C++ | 3333333333 |

可以看到，name 为 NULL 的记录被忽略，导致查询结果不完整。

#### 解决方案

* **显式处理 NULL**：在查询条件中加入对 NULL 的判断，例如：

```plsql
SELECT * FROM person WHERE name != 'Java' OR name IS NULL;
```

***

### 三、NULL 值运算都为 NULL

#### 问题描述

在使用 NULL 值进行运算时，比如加减乘除，拼接等等 最终的结果都为 NULL

```plsql
SELECT id,salary + 1 FROM employee;
SELECT id,concat(name,'-baili') FROM person;
```

### 四、聚合空指针异常

#### 问题描述

在使用聚合函数（如 SUM、AVG）时，如果字段值为 NULL，查询结果也会为 NULL，而不是预期的 0。这可能导致程序在处理结果时出现空指针异常。例如：

```plsql
SELECT SUM(salary) AS total_salary FROM employee WHERE id >= 3;
```

执行结果如下：

| **total\_salary** |
| --- |
| NULL |

#### 解决方案

* **使用\*\*\*\* ****IFNULL**** \*\*\*\*函数**：将 NULL 转换为 0，例如：

```plsql
SELECT SUM(IFNULL(salary, 0)) AS total_salary FROM employee WHERE id >= 3;
```

执行结果为：

| **total\_salary** |
| --- |
| 0 |

***

### 五、Group By Order By 会统计 NULL 值

#### 问题描述

在使用 group by 与 order by 时，不会剔除 NULL，会将 NULL 作为最小值，例如：

```plsql
SELECT * FROM person order by name desc;
```

#### 解决方案

* **使用 ****IS NOT NULL**：剔除掉 NULL 记录，例如：

```plsql
SELECT * FROM person where name is not null order by name desc;
```

***

## 最佳实践

1. **表设计时尽量避免 NULL 值**：
   * 设置字段为 NOT NULL。
   * 为字段指定默认值，例如空字符串 '' 或 0。
2. **查询时显式处理 NULL**：
   * 使用 IFNULL 或 COALESCE 函数将 NULL 转换为默认值。
   * 在查询条件中加入 IS NULL 或 IS NOT NULL。
3. **遵循规范**：
   * 根据阿里巴巴《Java 开发手册》的建议，优先使用 ISNULL(column) 判断 NULL 值，提升代码可读性和执行效率。

***

## 总结

MySQL 中 NULL 值的处理是一个容易被忽视但又非常重要的问题。

通过本文的分析和解决方案，希望你能更好地理解和应对 NULL 值问题。

在实际开发中，尽量避免使用 NULL 值，并遵循最佳实践，才能让你的数据库设计更加健壮、高效。


# MySQL进阶系列：Join算法详解

![1734939656801-5952ce0c-a337-4404-bdd6-dd6dfcbc6d0d.png](images/1734939656801-5952ce0c-a337-4404-bdd6-dd6dfcbc6d0d.png)

## 前言

在数据库开发中，JOIN 是多表查询的核心操作，其性能直接影响整个系统的效率。

MySQL 提供了多种 JOIN 算法来处理表之间的连接操作，包括

* 嵌套循环连接（Nested Loop Join）
* 索引嵌套循环连接（Index Nested Loop Join）
* 块嵌套循环连接（Block Nested Loop Join）
* 哈希连接（Hash Join）
* 排序合并连接（Sort-Merge Join）

这些算法各有优劣，适用于不同的场景。本文将详细解析这些 JOIN 算法的底层实现原理，并结合实际案例和优化建议，帮助开发者更好地理解和优化多表查询。

## 1. 简单嵌套循环连接（Simple Nested-Loop Join, SNLJ）

### 原理

驱动表中的每一条记录，会依次与被驱动表中的每一条记录进行比较，寻找符合条件的匹配记录。这是最基本的实现方式，几乎不依赖任何辅助优化。

### 特点

SNLJ 的实现简单，直接，同时也非常低效。因此，通常仅在小表连接场景下使用。

### 优缺点

* **优点：**实现极其简单，可广泛应用于快速验证。
* **缺点：**性能差，对大数据量的查询非常低效，尤其是驱动表和被驱动表数据均较大时。

### 执行流程图

简单嵌套循环连接（SNLJ）是最基础的连接算法，其执行过程如下：

* 从驱动表中取出一条记录。
* 遍历被驱动表中的所有记录，找到匹配的记录。
* 将匹配结果加入结果集。

![1734937321227-f780ca95-3d5a-447c-9507-ae9063ec8391.png](images/1734937321227-f780ca95-3d5a-447c-9507-ae9063ec8391.png)

## 2. 索引嵌套循环连接（Index Nested-Loop Join, INLJ）

### 原理

INLJ 是嵌套循环连接的优化版本，通过被驱动表上的索引，可以避免对其进行全表扫描，而是直接通过索引定位到匹配记录。

### 特点

利用了被驱动表索引提升查询效率，非常适合**小表连接大表**或者**大表间的少量匹配场景**。

### 优缺点

* **优点：**速度快，大幅减少了被驱动表的扫描次数。
* **缺点：**依赖被驱动表索引；如果索引丢失，性能直接退化为简单嵌套循环。

### 执行流程图

索引嵌套循环连接（INLJ）通过利用被驱动表的索引，显著减少匹配次数。其执行过程如下：

* 从驱动表中取出一条记录。
* 使用该记录的连接键，通过索引快速定位被驱动表中的匹配记录。
* 将匹配结果加入结果集。

![1734936881477-738b0ad6-8297-4b3b-84ea-ca6f6ae1efd7.png](images/1734936881477-738b0ad6-8297-4b3b-84ea-ca6f6ae1efd7.png)

## 3. 块嵌套循环连接（Block Nested-Loop Join, BNLJ）

### 原理

在 BNLJ 中，驱动表的一部分数据会首先被加载到内存缓冲区 (JOIN BUFFER) 中，然后再与被驱动表进行比较匹配操作。

### 特点

通过批量加载缓冲区减少被驱动表的扫描次数，适合于**大表之间无索引连接**的场景。

### 优缺点

* **优点：**缓冲机制可以显著降低被驱动表扫描次数。
* **缺点：**对内存消耗较大，缓冲区不足会导致效率下降。

### 执行流程图

块嵌套循环连接（BNLJ）通过引入 JOIN BUFFER 缓冲区，减少被驱动表的 I/O 次数。其执行过程如下：

* 将驱动表的一部分数据加载到 JOIN BUFFER 中。
* 遍历被驱动表的所有记录，与 JOIN BUFFER 中的数据进行匹配。
* 重复上述过程，直到驱动表的数据全部处理完毕。

![1734936931411-9ea68a1b-7c62-4c12-813a-3021171718db.png](images/1734936931411-9ea68a1b-7c62-4c12-813a-3021171718db.png)

## 4. 哈希连接（Hash Join）

### 原理

哈希连接是一种高效的连接算法，适用于**等值连接**场景。其核心思想是：

1. **构建阶段：**以较小的表为基准，基于连接键构建哈希表（作为构建表）。
2. **探测阶段：**扫描较大的表（探测表），根据哈希值快速定位构建表中的匹配项。

### 特点

哈希连接适用于需要连接的大表之间数据量大、缺少索引、但连接条件是**等值条件**的情况。

### 优缺点

* **优点：**在等值连接上效率极高，尤其适合无索引的大数据集。
* **缺点：**无法处理范围条件、不等式条件；哈希表构建阶段对内存的依赖较大。

### 执行流程图

哈希连接（Hash Join）是 MySQL 8.0.20 引入的一种高效连接算法，适用于大数据集的等值连接。其执行过程如下：

* **构建阶段**：将较小的表加载到内存中，并基于连接键构建哈希表。
* **探测阶段**：扫描较大的表，根据连接键查找哈希表中的匹配记录。

![1734936902592-891c31c0-0466-47d9-84e3-a0a77d098378.png](images/1734936902592-891c31c0-0466-47d9-84e3-a0a77d098378.png)

## 5. 排序合并连接（Sort-Merge Join）

### 原理

排序合并连接通过**先对表的连接键进行排序**，然后使用类似归并排序的方式合并两个表。步骤如下：

1. 为表 A 和表 B 基于连接键进行排序。
2. 分别从两个排序后的表读取数据，对比连接键并合并匹配的记录。
3. 对于不满足条件的记录，通过移动较小的一方指针解决。

### 特点

非常适合于需要排序的大表或者需要进行范围条件连接的时候。

### 优缺点

* **优点：**适用于范围条件和等值条件，特别适合超大数据集。
* **缺点：**排序阶段可能会导致较高的 I/O 开销。

### 执行流程图

排序合并连接（Sort-Merge Join）是一种高效的连接算法，特别适用于没有索引的大数据集和需要范围连接的场景。其执行过程如下：

* **排序阶段**：对两个表的连接键进行排序。
* **合并阶段**：使用类似“归并排序”的方式，依次扫描两个排序后的表。

![1734936912988-db408d2a-4b61-43f8-aec4-20732aaf3d51.png](images/1734936912988-db408d2a-4b61-43f8-aec4-20732aaf3d51.png)

## 6. JOIN 算法对比

以下为五种 JOIN 算法的总结性对比，为开发者选择合适算法提供参考：

| 算法 | 适用场景 | 优点 | 缺点 |
| --- | --- | --- | --- |
| SNLJ | 小表连接小表 | 实现简单 | 性能差，只适合小表 |
| INLJ | 被驱动表有索引 | 显著提升性能 | 缺少索引时性能退化 |
| BNLJ | 无索引的大表连接 | 减少被驱动表扫描 | 对内存依赖较高 |
| Hash Join | 等值连接 | 等值连接效率高 | 无法处理范围查询 |
| Sort-Merge Join | 范围或无索引场景 | 支持范围条件 | 排序的 I/O 开销大 |

## 7. 总结

通过深入理解 JOIN 的实现原理和适用场景，可以根据需求选择合适的算法：

* **SNLJ：**适合小表或快速验证。
* **INLJ：**优选小表到大表且有索引的场景。
* **BNLJ：**适用于无索引的场景。
* **Hash Join：**等值连接的高效利器。
* **Sort-Merge Join：**更适合范围查询和排序场景。


# MySQL踩坑笔记，加了唯一索引还会出现重复数据？

## 还原问题

表结构如下：

```sql
-- 表格式
CREATE TABLE `student_course` (
  `id` bigint NOT NULL,
  `student_id` bigint NOT NULL,
  `course_id` bigint NOT NULL,
  `xxx_id` varchar(255) COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- 为了保证数据的唯一性，建了唯一索引：
alter table student_course add unique index
ux_student_conrse_xxx(student_id,course_id,xxx_id);

INSERT INTO `student_course` (`id`, `student_id`, `course_id`, `xxx_id`) VALUES
(1, 1001, 2001, 'xxx_001'),
(2, 1002, 2002, 'xxx_002'),
(3, 1003, 2003, 'xxx_003');

INSERT INTO `student_course` (`id`, `student_id`, `course_id`, `xxx_id`) VALUES
(4, 1001, 2001, NULL),
(5, 1002, 2002, NULL);
```

第二天查看数据，发现该表中竟然产生了重复的数据：

从上图中看出，mysql的唯一性约束生效了，重复数据被拦截了。

![1684936066489-0abbd2f5-1199-45b2-a70c-c52296cdca59.png](images/1684936066489-0abbd2f5-1199-45b2-a70c-c52296cdca59.png)

接下来，我们再插入两条xxx_id为null的数据，其中第三条数据跟第二条数据中`student_id`、`course_id`和xxx_id字段值都一样.

![1684935985951-685bed3b-116b-4670-afcd-34ce0f140826.png](images/1684935985951-685bed3b-116b-4670-afcd-34ce0f140826.png)

从图中看出，竟然执行成功了。

换句话说，如果唯一索引的字段中，出现了null值，则唯一性约束不会生效。

最终插入的数据情况是这样的：

1. 当xxx_id字段不为空时，不会产生重复的数据。
2. 当xxx_id字段为空时，会生成重复的数据。

> 我们需要特别注意：创建唯一索引的字段，都不能允许为null，否则mysql的唯一性约束可能会失效。

## 产生原因：

这个问题涉及到 SQL 中的三值逻辑，即真（TRUE）、假（FALSE）和未知（UNKNOWN）。

在 MySQL 官方文档中也有说明，Null 与任何值都不相等，包括与另一个 Null 比较。

官网链接：https://dev.mysql.com/doc/refman/8.4/en/problems-with-null.html

![1743320674236-f82e93c9-9285-4b24-a067-4d14656770ca.png](images/1743320674236-f82e93c9-9285-4b24-a067-4d14656770ca.png)

**举个简单例子：**当你使用 NOT IN 条件时，如果其中包含 NULL 值，这会导致整个条件的结果不确定。具体来说：

* 如果一个值与 NULL 进行比较，结果是未知（UNKNOWN）。
* 如果一个条件的结果是未知（UNKNOWN），那么整个条件的结果也是未知（UNKNOWN）。

```sql
SELECT * FROM student_course WHERE xxx_id NOT IN ('xxx_003', NULL);

SELECT * FROM student_course WHERE xxx_id NOT IN ('xxx_003') OR xxx_id IS NULL;
```

因此，当你使用 NOT IN 条件时，如果其中包含 NULL 值，它会导致整个条件结果为未知（UNKNOWN）。

在 SQL 中，任何未知（UNKNOWN）的条件都被视为不符合条件，因此相关的行将被过滤掉，不会包含在结果中。\ 这就是为什么在处理包含 NULL 值的情况时，需要谨慎地使用条件，以确保你的查询逻辑正确。\ 在这种情况下，**使用 IS NULL 条件 **或者 **将 NULL 视为一个单独的选项**。

* **真（TRUE）：**代表条件或表达式为真。如果一个条件符合或一个表达式为真，则结果为真。
* **假（FALSE）：**代表条件或表达式为假。如果一个条件不符合或一个表达式为假，则结果为假。
* **未知（UNKNOWN）：**代表条件或表达式的真假未知。当无法确定条件或表达式的真实值时，结果为未知。

这可能是因为某些数据缺失、表达式中存在空值（NULL）或其他不确定因素导致的。

## 逻辑删除表加唯一索引

我们都知道唯一索引非常简单好用，但有时候，在表中它并不好加。不信，我们一起往下看。通常情况下，要删除表的某条记录的话，如果用delete语句操作的话。例如：

```sql
delete from product where id=123;
```

这种delete操作是物理删除，即该记录被删除之后，后续通过sql语句基本查不出来。（不过通过其他技术手段可以找回，那是后话了）还有另外一种是逻辑删除，主要是通过update语句操作的。例如：

```sql
update product set delete_status=1,edit_time=now(3) where id=123;
```

逻辑删除需要在表中额外增加一个删除状态字段，用于记录数据是否被删除。在所有的业务查询的地方，都需要过滤掉已经删除的数据。通过这种方式删除数据之后，数据任然还在表中，只是从逻辑上过滤了删除状态的数据而已。

其实对于这种逻辑删除的表，是没法加唯一索引的。为什么呢？

假设之前给商品表中的name和model加了唯一索引，如果用户把某条记录删除了，delete\_status设置成1了。后来，该用户发现不对，又重新添加了一模一样的商品。由于唯一索引的存在，该用户第二次添加商品会失败，即使该商品已经被删除了，也没法再添加了。这个问题显然有点严重。

有人可能会说：把name、model和delete\_status三个字段同时做成唯一索引不就行了？

答：这样做确实可以解决用户逻辑删除了某个商品，后来又重新添加相同的商品时，添加不了的问题。但如果第二次添加的商品，又被删除了。该用户第三次添加相同的商品，不也出现问题了？由此可见，如果表中有逻辑删除功能，是不方便创建唯一索引的。\
但如果真的想给包含逻辑删除的表，增加唯一索引，该怎么办呢？

## 删除状态+1

通过前面知道，如果表中有逻辑删除功能，是不方便创建唯一索引的。其根本原因是，记录被删除之后，delete\_status会被设置成1，默认是0。相同的记录第二次删除的时候，delete\_status被设置成1，但由于创建了唯一索引（把name、model和delete\_status三个字段同时做成唯一索引），数据库中已存在delete\_status为1的记录，所以这次会操作失败。

我们为啥不换一种思考：不要纠结于delete\_status为1，表示删除，当delete\_status为1、2、3等等，只要大于1都表示删除。这样的话，每次删除都获取那条相同记录的最大删除状态，然后加1。\
这样数据操作过程变成：

```sql
添加记录a，delete_status=0。
删除记录a，delete_status=1。
添加记录a，delete_status=0。
删除记录a，delete_status=2。
添加记录a，delete_status=0。
删除记录a，delete_status=3。
```

由于记录a，每次删除时，delete\_status都不一样，所以可以保证唯一性。该方案的优点是：不用调整字段，非常简单和直接。\
缺点是：可能需要修改sql逻辑，特别是有些查询sql语句，有些使用delete\_status=1判断删除状态的，需要改成delete\_status>=1。

## 增加时间戳字段

导致逻辑删除表，不好加唯一索引最根本的地方在逻辑删除那里。我们为什么不加个字段，专门处理逻辑删除的功能呢？

答：可以增加时间戳字段。

把name、model、delete\_status和timeStamp，四个字段同时做成唯一索引在添加数据时，timeStamp字段写入默认值1。

然后一旦有逻辑删除操作，则自动往该字段写入时间戳。这样即使是同一条记录，逻辑删除多次，每次生成的时间戳也不一样，也能保证数据的唯一性。

时间戳一般精确到秒。除非在那种极限并发的场景下，对同一条记录，两次不同的逻辑删除操作，产生了相同的时间戳。这时可以将时间戳精确到毫秒。

该方案的优点是：可以在不改变已有代码逻辑的基础上，通过增加新字段实现了数据的唯一性。缺点是：在极限的情况下，可能还是会产生重复数据。

## 增加id字段

其实，增加时间戳字段基本可以解决问题。但在在极限的情况下，可能还是会产生重复数据。有没有办法解决这个问题呢？

答：增加主键字段：delete\_id。

该方案的思路跟增加时间戳字段一致，即在添加数据时给delete\_id设置默认值1，然后在逻辑删除时，给delete\_id赋值成当前记录的主键id。

把name、model、delete\_status和delete\_id，四个字段同时做成唯一索引。这可能是最优方案，无需修改已有删除逻辑，也能保证数据的唯一性。

## 重复历史数据如何加唯一索引？

前面聊过如果表中有逻辑删除功能，不太好加唯一索引，但通过文中介绍的三种方案，可以顺利的加上唯一索引。\
但来自灵魂的一问：如果某张表中，已存在历史重复数据，该如何加索引呢？最简单的做法是，增加一张防重表，然后把数据初始化进去。

可以写一条类似这样的SQL：

```sql
insert into product_unqiue(id,name,category_id,unit_id,model)
select max(id), select name,category_id,unit_id,model from product
group by name,category_id,unit_id,model;
```

这样做可以是可以，但今天的主题是直接在原表中加唯一索引，不用防重表。那么，这个唯一索引该怎么加呢？其实可以借鉴上一节中，增加id字段的思路。增加一个delete\_id字段。不过在给product表创建唯一索引之前，先要做数据处理。获取相同记录的最大id：

```sql
select max(id), select name,category_id,unit_id,model from product
group by name,category_id,unit_id,model;
```

然后将delete\_id字段设置成1。然后将其他的相同记录的delete\_id字段，设置成当前的主键。这样就能区分历史的重复数据了。

当所有的delete\_id字段都设置了值之后，就能给name、model、delete\_status和delete\_id，四个字段加唯一索引了。完美。


# 假如优化器走的索引不是预期中的索引怎么办

**老规矩，学习某个知识点，先搞清楚为什么？在看怎么解决**

### 为什么优化器可能选择非预期索引？

#### **1. 统计信息偏差 **

优化器依赖**数据分布统计信息**进行成本估算：

* **场景**：
  * 表数据量剧增/剧减未更新统计信息
  * 索引列数据分布不均（如90%都是同一状态）
* **后果**：
  * 优化器误判扫描行数（Rows列）

***示例：实际扫描1万行，统计信息误判为100行，导致错误选择索引***

* **更新机制**

| **数据库** | **自动更新触发条件** | **手动更新命令** |
| --- | --- | --- |
| MySQL | 表数据修改 > 10% + 重启 | **ANALYZE TABLE t** |
| PostgreSQL | AUTOVACUUM 阈值 (默认20%修改) | **VACUUM ANALYZE t** |
| **关键隐患**：大表统计更新可能锁表，需在业务低峰执行 | | |

***

#### **2. 查询条件陷阱**

SQL写法导致索引失效，但优化器仍然选择低效索引：

| **陷阱类型** | **案例** | **优化器行为** |
| :---: | :---: | :---: |
| 隐式类型转换 | WHERE varchar_col = 123 | 索引失效但仍出现在执行计划 |
| 索引列函数操作 | WHERE YEAR(create_time)=2023 | 索引无效但被选择 |
| LIKE通配符开头 | WHERE name LIKE '%apple%' | 退化全表扫描 |
| OR连接非索引列 | WHERE indexed_id=1 OR name='A' | 可能放弃索引 |

***

#### **3. 索引设计缺陷**

索引本身存在结构性问题：

* **复合索引顺序错误**：

```plsql
-- 现有索引
INDEX(status, create_time)
-- 但高频查询
WHERE create_time > '2023-01-01' AND status='paid'
-- 优化器无法高效使用 create_time 范围扫描
```

* **缺失覆盖索引**：
  * 查询需回表大量数据，优化器可能放弃索引扫描
* **冗余索引干扰**：
  * 过多相似索引（如idx_a,idx_a_b）导致优化器选择错误

***

#### **4. 成本计算模型局限**

优化器基于**成本估算**而非实际耗时：

* **参数误差**：
  * random_page_cost (PostgreSQL)
  * innodb_stats_persistent_sample_pages (MySQL)
* **硬件认知偏差**：
  * SSD环境仍用HDD默认成本参数
* **算法限制**：
  * MySQL对IN子查询可能错误选择全表扫描

***

#### **5. 环境干扰因素**

外部因素导致误判：

* **Buffer Pool未预热**：冷启动时优化器拒绝走索引
* **参数强制设置**：
  * optimizer_switch关闭索引下推(ICP)
  * force index残留导致后续执行计划混乱

***

### 系统化解决方案

根据根因采取针对性措施：

#### **1. 解决统计信息问题**

```plsql
-- MySQL (立即更新)
ANALYZE TABLE orders;

-- PostgreSQL (提升采样精度)
SET default_statistics_target = 1000;
VACUUM ANALYZE orders;
```

#### **2. 修正查询写法**

```plsql
/* 类型转换修复 */
-- 原: SELECT ... WHERE phone = 13800138000
SELECT ... WHERE phone = '13800138000'  -- 明确字符串类型

/* 函数操作改造 */
-- 原: SELECT ... WHERE DATE(create_time) = '2023-01-01'
SELECT ...
WHERE create_time >= '2023-01-01 00:00:00'
  AND create_time  1 OR indexed_id IS NULL)
```

#### **3. 优化索引结构**

```plsql
/* 重建复合索引顺序 */
-- 原索引：INDEX(status, create_time)
DROP INDEX idx_old ON orders;
CREATE INDEX idx_new ON orders(create_time, status);  -- 范围列前置

/* 添加覆盖索引 */
-- 高频查询：SELECT status, amount FROM orders WHERE user_id=?
CREATE INDEX idx_cover ON orders(user_id, status, amount);  -- 覆盖查询字段
```

#### **4. 干预优化器决策**

```plsql
# MySQL SSD优化 (my.cnf)
innodb_io_capacity=20000
innodb_read_io_threads=16
optimizer_switch='index_merge=on'

# PostgreSQL SSD优化 (postgresql.conf)
random_page_cost=1.1
effective_io_concurrency=200
```

#### **5. 终极端解决方案**

当所有优化无效时：

```plsql
-- 创建虚拟计算列 + 函数索引
ALTER TABLE orders
  ADD COLUMN create_date DATE AS (DATE(create_time)) VIRTUAL;
CREATE INDEX idx_func ON orders(create_date);  -- 对计算列创建索引

-- 业务层拆分查询：将复杂查询拆分为多个简单查询
```


# count(1)、count(_)与count(列名)的区别

面试SQL优化时可能会被问到 SQL Count（）的性能问题？

首先可以看下 SQL 中，COUNT() 函数用于统计行的数量。不同的用法 (COUNT(1), COUNT(*), COUNT(column_name)) 具有略有不同的行为和性能表现。以下是它们的具体区别：

### 1. COUNT(1)

* **功能**：
  * 统计表中行的数量，包含所有行，不论行中的值是什么。
* **工作原理**：
  * 每一行以常数 1 进行计算，即对于每一行都会计数一次，因此它的计算与 COUNT(*) 基本相同。
* **效率**：
  * 在某些数据库实现中，COUNT(1) 的性能可能与 COUNT(*) 相同，因为二者在功能上是等效的。

### 2. COUNT(*)

* **功能**：
  * 统计表中所有行的数量，包括所有列，无论列的值是否为 NULL。
* **工作原理**：
  * 按行统计时，不考虑列的具体值和数据类型。
* **效率**：
  * 是最常用的方法之一，特别是在 InnoDB 引擎中， COUNT(*) 通常是最优的计数形式，因为它被优化为直接统计数据页上的数目。

### 3. COUNT(column_name)

* **功能**：
  * 统计指定列中非 NULL 值的行数。
* **工作原理**：
  * 只计数该列中有非 NULL 值的行。因此，如果某行在 column_name 中的值为 NULL，则不会计入总数。
* **适用场景**：
  * 用于需要过滤掉 NULL 值时，例如，统计某个特定字段有值的记录数。

### 性能对比

* 现代数据库通常对 COUNT(*) 和 COUNT(1) 进行了优化，因此二者性能基本相似。
* COUNT(column_name) 可能较慢一些，特别是当列中有大量 NULL 值时，因为需要遍历和检查每一个值。

### 用法选择

* **大多数情况下**：COUNT(*) 是首选，因为它清晰明了并且通常是经过优化的。
* **特定需求**：当需要统计去除 NULL 值的特定列的值，只用 COUNT(column_name)。

### 小结

选择 COUNT(*)、COUNT(1) 或 COUNT(column_name) 应基于具体需求。如果只是需要统计总行数，可以使用 COUNT(*)。如果需要忽略某列中的 NULL 值，则需使用 COUNT(column_name)。它们之间选取的重要依据在于是否需要忽略 NULL 值及所用数据库的优化情况。

### 面试可能追问 count（\*）很慢，具体如何提升性能？

#### 1.首先要根据业务 数据量和过滤条件 来分析。

比如4000000数据量无过滤条件时间差不多。

![1740030761222-d89f9ab8-0bbe-4cd5-9745-5a2724eb7412.png](images/1740030761222-d89f9ab8-0bbe-4cd5-9745-5a2724eb7412.png)

如果业务需要的统计结果不需要特别精确

可以用 **explain**关键字 看filter 大概多少行，或者查询系统表\*\* information\_schema.tables。\*\*

**实例:这个存在误差但查询非常快。**

```java
EXPLAIN SELECT COUNT(*) FROM user_innodb where id>0;

SELECT *
FROM information_schema.tables
WHERE Table_schema = 'demo'
  AND table_name = 'user_innodb';
```

查询结果：

![1740030819665-5aebeb19-34c5-4281-9f9f-4e7bc32f60c6.png](images/1740030819665-5aebeb19-34c5-4281-9f9f-4e7bc32f60c6.png)

![1740030846027-4ddfd950-089b-4aaf-84a3-418ec776d7f9.png](images/1740030846027-4ddfd950-089b-4aaf-84a3-418ec776d7f9.png)

#### 2，explain分析sql看是否有优化的余地，最好能走主键索引。

通过上面explain可以看到 key走的不是primary ，加上过滤条件id>0速度能提升一截

![1740031050235-b77c8db5-5521-42ed-9b31-3a2956ffb7c3.png](images/1740031050235-b77c8db5-5521-42ed-9b31-3a2956ffb7c3.png)

#### 3，分批查询或者数据分片汇总统计

如果查询的结果集很大，可以考虑将查询分批进行，每次查询一部分数据，然后累加结果。这样可以减少单次查询的数据量，提高查询速度。

如果数据量非常大，可以考虑将数据进行分片存储，将数据分散到多个表或数据库中。这样可以将查询的数据量分散到多个节点上，提高查询性能。

4，**使用缓存或者直接新建统计表**

如果查询的结果不需要实时更新，可以将结果缓存在缓存中，避免每次查询都执行COUNT(*)操作。可以使用缓存技术如Redis或[Memcached](https://so.csdn.net/so/search?q=Memcached\&spm=1001.2101.3001.7020)来实现。

这里需要考虑Redis持久化，以及双写一致性的问题。避免宕机等因素影响精确度

如果对缓存的统计还不满意，可以新建一张统计表

如果是想精确的获取表的记录总数，我们可以将这个计数值保存到单独的一张计数表中。

当我们在数据表插入一条记录的同时，将计数表中的计数字段 + 1。也就是说，在新增和删除操作时，我们需要额外维护这个计数表。


# 为什么还会有人认为MySQL单表不要超过2000W数据

关于MySQL单表建议最大两千万行的说法，其核心依据主要源于InnoDB存储引擎的B+树索引结构对查询性能的影响，以及实际业务维护的经验总结。以下是详细分析：

***

### **1. B+树索引结构限制**

![1747317753732-3fa5f873-fbf5-44b2-91b4-90c5152f3cc2.png](images/1747317753732-3fa5f873-fbf5-44b2-91b4-90c5152f3cc2.png)

InnoDB使用B+树组织数据，主键索引（聚簇索引）的叶子节点直接存储行数据。

B+树的高度直接影响查询效率，树越高，磁盘I/O次数越多。以下为具体计算：

![1747317828754-6aef92cd-2107-4059-9122-83d54f463c2c.png](images/1747317828754-6aef92cd-2107-4059-9122-83d54f463c2c.png)

#### **关键参数**

![1747317855029-436fe338-27ce-4996-afba-eed1100e1e8e.png](images/1747317855029-436fe338-27ce-4996-afba-eed1100e1e8e.png)

* **页大小（Page Size）**：默认16KB（16384字节）。
* **主键类型**：假设使用BIGINT（8字节）或INT（4字节）。
* **指针大小**：InnoDB中每个页指针占6字节。
* **单行数据大小**：假设行数据平均约1KB。

#### **计算过程**

1. **非叶子节点容量**\ 每个非叶子节点存储主键值 + 指针。例如：
   * BIGINT主键：每个条目占 8+6=14字节。
   * 单页可存条目数：16384 / 14 ≈ 1170条。
2. **B+树高度与最大行数**
   * **高度为3时**：\ 根页 + 1170个二级页 + 1170×1170个叶子页。\ 叶子页总数：1170 × 1170 ≈ 1.37M页。\ 若每页存储约15行（1KB/行）：总行数 1.37M × 15 ≈ 20.5M。
   * **高度为4时**：\ 总行数飙升至 1170^3 × 15 ≈ 24亿，但查询需4次I/O，性能显著下降。

![1747547163604-7fba5c1b-01c6-4a19-a038-179b765c11b5.png](images/1747547163604-7fba5c1b-01c6-4a19-a038-179b765c11b5.png)

#### **为何建议两千万？**

* **经验平衡点**：在高度为3时，若单页存储行数更少（如因大字段或行格式限制），总行数可能降至约2000万。
* **性能拐点**：数据量接近B+树层级跃升临界值时（如从3层到4层），写入和范围查询效率会骤降。

![1747547120502-f030243e-6b9b-47d1-8fd0-f2ae1783f53a.png](images/1747547120502-f030243e-6b9b-47d1-8fd0-f2ae1783f53a.png)

***

### **2. 实际业务维护考量**

* **查询延迟**：单表过大时，即使走索引，扫描少量数据也可能因磁盘寻址变慢。
* **DDL操作风险**：修改表结构（如加列）需锁表或重建表，耗时与数据量正相关。
* **备份与恢复**：大表备份时间长，故障恢复风险高。
* **分库分表阈值**：提前规划水平拆分，避免性能恶化后紧急处理。

***

### **3. 其他影响因素**

* **行溢出（Row Overflow）**：若单行数据超过页大小（如含TEXT/BLOB），部分数据存于额外页，导致有效单页行数减少。
* **碎片化**：频繁增删导致页空间利用率低，实际容量小于理论值。
* **辅助索引**：二级索引叶子节点存储主键值，过多索引会增加存储压力，间接影响主树性能。

***

### **总结**

* **理论极限**：InnoDB单表可存储数十亿行，但性能会随B+树高度增加而下降。
* **经验建议**：2000万行是平衡查询效率、维护成本后的经验值，尤其在主键为BIGINT、行大小适中的场景下。
* **灵活调整**：实际阈值需根据硬件性能、数据访问模式（如冷热数据分离）动态评估。

***

### **优化建议**

![1747547082813-c7a3c414-086a-4545-90ef-5b63ad58dc7f.png](images/1747547082813-c7a3c414-086a-4545-90ef-5b63ad58dc7f.png)


# 一次性查2000万数据，MySQL会OOM吗？

在技术圈里，有一道非常经典的“送命题”在阿里和字节的面试中反复出现： **“如果不考虑网络传输慢的问题，我在 MySQL 里执行 ****SELECT ***** 一次性查 2000 万条数据，MySQL 的 Server 端会不会内存溢出（OOM）？”**

很多 3-5 年经验的 Java 工程师，第一反应往往是：“肯定会啊！2000 万行数据，就算一行 1KB，那也是 20GB 的数据量。MySQL 的 Buffer Pool 通常也就配个几 G，一次性加载进内存，绝对把堆内存撑爆，原地 OOM！”

如果你的答案也是“会”，那么恭喜你，这道题已经把你送进了面试的“火葬场”。 这个误区的根源在于，很多同学拿 **Java List** 的内存模型去套用数据库，却忽略了 MySQL 底层的**流式通讯协议**。

今天 Fox 就带你拆解这个经典陷阱，从源码层面揭秘真正能搞垮你数据库的“隐形杀手”。

### 地雷一：MySQL 真的会傻到“一口吞”吗？

首先给结论：**MySQL 服务端只要配置正常，绝对不会因为单次查询数据量大而 OOM！**

大家犯的错误，是用 Java `List.add()` 的思维去理解数据库。在 Java 里，你把 2000 万个对象加载到内存，那是“自杀”。但在 MySQL 里，这是一个\*\*流式（Streaming）\*\*过程。

![1768460600329-879b7053-1d90-41e2-9142-5b1dcde05323.png](images/1768460600329-879b7053-1d90-41e2-9142-5b1dcde05323.png)

**【底层原理解析】** MySQL 服务端并不是“把 2000 万行读完 -> 打包 -> 发送”，而是\*\*“边读边发”\*\*。

1. **扫描引擎层**：InnoDB 扫描出一行数据。
2. **写入缓冲区**：Server 层把这行数据塞进一个叫 `net_buffer` 的内存区域（对应参数 `net_buffer_length`，默认才 **16KB**！你没看错，是 KB）。
3. **触发发送**：一旦 `net_buffer` 写满了，或者一批数据读完了，MySQL 就会立马通过网络把这包数据推给客户端。
4. **清空复用**：发送成功后，清空 `net_buffer`，接着读下一行。

![1768460616885-d2c84122-bae0-481b-a24d-cf9ac7df973c.png](images/1768460616885-d2c84122-bae0-481b-a24d-cf9ac7df973c.png)

**真相大白：** 不管你的表有 2000 万行还是 200 亿行，MySQL 在服务端内存里暂存的数据，永远只有 `net_buffer_length` 定义的那么大。它就像一根水管，水是流过去的，不是积压在管子里的。 所以，MySQL 的内存根本不可能因此爆掉。

**防杠小贴士：** 当然，现实中你大概率等不到数据传完，客户端就会因为\*\*网络超时（Timeout）\*\*而断开连接；或者你的 Java 客户端因为接不住这么多数据先 OOM 了。但这锅得扣在网络和客户端头上，单论 MySQL 服务端，它是绝对撑得住的。

***

### 地雷二：没 OOM 就没事？真正的“死神”在后头

既然不会 OOM，那我是不是可以肆无忌惮地写全表扫描了？ **千万别！** 面试官挂掉你，不是因为你不懂 `net_buffer`，而是因为你完全没意识到全表扫描的真正破坏力。

虽然 MySQL 进程没死，但它会引发一种比 OOM 更恶心的灾难——**Buffer Pool 污染**。

![1768460731439-61bbe619-4036-4771-94f6-f400048de066.png](images/1768460731439-61bbe619-4036-4771-94f6-f400048de066.png)

**【生产惨案复盘】** 你的数据库内存（Buffer Pool）本来是很金贵的。里面存着全站最热的数据：

* 用户的登录 Session
* 秒杀活动的商品库存
* 首页的热门文章

这些数据在内存里，响应速度是毫秒级。 突然，你执行了一个 `SELECT *` 扫描 2000 万行冷数据（比如 3 年前的历史日志）。 InnoDB 会疯狂地从磁盘读取这些冷数据，塞进 Buffer Pool。

**后果：** 根据标准的 LRU（最近最少使用）算法，这些用一次就扔的垃圾数据，会把那些珍贵的热点数据全部**挤出内存**！ **结局：** 你的导出任务跑得很欢，MySQL 也没挂。但紧接着，全站用户发现登录变慢了、商品打不开了。 因为热点数据不在内存了，所有请求必须去读磁盘。磁盘 IO 直接打满，全站进入“假死”状态。

***

### 地雷三：InnoDB 的“防污染”护盾（源码级铁证）

有人会问：“Fox，那为什么我平时用 `mysqldump` 导数据，也没见把生产库搞挂啊？” 这就对了！因为 `mysqldump` 底层走的也是流式查询，它正好配合了 InnoDB 的 LRU **“冷热分离”** 策略，完美避开了热区污染。

![1768460646656-72ef8b31-753a-4f3b-a1f4-fd83ec2db0dc.png](images/1768460646656-72ef8b31-753a-4f3b-a1f4-fd83ec2db0dc.png)

既然大家都要“源码实锤”，今天 Fox 就带你直接扒掉 MySQL 的外衣，看看 InnoDB 引擎底层到底是怎么用 C++ 代码实现这个“防污染”逻辑的。

#### 铁证一：新数据默认“打入冷宫”

很多教程说“LRU 就是把新数据放到链表头部”，但在 InnoDB 源码里，全表扫描读进来的新数据，是直接插到 **Old Sublist 的头部**（也就是 LRU 链表的腰部/Midpoint），根本没资格碰热区！

![1768460679742-d7fee316-1e62-428c-b8ab-31f94ac76670.png](images/1768460679742-d7fee316-1e62-428c-b8ab-31f94ac76670.png)

**坐标：****storage/innobase/buf/buf0lru.cc**

```cpp
// 函数：buf_LRU_add_block (添加数据页到 LRU)
void buf_LRU_add_block(buf_pool_t* buf_pool, buf_page_t* bpage, ibool old)
{
    // ... 前置逻辑 ...

    // 【关键点 1】判断是否要加入到“冷链表”(old list)
    // 全表扫描时，这个 old 参数默认为 TRUE
    if (old) {
        // 直接插到 LRU_old 指针的位置（冷热交界处）
        // 这就是所谓的 "Midpoint Insertion Strategy"
        UT_LIST_INSERT_AFTER(LRU, buf_pool->LRU, buf_pool->LRU_old, bpage);
    } else {
        // 只有极其罕见的情况，才会直接插到头部
        UT_LIST_ADD_FIRST(LRU, buf_pool->LRU, bpage);
    }
}
```

**解析：** 看到 `if (old)` 了吗？新数据进来直接就被按在了冷区，根本没机会去污染 `LRU_new`（热区）。

#### 铁证二：时间门槛 (The Time Barrier)

这是最核心的逻辑。全表扫描时，虽然数据会被访问，但 InnoDB 会检查“你是不是刚进来的”。如果进来不到 1 秒（默认值），**拒绝晋升！**

![1768460701673-0009c3b6-6a1d-4337-b769-10935308abda.png](images/1768460701673-0009c3b6-6a1d-4337-b769-10935308abda.png)

**坐标：****storage/innobase/buf/buf0lru.cc**

```plain
// 函数：buf_page_make_young_if_needed (尝试将页面移动到热区)
void buf_page_make_young_if_needed(buf_pool_t* buf_pool, buf_page_t* bpage)
{
    // 【关键点 2】判断是否是“冷链表”里的数据
    if (buf_page_is_old(bpage)) {

        // 【关键点 3】时间与参数的硬碰硬
        // buf_LRU_old_threshold_ms 就是参数 innodb_old_blocks_time (默认 1000ms)
        if (now - access_time  发送 -> 读下一行。对同一个数据页的访问非常密集，基本都在几毫秒内完成。 `now - access_time` 肯定小于 1000ms，所以直接 return。 你的 2000 万行垃圾数据，只是在冷区里“一日游”，随后被淘汰。真正的热点数据（New Sublist）纹丝不动！

**注意：**`innodb_old_blocks_time` 这个机制专门针对全表扫描或大范围扫描这种批量加载场景，对正常的“常住居民”（高频单行查询）没有影响。

***

### ✅ 王者级回答模板（面试满分版）

下次再遇到面试官问“大表查询会不会 OOM”，别再踩坑了，直接把这套组合拳打出去：

“这个问题要从两个维度看。

**第一，关于 OOM（内存溢出）：** MySQL 服务端绝对不会 OOM。因为 MySQL 采用的是\*\*‘边读边发’的流式协议\*\*。数据是分批填充到 `net_buffer`（全称 `net_buffer_length`，默认 16KB）发送的，内存里不积压数据。真正可能 OOM 的是客户端（比如 Java List 接不住）。

**第二，真正的隐患（Buffer Pool 污染）：** 虽然物理内存不会崩，但全表扫描最大的风险是淘汰热点缓存。 如果是朴素的 LRU 算法，全表扫描会将热点数据全部挤出内存，导致磁盘 IO 飙升，引发系统雪崩。

**第三，InnoDB 的源码级防御：** InnoDB 采用了\*\*‘冷热分离’策略（Midpoint Insertion）\*\*。我看过 `buf0lru.cc` 的源码，新数据默认插入到 `LRU_old` 列表。 配合 `innodb_old_blocks_time`（默认 1s），全表扫描的数据因为‘访问间隔极短’，不满足晋升条件，只能在冷区被淘汰，从而完美保护了热点数据。”

***

**老哥最后再唠两句：** 细节决定成败，源码决定高度。 很多人觉得 MySQL 只是个存数据的黑盒子，但大厂面试考的就是你对这个黑盒子“脾气”的理解。能说出 `net_buffer` 的流式机制，能甩出 `buf_LRU_add_block` 的底层逻辑，你就是面试官眼里的 P7。

觉得这篇真的颠覆了你认知的，点个赞，收藏起来。


# 添加索引真的不会锁表吗？（onlineDDL）

# 1.MySQL DDL执行方式
MySQL5.5以及之前的版本，通常更改数据表结构操作(DDL)会阻塞对表数据的增删改操作(DML)。

MySQL5.6提供Online DDL之后可支持DDL与DML操作同时执行，降低了DDL期间对业务延迟带来的影响。

# 2.Online ddl：
### 概念：
在不中断现有数据读写操作的情况下，自动执行 DDL 语句 (例如创建、修改、删除表等) 的机制。Online DDL 可以在MySQL进行表空间或数据文件的变化时，自动执行 DDL 语句，从而避免了传统方式中，执行 DDL 语句时对数据库读写操作的干扰和中断。

### 执行过程：
Online ddl执行大致可分为三个阶段：初始化阶段、执行阶段和提交表定义阶段：
**初始化阶段：**

+ 评估存储引擎能力与DDL语句
+ 评估ALGORITHM 和 LOCK
+ 创建可升级的**MDL读锁**

**执行阶段：**

+ 此阶段分为两个步骤**准备**和**执行**DDL 语句
+ 此阶段是否需要MDL写锁取决于**初始化阶段**评估的因素。如果需要MDL写锁的话，仅在**准备过程**会**短暂的使用MDL写锁**，然后**降级为MDL读锁**
+ DDL执行过程（最耗时）

**提交表定义****阶段：**

+ 此阶段会将**MDL读锁升级到MDL写锁**，此阶段一般较快，因此独占锁的时间也较短
+ 用新的表定义替换旧的表定义，**释放MDL锁**

### 用法：
```sql
ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=INPLACE, LOCK=NONE;

ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=COPY, LOCK=EXCLUSIVE;
```

### 参数：
ALGORITHM：ALGORITHM=DEFAULT：默认算法，使用最高效的算法ALGORITHM=INPLACE：在原表上进行更改，不需要生成临时表，不需要进行数据copy的过程。添加索引步骤：1.创建索引(二级索引)数据字典2.加共享表锁，禁止DML，允许查询3.读取聚簇索引，构造新的索引项，排序并插入新索引4.等待打开当前表的所有只读事务提交5.创建索引结束ALGORITHM=COPY：最原始的方式，通过临时表创建索引，需要多一倍存储，还有更多的IO（类似5.6版本之前的处理过程）添加索引步骤：1.新建带索引（主键索引）的临时表2.锁原表，禁止DML，允许查询3.将原表数据拷贝到临时表4.禁止读写,进行rename，升级字典锁5.完成创建索引操作
LOCK：LOCK=DEFAULT：默认方式，MySQL自行判断使用哪种LOCK模式，尽量不锁表LOCK=NONE：无锁：允许Online DDL期间进行并发读写操作。如果Online DDL操作不支持对表的继续写入，则DDL操作失败，对表修改无效LOCK=SHARED：共享锁：Online DDL操作期间堵塞写入，不影响读取LOCK=EXCLUSIVE：排它锁：Online DDL操作期间不允许对锁表进行任何操作
### 注意事项：
不是所有的ddl都支持online ddl；如下官网给出的部分支持场景：
![1680509607122-5e10d223-1b05-44b5-80dc-03b7594755ff.png](images/1680509607122-5e10d223-1b05-44b5-80dc-03b7594755ff.png)
![1680509744854-3ae979f5-ef47-401f-a5b3-317a95bd104b.png](images/1680509744854-3ae979f5-ef47-401f-a5b3-317a95bd104b.png)
![1680509756926-7c09c2d5-bcf8-4db2-a849-62f5ef978805.png](images/1680509756926-7c09c2d5-bcf8-4db2-a849-62f5ef978805.png)
更多Online ddl支持场景，可以通过MySQL官方文档去获取
[https://dev.mysql.com/doc/refman/5.7/en/innodb-online-ddl-operations.html](https://dev.mysql.com/doc/refman/5.7/en/innodb-online-ddl-operations.html)

# 3.演示：
```sql
DROP TABLE IF EXISTS `scores`;
CREATE TABLE scores (
   id INT NOT NULL AUTO_INCREMENT COMMENT '序号',
   student_id INT NOT NULL COMMENT '学号',
   course_name VARCHAR(50) NOT NULL COMMENT '课程名称',
   score INT NOT NULL COMMENT '分数',
	 remarks varchar(400) COMMENT '备注',
	 PRIMARY KEY (id)
);ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

select count(*) from scores; --240w
```

### 1.使用ALGORITHM = INPLACE，Lock = NONE;
使用INPLACE，NONE时不阻塞其他事务的DML操作。

```sql
ALTER TABLE scores drop index idx_student_id;
事务A使用online ddl添加索引:
begin;
ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=INPLACE, LOCK=NONE;
commit;

1.事务A使用online ddl添加索引，事务B进行查询，可以正常读取：
begin;
select * from scores where id = 1 ;
commit;

2.事务A使用online ddl添加索引，事务B进行修改，可以正常修改：
begin;
update scores set course_name = '张三' where id = 1 ;
commit;

3.事务A使用online ddl添加索引，事务B进行删除，可以正常删除：
begin;
delete from scores where id = 1;
commit

4.事务A使用online ddl添加索引，事务B进行插入，可以正常插入：
begin;
INSERT INTO `scores` (`id`, `student_id`, `course_name`, `score`, `remarks`)
	VALUES ('1', '1', 'mock_Chinese1', '71', 'mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks');
commit;
```

### 2.使用ALGORITHM = COPY，Lock = EXCLUSIVE;
使用COPY，EXCLUSIVE时，会阻塞其他事务的DML操作。当DDL事务提交后，其他事务才能正常DML操作。

```sql
ALTER TABLE scores drop index idx_student_id;
事务A使用online ddl添加索引:
begin;
ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=COPY, LOCK=EXCLUSIVE;
commit;

1.事务A使用online ddl添加索引，事务B进行查询出现阻塞，需等事务A结束：
begin;
select * from scores where id = 1 ;
commit;

2.事务A使用online ddl添加索引，事务B进行修改出现阻塞，需等事务A结束：
begin;
update scores set course_name = '张三' where id = 1 ;
commit;

3.事务A使用online ddl添加索引，事务B进行删除出现阻塞，需等事务A结束：
begin;
delete from scores where id = 1;
commit

4.事务A使用online ddl添加索引，事务B进行插入出现阻塞，需等事务A结束：
begin;
INSERT INTO `scores` (`id`, `student_id`, `course_name`, `score`, `remarks`)
	VALUES ('1', '1', 'mock_Chinese1', '71', 'mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks_mock_remarks');
commit;
```

### 3.模拟online ddl执行时，有其他事务持有MDL锁。
Online DDL 过程必须等待已经持有MDL锁的并发事务提交或者回滚才能继续执行。

```sql
ALTER TABLE scores drop index idx_student_id;
事务A进行查询，不提交事务:
begin;
select * from scores;
--commit;

事务B使用online ddl添加索引，阻塞中:
begin;
ALTER TABLE scores ADD index idx_student_id (student_id) , ALGORITHM=INPLACE, LOCK=NONE;
commit;

事务C进行查询，阻塞中:
select * from scores where id = 1 ;

查询进程信息：
show processlist;
```

# 4.总结：
在online ddl执行过程会两次获取MDL锁，并且需要等待已经持有DML锁的并发事务提交或回滚后才能继续执行，在实际执行时需注意以下几点：

+ 进行DDL操作时尽量在业务低峰期进行操作。
+ 在操作之前最好确认对要操作的表没有任何进行中的操作、没有未提交事务、也没有显式事务中的报错语句。
+ 设置超时时间lock_wait_timeout，避免长时间的metedata锁等待。


# 讲讲你对MVCC的理解

兄弟们，去面中大厂的后端核心岗，**MVCC (多版本并发控制)** 绝对是区分“CRUD Boy”和“架构师”的分水岭。 面试官问你 MVCC，表面问的是概念，实则在考察你对\*\*“事务、锁、并发、存储引擎”\*\*的综合理解。

很多同学只能背出“快照读”，一旦被追问：“**ReadView 到底什么时候生成？**”、“**Undo Log 既然是链表，什么时候清理？**”、“**我看不到这条数据，但我能 UPDATE 它吗？**”，立马就会现原形。

今天 Fox 带你从源码级视角拆解 MVCC，助你面试**降维打击**！

***

## ⚔️ 第一部分：什么是 MVCC？（一句话定调）

**话术模板：**

“MVCC 的全称是多版本并发控制。它的核心思想是：**通过维护数据的多个历史版本，让读操作去读历史快照，写操作去更新最新版本，从而实现读写并行，互不阻塞。**”

**核心价值：**

* **读写解耦**：写操作加锁（当前读），读操作不加锁（快照读）。
* **提升性能**：极大地提高了数据库的高并发处理能力。

***

## ⚙️ 第二部分：MVCC 的“三驾马车”实现原理

要讲清楚 MVCC，必须把这三个组件讲透：**隐藏字段、Undo Log、ReadView**。

### 1. 隐藏字段（聚簇索引的秘密）

InnoDB 会在每行数据（聚簇索引）后面悄悄加三个字段：

* **DB\_TRX\_ID**（6字节）：**事务 ID**，记录最近一次修改这行数据的事务 ID。
* **DB\_ROLL\_PTR**（7字节）：**回滚指针**，指向 Undo Log 中这行数据的上一个版本。
* **DB\_ROW\_ID**：隐藏主键（如果表没有主键才会生成）。

![1768458850074-829cae90-1b1f-47bf-8fab-c0775c86147f.png](images/1768458850074-829cae90-1b1f-47bf-8fab-c0775c86147f.png)

**🔥**\*\* 高手加分点（二级索引）：\*\* 面试官如果问：“二级索引也有这两个隐藏字段吗？” 你要回答：**“没有！”** 二级索引页头有个 `PAGE_MAX_TRX_ID`。如果这个 ID 小于当前事务的可见性水位，直接读；否则，需要**回表**到聚簇索引，利用聚簇索引上的 `DB_TRX_ID` 和 Undo Log 来做版本判断。

### 2. Undo Log（版本链）

当你更新一行数据时，InnoDB 不会直接覆盖旧数据，而是先把旧数据拷贝到 **Undo Log** 里。 `DB_ROLL_PTR` 就像一根链条，把新老数据串起来，形成一个**版本链**。链头是最新数据，链尾是最老数据。

![1768458879268-d50cb9d7-f7dd-4572-8677-7d112b12c3f7.png](images/1768458879268-d50cb9d7-f7dd-4572-8677-7d112b12c3f7.png)

### 3. ReadView（读视图）—— 裁判员

这是 MVCC 的灵魂！ReadView 是一个\*\*“快照切片”\*\*，决定了你到底能看到版本链里的哪一个版本。 核心字段：

* **m\_ids**：生成 ReadView 时，当前系统中\*\*活跃（未提交）\*\*的事务 ID 列表。
* **min\_trx\_id**：活跃事务中最小的 ID（低水位）。
* **max\_trx\_id**：系统应该分配给下一个事务的 ID（高水位）。
* **creator\_trx\_id**：生成该 ReadView 的事务 ID（我自己）。

![1768458893718-511d928d-67bf-4bf3-b85f-dbfef78e54cf.png](images/1768458893718-511d928d-67bf-4bf3-b85f-dbfef78e54cf.png)

***

## ⚖️ 第三部分：数据的“可见性算法”（面试高频）

![1768458921334-dcea170f-2389-41fe-91da-270abf14f656.png](images/1768458921334-dcea170f-2389-41fe-91da-270abf14f656.png)

拿着行记录的 `TRX_ID` 去跟 ReadView 比对，规则如下：

1. **自己改的** (`TRX_ID == creator_trx_id`)：✅ **可见**。
2. **已提交的旧事务** (`TRX_ID = max_trx_id`)：❌ **不可见**（你是在我生成快照后才出现的）。
4. **复杂的中间地带** (`min_trx_id  顺着 Undo Log 找上一个版本。
   * **不在**：说明虽然 ID 较大，但已经提交了，✅ **可见**。

***

## 🥊 第四部分：RC 和 RR 的本质区别（进阶杀手锏）

面试官追问：“为什么 RC 能读到新提交的，而 RR 读不到？” **这是 P6 和 P7 的分水岭！** 答案在于 **ReadView 生成的时机不同**。

![1768458965224-63c4a869-619e-4315-8dfc-3df80ddfbb8f.png](images/1768458965224-63c4a869-619e-4315-8dfc-3df80ddfbb8f.png)

* **RC（读已提交）**：
  * **每次 SELECT 语句执行时**，都会重新生成一个新的 ReadView。
  * 所以，只要别的事务提交了，新的 ReadView 就能看到。
* **RR（可重复读）**：
  * **⚠️**\*\* 纠偏细节\*\*：不是一开启事务就生成，而是**在事务中执行第一条快照读（SELECT）时**，生成一个 ReadView。
  * **之后所有的 SELECT，都复用这同一个 ReadView**。
  * 这就实现了“可重复读”：不管外面怎么翻江倒海，我看的一直是刚开始的那个快照。

***

## 💣 第五部分：面试避坑指南（这才是高手的细节）

这里有三个**只有架构师才会关注**的细节，抛出来绝对震惊面试官：

### 1. MVCC 能完全解决幻读吗？

**标准回答：**

“MVCC 解决了**快照读**下的幻读，但没有解决**当前读**下的幻读。”

* **快照读**（普通 `SELECT`）：靠 ReadView 复用，看不到新插入的数据 -> **解决了**。
* **当前读**（`SELECT FOR UPDATE`, `UPDATE`）：必须读最新版。如果不加锁，别人插入新数据，你就能更新到，产生幻读。
* **最终解法**：在 RR 级别下，**当前读**是通过 **Next-Key Lock（临键锁）** 锁住间隙来彻底解决幻读的。

### 2. “看不见”的数据，我能 UPDATE 吗？（诡异悖论）

**场景**：RR 级别，事务 A 插入并提交了一条记录。事务 B（在 A 提交前开启）SELECT 看不到这条记录（因为 ReadView 老）。 **问题**：事务 B 能执行 `UPDATE` 这条“看不见”的记录吗？ **答案**：\*\*能！而且更新完后，再次 SELECT 就能看见了！\*\***原理**：

* `UPDATE` 是**当前读**，它不看 ReadView，直接读最新提交的数据，所以能更新成功。
* 更新成功后，这条记录的 `TRX_ID` 变成了事务 B 自己的 ID。
* 再次 SELECT 时，根据可见性规则“**自己改的可见**”，你就看到了！

### 3. Undo Log 会无限膨胀吗？（Purge 机制）

**问题**：历史版本这么多，磁盘不爆吗？ **答案**：不会。MySQL 有后台 **Purge 线程**。 当系统中最老的 ReadView 都不再需要某个事务版本之前的记录时，Purge 线程就会自动清理掉那些无用的 Undo Log。

**延伸**：这也是为什么我们**千万不要在生产环境搞长事务**！长事务会导致 ReadView 一直不关闭，Undo Log 无法回收，导致表空间极速膨胀，查询变慢。

***

## 🎓 第六部分：满分总结（背诵版）

最后，给面试官来个**降维打击式**的总结：

“MySQL 的 MVCC 本质上是**空间换时间**，通过维护**Undo Log 版本链**和**ReadView**，实现了读写并发。

它的核心在于：

1. **结构上**：利用聚簇索引的隐藏字段和 Undo Log 构建历史版本。
2. **流程上**：通过 ReadView 机制判断版本可见性。RC 级别是‘次次生成’，RR 级别是‘一次生成，终身复用’。
3. **边界上**：它解决了快照读的幻读，但当前读的幻读依然需要 Next-Key Lock 配合解决。同时，还要注意 Purge 机制回收日志，避免长事务导致系统膨胀。”

![1768459021183-67bf0d8b-ee59-486f-99ee-bf7b7e7bc71d.png](images/1768459021183-67bf0d8b-ee59-486f-99ee-bf7b7e7bc71d.png)

***

**Fox 老师寄语：** 兄弟们，这才是真正的底层原理。理解了这些，你不光能过面试，以后在生产环境排查死锁、慢查询、回滚空间膨胀这些问题时，你脑子里会有一幅清晰的图。 觉得有用的，**点赞、收藏**，下次面试前拿出来复习一遍，绝对稳！


# 索引失效的问题如何排查

排查索引失效的问题对于保持数据库查询性能的高效至关重要。当数据库索引未被使用时，查询性能可能显著下降。以下是发现和排查索引失效的方法及策略：

### 1. 使用 EXPLAIN 诊断查询

* **分析查询执行计划**：
  * 使用 EXPLAIN 命令查看查询的执行计划，判断索引是否被利用。
  * 检查输出中的 type 字段（最好是 ref 或 const），避免使用全表扫描 (ALL)。

### 2. 常见索引失效原因

* **函数和表达式**：
  * 在 WHERE 子句中对索引字段应用函数（如 YEAR(date) ）可能使索引用不了。
  * 避免在索引字段上直接进行运算或类型转换。
* **前导模糊查询**：
  * 使用 LIKE '%abc%' 模糊查询时，前置的百分号会导致索引失效，因为无法利用索引进行前缀定位。
* **不等式条件**：
  * <> 或 NOT IN 操作符通常会导致索引失效，应尽量使用等值查询。
* **范围条件的影响**：
  * 在复合索引中，使用范围操作符（如 >、、BETWEEN）可能导致后续的索引列失效。

### 3. 优化查询结构

* **改写条件**：
  * 改写 WHERE 子句以利用索引，例如将 WHERE UPPER(name) = 'ABC' 改为 WHERE name = 'abc' 并保证列字段存储小写。
* **运用等效替代**：
  * 将不等操作分解为多个等值条件（如将 NOT IN 转为 OR）。

### 4. 检查索引和表设计

* **审查索引的设计**：
  * 确保字段的索引顺序与查询条件匹配，用最左前缀规则审查复合索引。
* **数据类型匹配**：
  * 检查查询条件中的类型，确保与列的数据类型一致，避免隐式转换。

### 5. 数据库配置和统计信息

* **更新统计信息**：
  * 如果索引存在但未被使用，检查并更新数据库统计信息，帮助优化器选择最优计划。
* **检查连接参数**：
  * 确保全局数据库和连接特定的配置（如查询缓存设置）未阻碍索引的使用。

### 6. 限制和事务问题

* **死锁和锁问题**：
  * 检查是否存在锁问题（如表锁、行锁）阻止索引的使用。
* **事务隔离级别**：
  * 较高的事务隔离级别可能影响索引利用，通过优化事务管理来改善。

### 小结

索引失效往往与查询模式变化、不当的索引设计以及数据库统计信息不准确有关。通过上述方法，可以系统地识别并解决索引失效的问题，确保数据库的高效运行。排查过程还需要结合具体业务场景进行分析和测试，以找到适合的解决方案。


# 如何进行SQL调优

SQL调优（SQL Optimization）是提升数据库查询性能的关键步骤。通过优化SQL查询，可以显著提高应用程序的响应速度和系统效率。以下是进行SQL调优的一些有效策略和技巧：

### 1. 分析查询性能

* **使用查询分析工具**：
  * 利用数据库提供的性能分析工具（如 MySQL 的 EXPLAIN、ANALYZE）来查看查询的执行计划和性能瓶颈。
* **查看执行时间**：
  * 通过查询日志分析执行时间，找出响应时间较长的SQL语句进行优化。

### 2. 合理使用索引

* **创建适当的索引**：
  * 针对查询的条件列（WHERE、JOIN）、排序（ORDER BY）、分组（GROUP BY）等，创建相应的索引。
* **避免过多索引**：
  * 过多的索引会影响写性能，选择对查询影响最大的列进行索引。
* **优化复合索引**：
  * 使用复合索引优化多列查询，并确保索引顺序符合查询使用模式的最左前缀原则。

### 3. 重写SQL语句

* **简化查询条件**：
  * 避免在 WHERE 子句中使用复杂计算和函数。
  * 使用简单易理解的条件表达式。
* **使用\*\*\*\* ****JOIN**** \*\*\*\*替代子查询**：
  * 在可能的情况下，使用 JOIN 替代子查询，以提升性能。
* **避免\*\*\*\* ****SELECT ***：
  * 明确选择需要的列而不是使用 SELECT *，以减少不必要的列访问。

### 4. 优化数据模型

* **规范化与反规范化**：
  * 确保表结构合理，必要时对数据进行反规范化以优化查询性能。
* **使用合适的数据类型**：
  * 选择合适的数据类型，以减少存储和内存占用。

### 5. 缓存和批量操作

* **缓存常用查询**：
  * 利用缓存技术（如 Redis、Memcached），降低数据库负载，提升查询响应速度。
* **批量数据操作**：
  * 尽量使用批量插入、更新操作，减少数据库交互次数。

### 6. 更新和维护数据库

* **定期重建索引**：
  * 定期维护和重建索引以防止索引碎片影响性能。
* **更新统计信息**：
  * 确保数据库统计信息是最新的，以帮助优化器选择最佳执行计划。

### 7. 分布式和分区策略

* **表分区或分片**：
  * 对于大表，可以考虑水平或垂直分区，以改善性能。
* **负载均衡**：
  * 利用负载均衡分配查询负载，以提高系统性能。

### 8. 数据库和硬件优化

* **调整数据库配置**：
  * 如内存分配，连接池大小等设置应根据具体用例和应用程序需求来调节。
* **硬件优化**：
  * 合理使用 SSD，增加内存，或优化网络连接等硬件层优化。

### 小结

SQL调优需要从多个方面入手，包括查询本身的优化和数据库配置的优化。遵循这些原则和方法能够帮助发现性能瓶颈，进而提升整个系统的处理能力和响应速度。另外，在调优过程中，持续的监控和反馈将会为不断改善提供有价值的建议和数据支持。


# 我查这么多数据，会不会把数据库内存打爆？

最近被问到这样一个问题：我的主机内存只有100G，现在要对一个200G的大表做全表扫描，会不会把数据库主机的内存用光了？

顿时有点无语，很明显不会啊，MySQL 逻辑备份就是做整库扫描，如果这样就会把内存吃光，逻辑备份不是早就挂了，那为什么不会打爆呢？

### 全表扫描对server层的影响
假设，我们现在要对一个200G的InnoDB表db1. t，执行一个全表扫描。当然，你要把扫描结果保存在客户端，会使用类似这样的命令：

```plsql
select * from db1.t > $target_file
```

InnoDB的整行数据是保存在主键索引上的，所以全表扫描实际上是直接扫描表t的主键索引。这条查询语句由于没有其他的判断条件，所以查到的每一行都可以直接放到结果集里面，然后返回给客户端。

那么，这个“结果集”存在哪里呢？

实际上，服务端并不需要保存一个完整的结果集。取数据和发数据的流程是这样的：

1. 获取一行，写到net_buffer中。这块内存的大小是由参数net_buffer_length定义的，默认是16k。
2. 重复获取行，直到net_buffer写满，调用网络接口发出去。
3. 如果发送成功，就清空net_buffer，然后继续取下一行，并写入net_buffer。
4. 如果发送函数返回EAGAIN或WSAEWOULDBLOCK，就表示本地网络栈（socket send buffer）写满了，进入等待。直到网络栈重新可写，再继续发送。

![1727101191866-29b9d58f-f0fb-4b37-8e88-b4235081521c.jpeg](images/1727101191866-29b9d58f-f0fb-4b37-8e88-b4235081521c.jpeg)

从这个流程中，你可以看到：

1. 一个查询在发送过程中，占用的MySQL内部的内存最大就是net_buffer_length这么大，并不会达到200G；
2. socket send buffer 也不可能达到200G（默认定义/proc/sys/net/core/wmem_default），如果socket send buffer被写满，就会暂停读数据的流程。

也就是说，**MySQL是“边读边发的”**。这就意味着，如果客户端接收得慢，会导致MySQL服务端由于结果发不出去，这个事务的执行时间变长，但是不会导致数据库内存打爆。

### 全表扫描对InnoDB的影响
接着来看看，全表查询对innoDB的影响，

内存的数据页是在buffer pool中管理的，在WAL里 buffer pool 起到了加速更新的作用，同时也起到了加速查询。

比如更新了一个SQL，但是由于WAL机制，数据先是写到buffer pool中，然后磁盘的数据还是旧的，如果这个时候来了一个查询，那么就会直接从buffer pool中直接读取数据返回，可以加速读的作用。

可以通过 show engine innodb status 显示当前的命中率。

InnoDB Buffer Pool 的大小是由参数 innodb_buffer_pool_size 确定的，一般建议设置成可用物理内存的 60%~80%。

```plsql
show variables like '%innodb_buffer_pool_size%';
```

但是数据是远远超过物理内存的，这个时候如果一个 Buffer Pool 已经满了，还需要从磁盘读入一个数据页，那肯定是要淘汰一个旧数据页的，所以就有一定的淘汰算法，LRU。

![1727101192226-491ce0b0-e107-458f-8e87-6211900d97ea.jpeg](images/1727101192226-491ce0b0-e107-458f-8e87-6211900d97ea.jpeg)

InnoDB管理Buffer Pool的LRU算法，是用链表来实现的。

1. 在上图的状态1里，链表头部是P1，表示P1是最近刚刚被访问过的数据页；假设内存里只能放下这么多数据页；
2. 这时候有一个读请求访问P3，因此变成状态2，P3被移到最前面；
3. 状态3表示，这次访问的数据页是不存在于链表中的，所以需要在Buffer Pool中新申请一个数据页Px，加到链表头部。但是由于内存已经满了，不能申请新的内存。于是，会清空链表末尾Pm这个数据页的内存，存入Px的内容，然后放到链表头部。
4. 从效果上看，就是最久没有被访问的数据页Pm，被淘汰了。

这个算法乍一看上去没什么问题，但是如果考虑到要做一个全表扫描，会不会有问题呢？

假设按照这个算法，我们要扫描一个200G的表，而这个表是一个历史数据表，平时没有业务访问它。

那么，按照这个算法扫描的话，就会把当前的Buffer Pool里的数据全部淘汰掉，存入扫描过程中访问到的数据页的内容。也就是说Buffer Pool里面主要放的是这个历史数据表的数据。

对于一个正在做业务服务的库，这可不妙。你会看到，Buffer Pool的内存命中率急剧下降，磁盘压力增加，SQL语句响应变慢。

所以，InnoDB不能直接使用这个LRU算法。实际上，InnoDB对LRU算法做了改进。

![1727101192369-6006f7b4-100f-4f2c-ae37-ae77287b40ca.png](images/1727101192369-6006f7b4-100f-4f2c-ae37-ae77287b40ca.png)

在InnoDB实现上，按照5:3的比例把整个LRU链表分成了young区域和old区域。图中LRU_old指向的就是old区域的第一个位置，是整个链表的5/8处。也就是说，靠近链表头部的5/8是young区域，靠近链表尾部的3/8是old区域。

改进后的LRU算法执行流程变成了下面这样。

1. 上图中状态1，要访问数据页P3，由于P3在young区域，因此和优化前的LRU算法一样，将其移到链表头部，变成状态2。
2. 之后要访问一个新的不存在于当前链表的数据页，这时候依然是淘汰掉数据页Pm，但是新插入的数据页Px，是放在LRU_old处。
3. 处于old区域的数据页，每次被访问的时候都要做下面这个判断：
    - 若这个数据页在LRU链表中存在的时间超过了1秒，就把它移动到链表头部；
    - 如果这个数据页在LRU链表中存在的时间短于1秒，位置保持不变。1秒这个时间，是由参数innodb_old_blocks_time控制的。其默认值是1000，单位毫秒。

这个策略，就是为了处理类似全表扫描的操作量身定制的。还是以刚刚的扫描200G的历史数据表为例，我们看看改进后的LRU算法的操作逻辑：

1. 扫描过程中，需要新插入的数据页，都被放到old区域;
2. 一个数据页里面有多条记录，这个数据页会被多次访问到，但由于是顺序扫描，这个数据页第一次被访问和最后一次被访问的时间间隔不会超过1秒，因此还是会被保留在old区域；
3. 再继续扫描后续的数据，之前的这个数据页之后也不会再被访问到，于是始终没有机会移到链表头部（也就是young区域），很快就会被淘汰出去。

可以看到，这个策略最大的收益，就是在扫描这个大表的过程中，虽然也用到了Buffer Pool，但是对young区域完全没有影响，从而保证了Buffer Pool响应正常业务的查询命中率。

### 小结
结论是mysql采用边算边发的策略，查询很大的数据表，不会将内存打爆，而InnoDB引擎内部，有淘汰策略，并且对LRU进行了改进，对Buffer pool做到可控。


# MySQL8的索引跳跃扫描是什么

MySQL中的索引跳跃扫描（Skip Scan）是一种优化策略，旨在提高在特定条件下对复合索引的利用效率。尽管MySQL并没有明确标记这项技术为"Skip Scan"功能，但通过其优化器的改进，特别是在MySQL 8.0.13及其后的版本中，MySQL可以在某些条件下实现类似Skip Scan的效果。让我们通过一个具体示例来说明其概念和潜在应用。

### 示例背景

假设有一个包含以下数据结构的表employees：

| **ID** | **Department** | **Position** |
| --- | --- | --- |
| 1 | Sales | Executive |
| 2 | Sales | Manager |
| 3 | Sales | Stuff |
| 4 | Sales | Stuff |
| 5 | HR | Executive |
| 6 | HR | Manager |
| 7 | HR | Stuff |
| 8 | IT | Executive |
| 9 | IT | Manager |
| 10 | IT | Stuff |

并且在表上有一个复合索引 (Department, Position)。

### 查询场景

假设我们希望查找所有Manager职位的员工：

```sql
SELECT * FROM employees WHERE Position = 'Manager';
```

### 传统索引处理

如果正常按索引(Department, Position)的顺序使用，理想情况下需要首先给出Department条件，以充分利用索引优势，但本查询并没有提供对Department的条件。

### 跳跃扫描的优化实现（概念性）

通过类似Skip Scan的逻辑，MySQL优化器可能会：

1. **分区扫描**：
   * 将索引按Department的唯一值进行分割。每个分区相当于不同的部门，比如Sales、HR、IT。
2. **应用条件**：
   * 对每个Department分区中的Position行进行扫描，即跳跃扫描中仅搜索Position = 'Manager'的员工。
3. **跳过无关分区**：
   * 由于Position = 'Manager'限定，我们只在每个Department的分区中寻找匹配的Position，而不是对整个表进行扫描。

### 实际效果

虽然MySQL索引跳跃扫描概念上并不是一个独立标识的特性，但此类索引优化策略在新版MySQL中可能通过改进的索引条件推送和查询优化器来实现。它潜在地减少读取和滤除不必要数据的开销。

这种策略在数据有较低基数（即Department的唯一值少）的场景中特别有效，因为跳跃的次数减少，提高了效率。可通过 EXPLAIN 检查特定查询的实际执行计划以确认优化的应用。

[bilibili](https://player.bilibili.com/player.html?bvid=BV1kFpue5Ehj\&p=11\&page=11\&autoplay=0)


# 用了索引还是慢可能是什么原因

使用索引查询仍然很慢的原因可能有多种，下面是一些常见的问题和可能的解决方案：

### 可能原因及解决方案

1. **索引不匹配查询**：
   * **原因**：查询没有使用最优的索引，例如使用了前缀不匹配的索引或者多列索引使用顺序错误。
   * **解决方案**：检查查询计划(EXPLAIN语句)以确保查询在使用正确的索引。确保查询语句的条件顺序与联合索引的列顺序匹配。
2. **数据分布不均**：
   * **原因**：索引选择性差，数据分布不均匀时索引效果较差。
   * **解决方案**：可以考虑重建索引或添加不同的索引来优化数据访问。
3. **索引的维护开销**：
   * **原因**：在大量写操作的表上，索引会增加写操作的开销。
   * **解决方案**：对于频繁更新的表，尽量减少索引数量，且只保留必要的索引。
4. **查询的非优化部分**：
   * **原因**：即使索引使用正确，查询中其他部分可能未优化，如在大结果集上进行排序或聚合操作。
   * **解决方案**：优化查询结构，考虑分页及限定范围的术语来减少处理数据的数量。
5. **硬件资源限制**：
   * **原因**：硬件性能瓶颈，如I/O速度、CPU和内存限制导致查询慢。
   * **解决方案**：升级硬件配置，增加内存，使用SSD代替HDD，甚至分片数据库以提升性能。
6. **表和索引的统计信息过期**：
   * **原因**：MySQL的查询优化器依赖于表统计信息，若这些信息不准确，则优化效果差。
   * **解决方案**：定期运行 ANALYZE TABLE 来更新统计信息，以帮助优化器做出更好的决策。
7. **锁争用**：
   * **原因**：高并发查询导致锁争用严重，尤其在写操作频繁的表。
   * **解决方案**：优化锁的粒度或将表划分成多个分表以降低锁竞争。
8. **不当的表设计**：
   * **原因**：如字段设计不合理，数据类型过大，或未能规范化数据。
   * **解决方案**：重新审视表结构，考虑字段类型和设计规范。

### 进一步分析

要解决查询速度慢的问题，您可以使用以下步骤来识别和解决性能瓶颈：

1. **使用\*\*\*\* ****SHOW INDEX FROM table_name**** \*\*\*\*查看当前索引**，确保索引按预期创建。
2. **使用\*\*\*\* ****EXPLAIN**** \*\*\*\*分析特定查询**，查看MySQL如何执行查询（执行计划）。
3. **监控系统资源**，例如使用工具如 top, iostat，以及数据库特有工具如 SHOW STATUS。
4. **评估操作日志和慢查询日志**，找出哪些查询消耗了大部分资源。

通过检查和调整上述因素，您可以提高数据库的查询性能。如果问题仍然存在，可以考虑咨询数据库专家或进行结构性的架构调整来应对更高的性能需求。


# 加密后的数据该如何支持模糊查询

在日常工作中，我们经常会有一些模糊查询的条件，比如说按照手机号模糊查询，或者是身份证号码。正常情况下我们可以使用

```plsql
select * from user where mobile like %123%
```

来模糊查询，但是这种方式是在你的手机号码没有加密的前提下，但是对于一些用户私密数据，我们在数据库都会进行加密保存。这时候有些人会说，那我把条件也加密，然后进行模糊查询不就可以了吗？事实真是这样吗？

看下面这个例子，我们将手机号进行加密，这时候我们要搜索手机前缀为136的手机号，这时候你讲条件进行加密，然后查询，你会发现，加密出来的是二个完全不一样的字符串，所以你根本就查不出来

![1729508972314-33b76e35-a7dc-4dc1-9abd-a2fbb4ff1136.png](images/1729508972314-33b76e35-a7dc-4dc1-9abd-a2fbb4ff1136.png)

## 方案一：**内存解密**(数据量少可用，数据量多不推荐)

第一种方案就是我们可以将所有数据都查询出来，然后在内存中将所有的手机号进行解密，然后在做一个匹配，这种方式优缺点也很明显

优点

* 1：简单方便，没有复杂的实现逻辑

缺点

* 1:每次查询都需要把整张表的数据都查询来，然后将所有的手机号进行解密
* 2:如果数据量过大，就会导致OOM的异常

## 方案二：**映射查询**(解决了，又好像没解决)

我们现在是要按照手机号进行一个模糊查询，这时候我们可以建一张表，这张表就的字段有二个，一个是手机号，一个是手机号加密后的数据

```sql
id   mobile                mobileSm4                              userID
1    18912359512           vCWbXmNO7mAkIQEGLoVQwQ==                 1
2    15975374387           vM6675stu2HOmjmhvUtwUA==            			2
```

这时候比如我们要查询手机号前缀是 189 的数据，我们可以先查这张表 select userId from user\_mobile where mobile like %189%

这时候就可以拿到对应的userId，然后再去用户表去查询我们需要的记录，看起来好像是解决了这个问题，但是仔细想想，我们的手机号还是没有加密存储，所以说好像是解决了这个问题，但是好像又没解决，手机号还是存在明文存储

## 方案三：加密函数

在数据库中实现与程序一致的加解密算法，修改模糊查询条件，使用数据库加解密函数先解密再模糊查找，这样做的优点是实现成本低，开发使用成本低，只需要将以往的模糊查找稍微修改一下就可以实现，但是缺点也很明显，这样做无法利用数据库的索引来优化查询，甚至有一些数据库可能无法保证与程序实现一致的加解密算法，但是对于常规的加解密算法都可以保证与应用程序一致。

如果对查询性能要求不是特别高、对数据安全性要求一般，可以使用常见的加解密算法比如说AES、DES之类的也是一个不错的选择。

如果公司有自己的算法实现，并且没有提供多端的算法实现，要么找个算法好的人去研究吃透补全多端实现，要么放弃使用这个办法。

## 方案四：**分片加密**(推荐)

密文检索的功能实现是根据4位英文字符（半角），2个中文字符（全角）为一个检索条件。将一个字段拆分为多个，

比如：taobao123\
使用4个字符为一组的加密方式。\
第一组 taob ，第二组aoba ，第三组obao ，第四组 bao1 … 依次类推\
如果需要检索 所有包含 检索条件4个字符的数据 比如：aoba ，加密字符后通过key like “%partial%” 查库。

我们的手机号是11位数，我们每4位作为一个分片

```java
public static void main(String[] args) {
    String mobile = "12345678765";
    int index = 0;
    for(;;) {
        String str = mobile.substring(index);
        if(str.length()  来自: 加密后的数据该如何支持模糊查询大家好


# 通俗易懂-MySQL常用函数解析

## ![1743341729896-ff5ffe14-d86c-40c5-84b7-ea069a5d55de.png](images/1743341729896-ff5ffe14-d86c-40c5-84b7-ea069a5d55de.png)

## 数学函数

#### count()

`count()`、`count(field)` 统计某个结果集中的总数量，`field`为要统计的字段。

```plsql
select count( 1 ) from order_details;
```

***

#### sum()

`sum(field)` 统计某个字段累计的总和，field为要统计的字段。

```plsql
select sum( price ) from order_details;
```

***

#### avg()

`avg(field)` 统计某个字段的平均数，field为要统计的字段。

```plsql
select avg( price )  from order_details;
```

***

#### round()

`round(number,x)`返回某个数字按指定位数取整后的数字，`number`被操作的数字，`x`为精确的位数

```plsql
# 返回 123.4600
select round(123.4567,2);

# 返回 765.4300
select round(765.4321,2);
```

***

#### abs()

`abs(number)` 取绝对值

```plsql
# 返回 88
select abs(-88);
```

#### rand()

`rand()` 返回0-1.0之间的浮点随机数

```plsql
-- 返回 0.7680746612773041
select rand();
```

***

## 类型转换

#### cast()

`cast(data as type)` 将一种类型的数据转换成另一种类型。data为数据， type为类型。

必须是数据库支持的数据类型。

```plsql
# SIGNED 可以是正数、负数或零
# UNSIGNED 只能是零或正数，不能为负数

# 将字符的123转换成数字的123
SELECT CAST('123' AS SIGNED);
```

***

## 字符串函数

#### concat()

`concat(data1,data2,data3,datan...)`拼接字符串。

如果其中一个数据为`null`则返回`null`。

```plsql
# 返回 1234
select concat(1,2,3,4);

# 返回 null
select concat(1,2,3,null);
```

***

#### concat\_ws()

`concat_ws(separator,data1,data2,data3,datan...)` 根据指定的分隔符(`separator`)拼接字符串，存在`null`则拼接空白。

```plsql
# 返回 1,2,3,4
select concat_ws(',',1,2,3,4);
# 返回 1-2-3-4
select concat_ws('-',1,2,3,4);
# 返回 1-2-3
select concat_ws('-',1,2,3,null);
```

***

#### group\_concat()

`group_concat()` 根据某个字段分组然后汇总数据。

```plsql
create table test (
    id INT,
    name VARCHAR(50)
);

insert into test (id, name) values
(1, '刘备'),
(2, '关羽'),
(3, '张飞'),
(4, '曹操'),
(5, '孙权');

-- 刘备,关羽,张飞,曹操,孙权
select group_concat(name) as names_summary from test;

-- 孙权,曹操,张飞,关羽,刘备
select group_concat(name order by id desc) as names_summary_desc from test;
```

***

#### date\_format()

`date_format(dateStr,pattern)`格式化时间函数。`dataStr`为要格式化的时间，`pattern`为格式。

```plsql
# 返回 2025-03-28
select date_format('2025-3-28 15:33:04',   '%Y-%m-%d');
```

可以使用的格式有：

| 格式 | 描述 |
| --- | --- |
| %a | 缩写星期名 |
| %b | 缩写月名 |
| %c | 月，数值 |
| %D | 带有英文前缀的月中的天 |
| %d | 月的天，数值(00-31) |
| %e | 月的天，数值(0-31) |
| %f | 微秒 |
| %H | 小时 (00-23) |
| %h | 小时 (01-12) |
| %I | 小时 (01-12) |
| %i | 分钟，数值(00-59) |
| %j | 年的天 (001-366) |
| %k | 小时 (0-23) |
| %l | 小时 (1-12) |
| %M | 月名 |
| %m | 月，数值(00-12) |
| %p | AM 或 PM |
| %r | 时间，12-小时（hh:mm:ss AM 或 PM） |
| %S | 秒(00-59) |
| %s | 秒(00-59) |
| %T | 时间, 24-小时 (hh:mm:ss) |
| %U | 周 (00-53) 星期日是一周的第一天 |
| %u | 周 (00-53) 星期一是一周的第一天 |
| %V | 周 (01-53) 星期日是一周的第一天，与 %X 使用 |
| %v | 周 (01-53) 星期一是一周的第一天，与 %x 使用 |
| %W | 星期名 |
| %w | 周的天 （0=星期日, 6=星期六） |
| %X | 年，其中的星期日是周的第一天，4 位，与 %V 使用 |
| %x | 年，其中的星期一是周的第一天，4 位，与 %v 使用 |
| %Y | 年，4 位 |
| %y | 年，2 位 |

***

#### length()

`length()`返回字符串的长度。

```plsql
# 返回3
select length('123');
```

***

#### replace()

`replace()`替换指定字符串中的指定字符串为指定字符串

```plsql
# 返回 aaaaa-abcd
select replace('1234abcd','1234','aaaaa-');
```

***

#### find\_in\_set()

`find_in_set()` 查找指定的字符串在不在字符串列表中

```plsql
-- 返回3，因为找到了
select find_in_set('百里','徐庶,诸葛,百里');

-- 返回0 没找到
select find_in_set('百里1','徐庶,诸葛,百里');
```

***

#### locate()

`locate()` 返回字符串首次出现的位置，下标从1开始

```plsql
-- 返回2
select locate('2','123');

-- 返回1
select locate('1','123');
```

***

## 日期函数

#### curdate()

`curdate()` 返回今天的日期

```plsql
-- 返回 2025-03-28
select curdate();
```

#### curtime()

`curtime()` 返回今天的时间

```plsql
-- 返回 15:42:42
select curtime();
```

#### now()

`now()` 返回日期和时间

```plsql
-- 返回 2025-03-28 15:43:09
select now();
```

***

## 逻辑函数

#### if()

`if()` 判断表达式是否成立，格式`if(表达式,成立返回,不成立返回)`，注意成立和不成立的返回必须是一个类型的，要是字符串必须都是字符串，不能一个是字符串一个是数字。

```plsql
-- 返回 成立
select if(1=1,'成立','不成立');

-- 返回 成立
select if(1 is not null,'成立','不成立');

-- 返回 不成立
select if(1=2,'成立','不成立');

-- 返回 成立
select if(1 is not null and 1=1,'成立','不成立');

-- 返回 不成立
select if(1 is not null and 1=2,'成立','不成立');
```

***

#### case

`case` 多表达式判断，返回最先成立表达式的结果，格式`CASE WHEN 表达式1 THEN 表达式1成立的结果 WHEN 表达式2 THEN 表达式2成立的结果 ELSE 都不成立的结果 END `

```plsql
-- 返回 1=1
select case when 1=1 then '1=1' when 2=2 then '2=2' else '都不成立' end

-- 返回 2=2
select case when 1=2 then '1=1' when 2=2 then '2=2' else '都不成立' end

-- 返回 都不成立
select case when 1=2 then '1=1' when 2=3 then '2=2' else '都不成立' end
```

***

#### ifnull()

`ifnull()` 如果传入的值为null，就返回指定的值，不为null，就返回传入的值

```plsql
-- 返回 1
select ifnull(1,'111');

-- 返回 111
select ifnull(null,'111');
```

***


# 业务系统每天增加五万条以上数据预计运维三年怎么优化

### 前言
随着互联网业务的快速发展，数据量呈现爆发式增长。

对于发布系统来说，每天新增的数据超过五万条，三年下来累积的数据总量将达到数亿级别，如果缺乏恰当的设计与优化措施，数据库可能会因为查询速度慢、写入操作卡顿或是维护工作变得过于复杂而成为限制业务发展的瓶颈。
面对这种快速增长且并发访问量高的应用场景，如何有效地对MySQL数据库进行优化以确保其能够持续稳定地运行呢？

本文将为您介绍七个实用的优化技巧，帮助您的系统更加轻松地应对大规模数据处理的需求。希望这些策略能为您的项目带来实质性的帮助！

---

### 设计良好的数据库结构，允许部分数据冗余，尽量避免 JOIN 查询，提高效率
高并发、海量数据场景下，表结构设计一定要面向查询高效和维护简单。

可以适当允许部分数据冗余，把常用信息直接冗余到主表，避免复杂的多表 JOIN 导致性能下降。

比如发布信息表可冗余部分用户信息字段（如用户名、昵称），加快单表查询速度。必要时用数据同步或触发器保障数据一致性。

### 选择合适的表字段数据类型和存储引擎，适当的添加索引
字段类型越精确越节省空间和提升性能，比如：

+ 整数选 int
+ 避免用 bigint
+ 定长字符串用 char
+ 长文本用 text

存储引擎推荐采用 InnoDB，它支持事务和高并发环境。

索引建议只加在高频查询条件、排序、分组字段，防止冗余索引拖慢写入效率。复合索引可结合实际业务查询需求设计。

### MySQL 库主从读写分离
部署主从架构，将写操作集中到主库，读操作分散到从库，可极大减轻单台服务器压力。

这样写入性能和读取扩展性都能得到保证。可以利用 MySQL 自身复制机制、读写分离中间件等进行实现。

但需注意读写延迟和一致性影响，部分业务流程仍需走主库。

![1747142178452-cd8e6a2e-fa71-4bc2-8fa0-2808f85f14ec.png](images/1747142178452-cd8e6a2e-fa71-4bc2-8fa0-2808f85f14ec.png)

### 找规律分表，减少单表中的数据量提高查询速度
随着数据的持续激增，要避免单表数据膨胀。

可以按时间（比如每月/每季度/每年分表）、业务类型、用户分段等规律拆表。

这样可以减小每个表的数据量，提高查询和维护效率，也便于历史数据归档和备份。

分表后要统一封装路由逻辑，简化应用维护。

![1747142203204-90591891-b46a-41cf-a782-f8b1d1b67807.png](images/1747142203204-90591891-b46a-41cf-a782-f8b1d1b67807.png)

### 添加缓存机制，比如 memcached，apc 等
对热点数据（如热门列表、详情页等）可使用 Redis、Memcached 等内存缓存中间件，大幅减少数据库访问压力，提高数据响应速度。

APC 等也能作为 PHP 的 Opcode 缓存提升应用端性能。

合理设置缓存失效机制，保持数据实时性和一致性，是保证高并发访问下服务稳定的关键。

![1747142221647-3b3f009b-2804-4eab-83aa-65e02595fd25.png](images/1747142221647-3b3f009b-2804-4eab-83aa-65e02595fd25.png)

### 不经常改动的页面，生成静态页面
对于不频繁变化的内容页，如公告、内容详情、帮助文档等，可在发布后由系统定时或按需生成静态HTML，前端直接从Web服务器加载，无需每次访问都请求数据库。

静态页面极大缓解高并发场景下数据库和应用服务器的压力，提升页面响应速度和系统稳定性。

### 书写高效率的 SQL。比如 SELECT * FROM TABLE 改为 SELECT field_1, field_2, field_3 FROM TABLE
查询时应只获取业务所需字段，避免 SELECT * 带来不必要的数据传输和解析压力。

精确筛选条件，利用好索引；复杂查询可通过分步或者先放缓存里处理，避免全表扫描。配合 EXPLAIN 工具分析慢查询，不断优化 SQL 逻辑，让每次访问都物有所值。

---

### 总结
面对海量业务数据和长周期高并发运维，只要在表结构、字段、索引、主从分离、分表、缓存、静态化、SQL优化等多个维度系统思考和分步实施，MySQL 完全可以长期稳定支撑业务发展。

配合持续的监控与备份，一套强壮的数据服务体系才能真正落地，助力业务稳步成长。


# MySQL索引设计有哪些原则

在设计数据库索引时，遵循一些关键原则和最佳实践可以显著提升查询性能，同时减少系统资源的浪费。以下是设计索引时应考虑的重要原则：

### 1. 选择合适的列

* **频繁作为查询条件的列**：
  * 对经常出现在 WHERE 子句中的列创建索引。
* **参与排序的列**：
  * 对 ORDER BY、GROUP BY 或者 DISTINCT 操作中出现的列建立索引。
* **作为连接条件的列**：
  * 在多表连接的情况下，对作为连接条件的列创建索引。

### 2. 优化多列索引

* **复合索引**：
  * 对多个列组合查询的情况，考虑使用复合索引而非单个列索引，以减少表扫描次数。
* **最左前缀匹配**：
  * 确保复合索引的列顺序遵循最左前缀原则，即将使用最频繁的列放在最前面。

### 3. 控制索引的数量和类型

* **避免过多索引**：
  * 索引有利于查询，但每个新增索引会影响插入、更新、删除的性能。应在查询效率与维护成本之间取得平衡。
* **适用索引类型**：
  * 选择合适类型的索引，例如 B-tree 索引用于大多数情况，Full-text 索引用于全文搜索，Hash 索引用于等值查询（如内存表）。

### 4. 考虑数据分布和选择性

* **高选择性的列**：
  * 高基数、高选择性（具有许多不同值）的列索引往往能提高查询效率。
* **均匀分布的数据**：
  * 索引在数据分布均匀时效果最佳，避免对只有少数不同值的列（低基数）设置索引。

### 5. 避免冗余和重复索引

* **合并索引**：
  * 考虑合并类似用途的索引，减少冗余。
* **定期清理**：
  * 定期审查和清理不再使用或效果不佳的索引。

### 6. 使用覆盖索引

* **覆蓋索引**：
  * 当索引包含查询所需的所有列时，称为覆盖索引，能有效减少读取数据页的次数。尽量使查询使用覆盖索引。

### 7. 关注变更和维护

* **更新和插入的影响**：
  * 在设计索引时，必须注意对写操作（如插入、更新）的影响，确保系统的峰值写入性能。
* **统计信息的刷新**：
  * 确保及时更新统计信息，特别是在大量数据变动后，帮助查询优化器做出更优的决策。

### 8. 考虑分区和分片

* **大数据集的优化**：
  * 对于非常大的数据集，考虑使用数据库的分区或分片功能，结合索引设计以提高性能。

### 小结

随着数据规模和访问模式的变化，索引设计并非一成不变，应根据应用的实际需求、查询特性和性能监控结果，持续调整和优化索引策略。通过合理设计算索引，可以在不显著增加存储空间和维护成本的前提下，最大化提升数据库的响应速度和整体性能。


# InnoDB存储引擎三大特性

### Buffer Pool

* **原理**：Buffer Pool是InnoDB存储引擎用于缓存数据页和索引页的内存区域。它提高了数据库的读写性能，因为数据页和索引页在内存中读写比在磁盘上快得多。当需要访问数据时，InnoDB会先在Buffer Pool中查找，如果找不到，才会从磁盘读取。
* **工作方式**：Buffer Pool采用LRU（最近最少使用）算法来管理内存中的页。当Buffer Pool满时，最近最少使用的页会被淘汰，以便为新的页腾出空间。
* **配置参数**：
  * `innodb_buffer_pool_size`：设置Buffer Pool的大小，通常建议设置为物理内存的70%左右，以平衡数据库和其他系统的需求。
  * `innodb_buffer_pool_instances`：设置Buffer Pool的实例数量，用于减少锁竞争，提高并发性能。
* **应用场景**：适用于需要频繁读写数据的场景，如事务处理、查询优化等。

### Adaptive Hash Index

* **原理**：Adaptive Hash Index（AHI）是InnoDB存储引擎的一种内存结构，用于加速等值查询。InnoDB会自动监控索引的使用情况，如果发现某个索引频繁被访问，就会在内存中为该索引创建哈希索引，以减少查询时间。
* **工作方式**：AHI是一个哈希表结构，键是索引键值，值是该键值对应的页面位置。需二级索 频繁查询（固定时间内连续多次等值查询==号,>=等不行，orderby 无效）成为热点数据会建立hash index 带来速度的提升。可通过 %hash\_index% 查询
* **配置参数**：
  * `innodb_adaptive_hash_index`：控制是否启用AHI，默认启用。在高并发场景下，如果CPU资源紧张，可以考虑禁用。
  * `innodb_adaptive_hash_index_partitions`：设置AHI的分区数量，增加分区数量可以减少哈希冲突，但也会增加内存消耗。
* **应用场景**：适用于频繁的等值查询，如主键查询或唯一索引查询。在高并发读取的场景下，AHI可以减少磁盘I/O，提高查询响应速度。
* **限制**：
  * 只能用于等值比较，如`=`、``、`IN`等。
  * 无法用于排序。
  * 存在哈希冲突的可能性，可能导致性能下降。
  * 维护AHI需要额外的内存和CPU资源。

### Double Write

* **原理**：Double Write是InnoDB存储引擎用于提高数据完整性和可靠性的机制。它通过在将数据页写入数据文件之前，先将它们写入一个称为Double Write Buffer的连续存储区域，确保数据的一致性。如果在写入过程中发生崩溃，InnoDB可以从Double Write Buffer中恢复数据。
* **工作方式**：数据页首先被写入Double Write Buffer，然后通过两次写入操作（顺序写）将数据页写入数据文件的适当位置。这种方式可以减少I/O开销，因为数据是连续写入的。
* **配置参数**：
  * `innodb_doublewrite`：控制是否启用Double Write功能。默认启用，但在某些性能测试场景下可以禁用。
  * `innodb_doublewrite_dir`：设置Double Write文件的存储目录。
  * `innodb_doublewrite_files`：定义Double Write文件的数量。
  * `innodb_doublewrite_pages`：控制每个线程的最大Double Write页数。
* **应用场景**：适用于需要高可靠性和数据一致性的场景，如生产环境中的数据库系统。

以上是关于InnoDB存储引擎的三大特性：Buffer Pool、Adaptive Hash Index和Double Write的详细解释。这些特性在不同的场景下各有优势，可以根据具体需求进行配置和优化。

**图解：**

API设计图：

![1743593433908-6b651c28-062d-4ab9-b651-ba5ca4c8ff75.png](images/1743593433908-6b651c28-062d-4ab9-b651-ba5ca4c8ff75.png)

BufferPool设计

![1743593485682-1ddf9fcf-d435-4f01-8c77-948714877b54.png](images/1743593485682-1ddf9fcf-d435-4f01-8c77-948714877b54.png)

淘汰策略

![1743593386366-95e6504e-7a06-48f6-8cd0-2b93f3ec796f.png](images/1743593386366-95e6504e-7a06-48f6-8cd0-2b93f3ec796f.png)

doublewrite双写机制

![1743593355545-aebcf763-12c0-4935-8b76-e8bde8e8ddbc.png](images/1743593355545-aebcf763-12c0-4935-8b76-e8bde8e8ddbc.png)


# truncate、delete、drop的区别

TRUNCATE、DELETE和DROP都是SQL中的数据操作语句，用于删除数据或表结构，但它们在功能、性能和使用场景上有显著的区别：

### TRUNCATE

* **用途**：
  * 用于删除表中的所有数据，但保留表结构。
* **性能**：
  * 比DELETE快，因为它通常不记录单独的行删除操作，也不触发行级触发器。
* **事务处理**：
  * 在大多数数据库系统中，TRUNCATE被视为一个DDL操作而非DML操作。因此，它可能不能被回滚（但这依赖于数据库的实现，某些系统可能支持事务性TRUNCATE）。
* **自动递增**：
  * 自动递增的值会被重置。
* **触发器**：
  * 不会激活行级触发器。
* **语法**：

```sql
TRUNCATE TABLE table_name;
```

### DELETE

* **用途**：
  * 用于删除表中的指定行或所有数据，但保留表结构和约束。
* **性能**：
  * 比TRUNCATE慢，特别是在处理大表时，因为它逐行记录删除操作，并能激活触发器。
* **事务处理**：
  * 是一个DML操作，支持事务处理，可以在事务中回滚。
* **自动递增**：
  * 自动递增的值不会被重置。
* **触发器**：
  * 激活行级触发器。
* **语法**：

```sql
DELETE FROM table_name WHERE condition;
```

若要删除所有行但不重置自动递增：

```sql
DELETE FROM table_name;
```

### DROP

* **用途**：
  * 用于删除整个表、数据库或其他数据库对象，包括其结构和数据。
* **性能**：
  * 通常是立即操作，不可恢复。
* **事务处理**：
  * 是一个DDL操作，不可回滚（具体依赖数据库系统）。
* **删除影响**：
  * 删除表时会删除所有数据、索引、约束和权限信息。
* **语法**：

```sql
DROP TABLE table_name;
```

### 总结

* **TRUNCATE**：快速清空表，但保留结构。适用于需要清空但不删除表的场景。
* **DELETE**：逐行删除数据，可以选择性删除某些记录。适用于只想删除部分数据的场合，且支持事务。
* **DROP**：删除整个表定义及其所有数据。适用于不再需要表结构或其数据的情况。

选择哪个语句取决于你的需求是否涉及数据完整性、安全性、性能优化或是事务处理

[bilibili](https://player.bilibili.com/player.html?bvid=BV1kFpue5Ehj\&p=10\&page=10\&autoplay=0)


# 哪些场景可以利用索引覆盖来优化SQL

在SQL查询优化中，索引覆盖（Covering Index）是一种通过索引直接提供查询所需数据而无需回表的技术，可显著提升性能。以下是适用场景及具体说明：

### 1. **全表COUNT查询优化**

当统计某非主键列的数量时，若为该列建立索引，数据库可直接扫描索引（而非数据行）完成统计。例如：

```plsql
-- 原表user无索引时无法覆盖
SELECT COUNT(name) FROM user;
-- 添加索引后，直接通过索引统计
ALTER TABLE user ADD KEY(name);
```

此时索引name包含所有需要统计的数据，避免全表扫描。

***

### 2. **避免回表查询**

若查询列未被索引覆盖，需回表查询数据行。通过升级为联合索引可解决：

```plsql
-- 原单列索引name需回表查sex
SELECT id, name, sex FROM user WHERE name = 'shenjian';
-- 升级为联合索引(name, sex)后，直接通过索引返回结果
CREATE INDEX idx_name_sex ON user(name, sex);
```

联合索引包含所有查询列，无需访问主键索引。

***

### 3. **分页查询优化**

分页查询（如LIMIT）若涉及排序和大量数据扫描，可通过覆盖索引减少回表。例如：

```plsql
-- 原索引name需回表获取sex
SELECT id, name, sex FROM user ORDER BY name LIMIT 500, 100;
-- 联合索引(name, sex)直接提供排序和返回列
CREATE INDEX idx_name_sex ON user(name, sex);
```

索引覆盖避免全表扫描和额外排序操作。

***

### 4. **无WHERE条件的查询**

即使无过滤条件，若查询列被索引覆盖，仍可避免全表扫描：

```plsql
-- 直接通过索引返回name和age
SELECT name, age FROM user;
-- 创建联合索引(name, age)实现覆盖
CREATE INDEX idx_name_age ON user(name, age);
```

适用于需要频繁读取特定列的报表类查询。

***

### 5. **WHERE条件区分度低的场景**

当WHERE条件区分度低（如性别字段）时，联合索引仍可通过覆盖减少数据访问：

```plsql
-- 性别区分度低，但联合索引(sex, age)覆盖查询
SELECT age FROM user WHERE sex = 'male';
```

即使需扫描较多索引条目，仍比回表访问数据行高效。

***

### 6. **仅查询主键的场景**

辅助索引的叶子节点存储主键值，因此仅查询主键时可天然覆盖：

```plsql
-- 辅助索引name的叶子节点含主键id
SELECT id FROM user WHERE name = 'shenjian';
```

无需回表，直接通过辅助索引返回结果。

***

### 7. **JOIN和ORDER BY优化**

若JOIN的关联字段或ORDER BY的排序列被索引覆盖，可优化连接和排序效率：

```plsql
-- 联合索引(t.emp_no, t.title)覆盖JOIN和SELECT列
SELECT t.emp_no, t.title FROM employees e
LEFT JOIN titles t ON e.emp_no = t.emp_no;
```

覆盖索引减少表访问和排序开销。

***

### 注意事项

* **索引类型限制**：仅B-Tree索引支持覆盖，Hash/全文索引不适用。
* **避免SELECT**\*：明确列出所需列以增加覆盖可能性，减少索引体积。
* **维护成本**：覆盖索引可能增加写入开销，需权衡读写比例。

通过合理设计索引覆盖上述场景，可显著减少I/O和CPU消耗，是SQL性能优化的核心手段之一。


# 对索引的了解？哪些字段适合加索引，哪些不适合

索引是数据库中用于加快数据查询的重要结构，类似于书的目录，可以让数据库迅速定位到所需的数据，而不必每次都全表扫描。

**一、常见索引类型**

+ **B树索引**：大多数关系型数据库的默认索引类型，支持范围查询、模糊查询等。
+ **哈希索引**：适合等值查询（=）；无法用于范围查询。
+ **全文索引**：针对大文本搜索，常用于文章、描述类字段。
+ **复合索引**：对多个字段联合建立的索引，优化多条件查询。

**二、适合加索引的字段**

1. **高基数（唯一性强）字段**
如用户ID、订单号、邮箱、手机号等。这类字段区分度高，能大幅提升查询效率。
_例：订单表的订单ID、用户表的手机号。_
2. **经常作为查询条件（WHERE、JOIN、ORDER BY、GROUP BY）的字段**
如登录时经常查询的邮箱、用户ID；报表经常分组的日期字段等。
_例：通过用户ID或邮箱登录时，常用作查询条件。_
3. **外键字段和经常用于表连接的字段**
能加快多表连接操作。
_例：订单表中的用户ID是用户表的外键，建议加索引。_
4. **经常用于排序、分组的字段**
能加快ORDER BY和GROUP BY的查询速度。
_例：订单表的创建时间用于最近订单排序，适合加索引。_

**三、不适合加索引的字段**

1. **低基数字段**
如性别、状态（如0/1）、布尔值。此类字段区分度低，加索引收益低，占空间反而影响写入性能。
_例：性别字段只有男、女两种，数据分布高度集中。_
2. **频繁更新的字段**
索引要随数据写入/更新同步维护，过于频繁的变动会拖慢整体性能。
_例：如用户最后一次登录时间/最近修改时间等频繁变更字段，一般不建议加索引。_
3. **超长文本、BLOB/CLOB类型的字段**
例如评论、备注、图片、附件等字段，索引只针对前缀、内容多变且占用空间大，通常用全文索引或不加索引。
4. **小表或记录量很小的表**
数据量小，直接全表扫描效率更高，加索引反而浪费资源。

**四、索引设计最佳实践**

+ **合理设计复合索引**：根据查询常用的多个字段创建联合索引，避免“失效”。
+ **避免过多索引**：每一个索引都会影响写入和更新性能。只为关键查询和连接加索引。
+ **覆盖索引优先**：查询可以只靠索引而无需回表，进一步提升效率。
+ **定期检查和优化**：随着业务发展、查询变化，需要定期清理冗余索引。
+ **注意索引顺序**：复合索引时，字段顺序建议放最常用、区分度高的字段在前。

**六、总结**
加索引的目的是提升查询效率，但不是越多越好。应该根据数据分布、查询特点和业务需求有选择性地加索引。合理的索引能极大提升数据库性能，但滥用索引则会降低写入效率并增加维护成本。


# MySQL只操作同一条记录也会死锁吗

在MySQL中，即使多个事务仅对同一条记录进行操作，也可能发生死锁。这通常与InnoDB存储引擎的锁管理机制有关。以下是一些触发这种情况的场景：

### 可能的死锁原因

1. **索引导致的锁竞争**：
   * 如果事务在WHERE子句中使用不同的索引来查找相同的行，InnoDB可能会导致多个事务以不同顺序锁住这些索引，从而产生死锁。
2. **自增锁（auto-increment lock）**：
   * 在使用自增列时，不同事务可能在等待获取表级锁来增加自增值，某些情况下也会出现死锁。
3. **外键约束**：
   * 外键检查过程中可能会涉及多个表，多个事务可能会因为不同的锁顺序而陷入死锁。

### 示例

假设有一个表accounts，事务A和事务B都对记录ID为1的行进行更新操作导致产生死锁。

```sql
CREATE TABLE accounts (
  account_id INT PRIMARY KEY,
  balance DECIMAL(10, 2)
);

-- 初始数据
INSERT INTO accounts (account_id, balance) VALUES (1, 100.00);
```

**事务A**:

```sql
START TRANSACTION;
UPDATE accounts SET balance = balance - 10 WHERE account_id = 1;
-- ... 其他处理，此时不提交事务
```

**事务B**:

```sql
START TRANSACTION;
UPDATE accounts SET balance = balance + 10 WHERE account_id = 1;
-- ... 其他处理，此时不提交事务
```

如果事务A和事务B在不提交事务的情况下，都在等待对方持有的锁释放，就会发生死锁。

### 解决方法

1. **合适的索引和查询计划**：
   * 确保查询使用最优的索引，以减少锁的粒度。
2. **减少锁定时间**：
   * 尽量缩短事务的生命周期，避免在事务内进行过多的运算或等待。
3. **合理规划事务逻辑**：
   * 统一事务的锁定顺序，避免因为不同的顺序引起的锁等待。
4. **检测和重试**：
   * 配置合适的重试机制，当捕获死锁异常时重试事务操作。

### Java代码示例

当检测到死锁时，可以使用重试机制来解决问题，如以下Java代码示例：

```java
import java.sql.*;
import java.util.concurrent.TimeUnit;

public class DeadlockRetryExample {

    private static final String URL = "jdbc:mysql://localhost:3306/your_database";
    private static final String USER = "your_username";
    private static final String PASSWORD = "your_password";
    private static final int MAX_RETRIES = 3;
    private static final int RETRY_DELAY = 2;

    public void updateBalanceWithRetry(int accountId, double balanceChange) throws SQLException {
        String sql = "UPDATE accounts SET balance = balance + ? WHERE account_id = ?";
        int attempts = 0;
        while (attempts = MAX_RETRIES) {
                            throw e;
                        }
                        TimeUnit.SECONDS.sleep(RETRY_DELAY);
                    } else {
                        throw e;
                    }
                }
            }
        }
    }

    private boolean isDeadlockException(SQLException e) {
        return e.getErrorCode() == 1213; // MySQL死锁的错误代码为1213
    }
}
```

通过理解MySQL的锁机制和适当规划应用程序事务，可以有效地减少因操作同一记录导致的死锁。


# 慢SQL你是怎么优化的

兄弟们，面试问“慢 SQL 优化”，如果你只回答“加索引”，那你大概率还在 P5/P6 徘徊。 真正的架构师，看的是**全链路**，思考的是**成本与收益**。

今天 Fox 老师教大家一套“海陆空立体化”**的优化打法，尤其是要避开那些**过时的技术陷阱。

***

## ⚔️ 第一维度：全链路监控（发现敌情）

别等用户投诉了才去查。

1. **慢查询日志 (Slow Query Log)**：这是基建。生产环境开启，阈值设为 1s，结合 **pt-query-digest** 工具每天出分析报告。
2. **实时监控 (Real-time)**：利用 Prometheus + Grafana 或 PMM (Percona Monitoring and Management)，监控 **QPS 抖动**、**锁等待** 和 **IO 飙升**。

***

## ⚙️ 第二维度：精准诊断（分析工具的迭代）

![1768458711707-62ac3ea3-79ce-4958-83ab-bac85e3513bd.png](images/1768458711707-62ac3ea3-79ce-4958-83ab-bac85e3513bd.png)

这里有个**关键区分点**，能体现你的技术深度：

### 1. EXPLAIN（基础必修）

* **type**：目标是 `ref` 或 `range`。看到 `index`（全索引扫）或 `all`（全表扫）要警惕。
* **Extra**：
  * `Using index`：完美（索引覆盖）。
  * `Using filesort`：**注意！** 只有当 `sort_buffer` 装不下，需要磁盘排序时才是大忌。如果内存够用，其实还好。

![1768458548620-33fc83c4-e67c-444c-b7c3-531fce763cbc.png](images/1768458548620-33fc83c4-e67c-444c-b7c3-531fce763cbc.png)

### 2. 弃用 `SHOW PROFILE`，拥抱 `Performance Schema`

**（高分点）**

“很多老教材教大家用 `SHOW PROFILE` 查看 CPU/IO 消耗。但这个命令早被废弃了。 我们团队现在主要用 **Performance Schema** 或 **sys schema**。 比如查询 `sys.statement_analysis` 视图，能看到全实例最耗 IO 的 SQL 是哪条，比 Profile 强大得多。”

![1768458562667-a2a48978-c9d9-4795-9909-d309df995863.png](images/1768458562667-a2a48978-c9d9-4795-9909-d309df995863.png)

### 3. Optimizer Trace（绝杀）

当 `EXPLAIN` 骗了你，明明有索引却不走时，开启 Trace 查看优化器的**代价计算过程 (Cost Model)**，看看是不是因为回表成本太高导致优化器放弃了索引。

***

## 🥊 第三维度：实战避坑（MySQL 8.0 新特性）

这一段抛出来，直接降维打击：

### 1. 索引失效的“新常识”

* **老生常谈**：函数计算、隐式转换、模糊查询左匹配，这些都会导致失效。
* **MySQL 8.0 颠覆点（Index Skip Scan）**：
  * 以前说：联合索引 `(a,b,c)`，查 `WHERE b=1` 必死。
  * **现在说**：在 MySQL 8.0+，如果字段 `a` 的区分度很低（如状态枚举），优化器会触发 **索引跳跃扫描**，依然能利用上索引！*（加上这句话，面试官就知道你技术在持续更新）*

![1768458578230-0c1702a8-e251-4554-8b09-66b17df82ee4.png](images/1768458578230-0c1702a8-e251-4554-8b09-66b17df82ee4.png)

### 2. 深分页的“特效药”

* **错误示范**：`LIMIT 1000000, 10`。

![1768458621660-f8bf8f5f-6ece-46d1-91d6-3a6fab24baf2.png](images/1768458621660-f8bf8f5f-6ece-46d1-91d6-3a6fab24baf2.png)

**条件解法**：

```
- `**id > N**`** 法**：仅适用于 **ID 连续且按 ID 排序** 的场景。如果按 `create_time` 排序，这招没用。
- **延迟关联 (Deferred Join)**：万能解法。
```

```sql
-- 先在索引树上把 ID 找出来（覆盖索引，不回表）
SELECT * FROM table t1
JOIN (SELECT id FROM table ORDER BY time LIMIT 1M, 10) t2 ON t1.id = t2.id;
```

***

## 💣 第四维度：架构兜底（空间换时间）

SQL 优化总有极限（物理极限）。当单表数据量突破 2000 万，或者 SQL 极其复杂时，**不要硬刚 MySQL**。

1. **转移阵地**：
   * **复杂搜索/全文检索**：上 **Elasticsearch**。MySQL 的 B+ 树不是为多维筛选设计的，ES 的倒排索引才是。
   * **高频热点**：上 **Redis**。
2. **冷热分离**：
   * 把 3 个月前的数据归档到历史表（History Table）或数仓（Hive/ClickHouse），保证核心业务表轻装上阵。
3. **读写分离**：
   * 报表类的慢 SQL 强制走从库，绝不让它拖垮主库的写性能。

![1768458646223-92e6de87-ff7a-4d1a-8564-1dd3dea7ba96.png](images/1768458646223-92e6de87-ff7a-4d1a-8564-1dd3dea7ba96.png)

***

## 🎓 满分总结（背诵版）

“慢 SQL 优化是一个**闭环**过程：

1. **发现**：靠监控和日志。
2. **诊断**：`EXPLAIN` 看执行计划，8.0 下用 `Performance Schema` 分析资源消耗，必要时用 `Optimizer Trace` 查源码级原因。
3. **治理**：
   * 战术上：利用覆盖索引、延迟关联优化深分页，并注意 8.0 的索引跳跃扫描新特性。
   * 战略上：引入 ES、Redis 或冷热分离，解决 B+ 树的物理局限性。

核心思想是：**技术服务于业务，不要为了优化而优化，要看 ROI（投入产出比）。**”

***

**Fox 老师寄语：** 兄弟们，细节决定成败，新特性决定高度。加上 **MySQL 8.0** 和 **Performance Schema** 这些点，你的回答就不是背八股文，而是真正的技术沉淀！ **点赞、收藏**，下次面试前拿出来复习一遍，绝对稳！


# 100W数据去重，该用distinct还是groupby，说说理由？

对于100万级别的数据去重，选择 `DISTINCT` 还是 `GROUP BY`，在**功能上（仅去重，不进行聚合运算）两者是等效的**，大多数现代数据库的查询优化器会将它们生成相似甚至相同的执行计划。然而，从**可读性和表达意图**的角度来看，`DISTINCT` 通常更胜一筹。以下是从不同的角度出发进行分析解答：

### 功能等效性 (仅去重)

* `SELECT DISTINCT column1, column2, ... FROM orders;`
* `SELECT column1, column2, ... FROM orders GROUP BY column1, column2, ...;`

这两条SQL语句在只获取唯一组合的列值时，返回的结果是完全相同的。

### 表达意图和可读性

* **DISTINCT**: 这个关键字的语义非常直接——“**返回唯一的行**”。当你的主要目的是去重时，使用 `DISTINCT` 能更清晰地表达你的意图，代码也更易于理解。
* **GROUP BY**: 这个子句的主要目的是**将数据分成多个组，并对每个组进行聚合操作**（如 `COUNT()`, `SUM()`, `AVG()` 等）。虽然在不使用聚合函数时，`GROUP BY` 可以达到去重的效果，但这并\*\*非其主要设计目的\*\*。如果读者看到 `GROUP BY`，通常会期望看到聚合函数。

**结论1：为了代码清晰和准确表达去重意图，优先推荐使用 ****DISTINCT****。**

### 性能考量 (100万数据量级)

在100万数据量级下，性能是关键。

* **查询优化器：** 现代数据库的查询优化器通常足够智能，能够识别出上述两种写法的等效性，并选择最优的执行计划。这意味着，在很多情况下，它们的实际性能表现可能几乎没有差异。
* **执行计划：** 无论是 `DISTINCT` 还是 `GROUP BY`，去重操作通常涉及以下一种或多种底层操作：
  * **排序 (Sorting):** 将所有数据按照去重列进行排序，然后遍历排序后的结果，只保留每组相同数据的第一条。如果数据量大到内存无法容纳，排序可能需要磁盘I/O（外部排序），这会比较慢。
  * **哈希 (Hashing):** 遍历数据，将列值组合计算哈希值并存入哈希表。如果哈希表中已存在相同的哈希值（并确认原始值相同），则丢弃当前行。哈希操作通常在内存中进行时效率较高。
* **索引的影响：**
  * **如果去重的列上有合适的索引**（特别是覆盖索引，即索引包含了所有需要去重的列），数据库可能可以直接利用索引的有序性或结构来高效地提取唯一值，避免全表扫描和大规模排序/哈希。在这种情况下，无论用 `DISTINCT` 还是 `GROUP BY`，性能都会很好，并且差异可能更小。
  * **如果没有合适的索引**，数据库将不得不进行全表扫描，然后进行排序或哈希。这时性能开销会比较大。

**结论2：对于性能，更关键的因素是是否有合适的索引支持去重操作，以及数据库优化器如何选择执行计划，而不是 ****DISTINCT**** 和 ****GROUP BY**** 关键字本身的区别。在没有索引的情况下，两者都可能较慢。**

### GROUP BY 的扩展性

如果你的需求不仅仅是去重，还需要基于这些唯一的组合进行聚合计算（例如，计算每个唯一组合出现的次数），那么 `GROUP BY` 是唯一的选择，并且更符合其设计意图。

* 例如，找出重复的行并统计重复次数：

```plsql
SELECT column1, column2, COUNT(*) as occurrences
FROM your_table
GROUP BY column1, column2
HAVING COUNT(*) > 1;
```

这种场景下 `DISTINCT` 无法直接实现。

### 总结与建议

对于100万数据去重（仅获取唯一行）：

1. **首选 ****DISTINCT****：** 因为它在语义上更清晰地表达了“去重”的意图。
2. **性能通常相似：** 大多数现代数据库优化器会将两者处理成相似的执行计划，性能差异不大。
3. **关注索引：** 确保你希望去重的列上有合适的索引。这是提升性能的关键，远比纠结用 `DISTINCT` 还是 `GROUP BY` 更重要。对于100万行数据，没有索引的去重操作将会非常慢。
4. \*\*实际测试：\*\***最重要的永远是实际测试。** 使用你目标数据库的 `EXPLAIN` (或等效工具，如 `EXPLAIN ANALYZE`) 来查看两条语句的执行计划。比较它们的成本、是否使用了索引、以及实际执行时间。不同数据库、不同版本、不同数据分布和表结构都可能导致细微的性能差异。

**简而言之：为了代码可读性，用 ****DISTINCT****，为了性能，确保有索引，并用 ****EXPLAIN**** 验证。**


# SQL用了函数一定会索引失效吗

在MySQL中，当查询语句中对索引列使用某些函数时，确实可能导致索引失效，迫使数据库执行全表扫描。这是因为函数应用于列值后，数据库无法直接利用索引中储存的排序信息。不过，这并不意味着所有情况都会导致索引失效，具体取决于使用的函数类型和场景。以下是详细说明：

### 常见会导致索引失效的情况：

1. **对索引列使用函数**：
   * 如果在 WHERE 子句中对索引列应用了函数转换，例如 LOWER(column_name)，会导致索引无法被使用。这是因为索引是基于列的原始值而构建的，函数改变了这些值。
   * 示例：

```sql
SELECT * FROM users WHERE LOWER(username) = 'john';
```

```
- 在这种情况下，可以考虑在应用层处理大小写不敏感的比较，或者在数据库中创建一个计算列（从MySQL 5.7开始支持持久生成列）、存储计算值并对其建立索引。
```

2\. **计算表达式**：
\- 使用计算表达式如 column + 1 可能导致MySQL放弃使用索引。
\- 示例：

```sql
SELECT * FROM orders WHERE price + 10 > 100;
```

### 不会导致索引失效的情况：

1. **函数在索引范围之外使用**：
   * 函数不在索引范围（即WHERE或ON条件）使用时，索引仍然有效。例如，在 SELECT 列表、ORDER BY、GROUP BY等地方使用函数通常不影响索引的使用。
   * 示例：

```sql
SELECT UPPER(username) FROM users WHERE username = 'john';  -- 索引用于WHERE子句
```

### 优化建议：

* **使用生成列**：如果定期需要函数值，可以考虑使用生成列来预计算值并索引它。

```sql
ALTER TABLE users ADD username_lower VARCHAR(255) GENERATED ALWAYS AS (LOWER(username)) STORED, ADD INDEX (username_lower);
```

* **在应用层处理**：在应用层而不是数据库中处理某些需要函数的计算或转换。
* **分析查询计划**：使用 EXPLAIN 语句分析和验证查询是否有效利用索引。

通过合理的索引设计与查询编写，尽量避免在索引列上直接使用会影响索引的函数，是提高查询性能的重要手段。

[bilibili](https://player.bilibili.com/player.html?bvid=BV1kFpue5Ehj\&p=7\&page=7\&autoplay=0)


# 为什么大厂不建议使用多表join

在大型互联网企业或者“超大规模”数据库环境中，不建议频繁使用多表 JOIN 的原因主要涉及性能、可维护性和架构设计等方面。以下是一些常见的考虑因素：

1. **性能问题**：
    - **计算复杂性**：多表 JOIN 通常需要进行复杂的计算，如哈希连接、合并连接，这会显著增加查询的计算开销，影响响应时间。
    - **资源消耗**：JOIN 操作特别是在多表参与时，会占用大量的内存和CPU资源，尤其是当涉及大表或需要对大量数据进行JOIN时。
    - **索引依赖**：JOIN 性能很大程度上依赖于索引的存在和选择，当索引不当或者没有索引时，查询性能会大幅下降。
2. **可扩展性**：
    - **水平扩展挑战**：在分布式数据库架构中，JOIN 操作可能需要跨多个节点获取数据（即“跨节点JOIN”），这往往会导致大量的数据传输，增加系统负担。
    - **难以分片**：复杂的 JOIN 查询在分片数据库中难以优化，因为涉及多个分片的数据可能位于不同的物理节点上，因此难以高效进行。
3. **维护与复杂度**：
    - **代码复杂性**：复杂的多表 JOIN 查询往往导致SQL语句难以理解和维护。维护这种复杂查询的成本较高。
    - **调试困难**：当数据错误或者查询性能不佳时，复杂的 JOIN 查询更难以调试和定位问题。
4. **架构设计**：
    - **领域模型割裂**：JOIN 通常需要深度了解不同表之间的关系，容易导致领域模型设计上的不一致。
    - **微服务架构限制**：在微服务架构中，数据通常是去中心化和跨服务的，JOIN 查询往往违反服务数据自治的原则。

### 替代策略
为了避免使用多表 JOIN，企业通常采取以下策略：

+ **反范式化**：适当的冗余存储以减少JOIN需求。
+ **数据冗余**：在不同表中冗余存储一些公共字段，以避免频繁的JOIN。
+ **分而治之**：将复杂查询拆分为多个简单查询，在应用层进行数据组合。
+ **预先计算**：通过ETL作业预先计算和存储结果。
+ **使用NoSQL数据库**：设计生产系统时采用文档数据库或键值存储一类的NoSQL数据库来轻松支持复杂数据需求。

这些方法有助于提高查询性能、减少延迟并增强系统的可扩展性。因此，大厂在设计数据库和编写查询时，往往会尽量避免频繁和复杂的多表 JOIN。

[bilibili](https://player.bilibili.com/player.html?bvid=BV1kFpue5Ehj&autoplay=0)


# where条件的顺序影响索引使用吗

在MySQL中，WHERE条件的顺序确实可能影响索引的使用，尤其是在使用复合索引（多列索引）的情况下。然而，这种影响主要取决于MySQL查询优化器的工作方式，而不是直接由WHERE子句中条件的书写顺序决定的。以下是一些关键点：

1. **查询优化器的作用**
   * MySQL的查询优化器通常会尝试重新排列WHERE条件以最优化索引的使用。
   * 在大多数情况下，优化器能够独立于条件书写顺序来选择最佳的执行计划。
2. **复合索引的左前缀匹配原则**
   * 对于复合索引，索引的使用遵循"最左前缀"原则。
   * 例如，对于索引(A, B, C)，查询条件可以使用A，或A和B，或A、B和C，但不能跳过A直接使用B或C。
3. **条件顺序与索引列顺序**
   * 虽然WHERE条件的顺序通常不会影响索引的使用，但将索引列的条件放在前面可能会使查询计划更易读和理解。
   * 例如：对于索引(A, B, C)，WHERE A = 1 AND B = 2 AND C = 3可能比WHERE C = 3 AND B = 2 AND A = 1更直观。
4. **范围条件的影响**
   * 在复合索引中，范围条件（如 >,  2 AND C = 3;
EXPLAIN SELECT * FROM table WHERE C = 3 AND B > 2 AND A = 1;
```

这两个查询可能会产生相同的执行计划，因为优化器会重新排列条件以最佳利用索引。

### 最佳实践

1. **索引设计**：根据查询模式设计合适的索引。
2. **使用EXPLAIN**：经常使用EXPLAIN来分析查询执行计划。
3. **优化器提示**：在必要时使用优化器提示来影响索引选择。
4. **条件顺序**：尽管不是决定性因素，但为了代码可读性，尽量让WHERE条件的顺序与索引列顺序一致。
5. **范围条件考虑**：在复合索引中，将范围条件放在等值条件之后。

总之，虽然WHERE条件的顺序在大多数情况下不会直接影响索引的使用，但了解这些原则有助于编写更高效和可维护的查询。始终通过EXPLAIN来验证实际的索引使用情况。


# 为什么不推荐使用外键

在许多数据库设计原则和项目中，尽管外键能够提供数据一致性和完整性约束，但在某些情况下，开发人员和数据库管理员可能会选择避免使用外键。以下是一些常见的原因：

1. **性能影响**
    - **插入和删除操作变慢**：外键约束要求数据库在插入和删除操作期间进行额外的完整性检查，以确保引用完整性。这可能导致插入和删除操作的性能下降。
    - **影响批量操作**：大批量插入或更新操作因为外键约束而变得更加耗时。
2. **灵活性受限**
    - **数据迁移和重构困难**：使用外键可能使数据库结构的变更（如拆分表、合并表、重构数据库）更加复杂，因为外键增加了表之间的依赖性。
3. **复杂的管理**
    - **事务复杂性**：外键可能会导致更复杂的事务管理，尤其是在涉及多个表的情况下，因为删除或更新父表中的记录会影响到子表的数据。
4. **分布式系统的局限**
    - **难以应用于分布式数据库**：在微服务架构或分布式数据库中，可能不便于使用外键，因为不同的服务或数据库实例可以在不同的节点上运行，带来一致性挑战。
5. **应用层管理**
    - **逻辑处理迁移到应用层**：许多团队选择在应用层通过业务逻辑来维护数据一致性，而不是依赖数据库中的外键约束。这可以在一定程度上增强跨数据库或平台的一致性管理。
6. **数据库锁定问题**
    - **锁定级别影响**：在某些数据库实现中，外键约束会增加锁定争用，特别是在高并发写操作中，这可能会对系统性能产生负面影响。

### 注意事项
虽然在某些情况下，不使用外键可能会带来灵活性和性能上的好处，但开发团队需要自行实现数据完整性检查，以确保数据库的一致性和正确性。否则，可能会引入数据不一致的问题，使数据库容易出现孤儿记录或数据不正确的风险。

### 何时使用外键
然而，在许多场合下，使用外键约束仍然被视为良好的数据库设计实践，特别是在以下情况下：

+ **明确的数据完整性需求**：当确保数据完整性至关重要时，外键约束可以提供可靠的保障。
+ **简单的数据模型**：在简单的数据模型中，外键对于维护基本的数据关系是有效的。
+ **开发效率优先**：对于小型项目或开发效率优先的项目，外键可以简化数据完整性管理。

综上所述，是否使用外键应根据具体项目的需求、性能要求和系统架构来制定策略。权衡利弊后做出明智的技术选择将有助于达到最佳的平衡。


# MySQL为什么默认使用RR隔离级别

MySQL 默认使用 Repeatable Read (RR) 隔离级别主要是为了在性能与一致性之间取得一个较好的平衡。让我们详细探讨一下使用 RR 隔离级别的理由：

1. **一致性保证**：
    - RR 提供了较高的一致性保障。它保证在同一个事务中, 相同的 SELECT 查询结果是一致的，因为它通过使用快照确保查询结果的一致性。
    - 在 MySQL 的 InnoDB 存储引擎中，RR 隔离级别还能防止幻读，这得益于使用间隙锁机制。这比 REPEATABLE READ 传统定义的行为有所提升。
2. **防止“幻读”**：
    - 幻读是指当在一个事务中读取多行记录时，另一事务可能在这期间插入新的记录，从而导致前后两次读取结果不一致。在 MySQL 的 RR 隔离级别下，会使用间隙锁（next-key locking）来防止这种情况。
3. **性能权衡**：
    - 虽然 SERIALIZABLE 提供了更强的一致性保障，但它会锁住读操作，极大地影响并发性能。
    - 在大多数应用场景下，RR 提供的隔离性足够好，而相比于 SERIALIZABLE 来说，它允许更高的并发度。
4. **可重复读取**：
    - 在金融系统等需要强一致性的场景中，确保在同一事务中读取结果一致是非常关键的。但又要避免由于串行执行带来的性能问题，因此 RR 是一个不错的选择。
5. **锁机制的优化**：
    - InnoDB 在实现 RR 隔离级别时进行了优化，竞争条件相对少，在多数情况下表现优异。
    - 通过多版本并发控制（MVCC），读操作不会被写操作阻塞，从而提升了读写性能。
6. **广泛应用和标准**：
    - RR 是 SQL 标准之一，大多数数据库系统都实现了它，并且 MySQL 的实现经过多年的应用，已被证明是稳固、可靠和性能良好的。
7. **综合考量**：
    - 默认使用 RR 隔离级别可以简化开发过程，开发人员不必为达到更高的读一致性需求而在代码中显式更改事务隔离级别。
    - 在 MySQL 环境中，对于大多数应用程序（尤其是 Web 应用），RR 已经能够满足常见的数据一致性需求，而不必承担使用 SERIALIZABLE 级别带来的额外性能损耗。

综上所述，MySQL 选择 default 为 Repeatable Read 是为了在一致性和性能上找到一个合理的平衡点。RR 足以应对绝大部分场景，而同时支持较高的并发操作。


# MySQL的行级锁锁的到底是什么

MySQL 的 InnoDB 存储引擎实现的行级锁，实际上锁定的是基于索引的行记录。这意味着，行锁针对的是数据表中的索引记录，而非数据表本身的物理行。这一关键特性有以下几个具体的表现：

### 行级锁的锁定对象
1. **索引记录**：
    - InnoDB 行级锁会锁住某条索引记录。这意味着，如果要锁住一行数据，InnoDB 实际上需要锁住该行对应的索引项。
    - 即使在没有显式定义索引的情况下，InnoDB 也会使用隐式生成的主键索引来进行行锁。
2. **基于索引加锁**：
    - 如果一个 SQL 语句使用了 WHERE 条件且条件字段是经过索引的，则 InnoDB 会锁定符合条件的索引项对应的行。
    - 如果表结构中没有索引，InnoDB 则会退而锁住整张表，类似于表锁。

### 锁的运作和限制
1. **使用索引进行精确加锁**：
    - 精确的索引设计（包括主键和次级索引）对于高效行锁操作是至关重要的。这能保证锁住的只是相关的行，而不是误锁其他无关行。
2. **锁冲突的减少**：
    - 行级锁允许多个事务在不同的行上进行并发操作，从而提高了数据库的并发性能。
    - 减少使用未加索引的列来避免无意间锁定过多行。
3. **隐式锁和显式锁**：
    - 默认情况下，所有操作的锁都是由 InnoDB 自动管理的。
    - 开发者需要确保事务逻辑中使用索引字段进行条件过滤，以便行级锁能够正确应用。

### 间隙锁和 Next-key 锁
1. **间隙锁（Gap Lock）**：
    - 除了锁住索引项本身，InnoDB 在某些隔离级别下（如 Repeatable Read）还会锁住索引项之间的间隙，以防止幻读。
2. **Next-Key Lock**：
    - 是行锁与间隙锁结合形成的锁，用于精确地锁住相邻的索引记录和索引间隙，以防止插入操作引起的幻读。

### 小结
在 InnoDB 中，行级锁的具体对象是索引中的行记录。这实现了行粒度的高效并发控制，但要求数据库在使用上需合理设计索引以减少锁冲突和性能损失。通过理解和利用这一特性，开发者可以优化数据库性能和并发事务处理的效率。


# Mysql默认RR，大厂为啥要改成RC

在许多大规模应用程序和互联网公司中，选择将 MySQL 的默认隔离级别从 Repeatable Read (RR) 调整为 Read Committed (RC) 有几个重要原因，主要是为了在特定业务场景下优化性能和提升系统的并发处理能力。以下是一些关键点：

1. **更高的并发性能**：
    - 在 RC 隔离级别下，读操作不需要持有锁，从而减少了锁争用，特别是在高并发环境下可以显著提升系统的吞吐量。
    - RC 只需要更少的锁定和版本控制开销，因为它允许“不可重复读”，无需像 RR 一样为保证可重复读而加持多版本控制。
2. **降低锁等待与死锁概率**：
    - RC 级别避免了由于间隙锁而产生的锁等待和死锁问题，尤其是在频繁进行插入、更新操作时，这能降低锁竞争带来的风险。
    - 由于减少了锁的范围和锁的保留时间，系统线程间等待时间缩短，死锁概率相对更低。
3. **较弱的隔离级别适应性**：
    - 网络应用通常更倾向于性能优化，对强一致性的要求不如事务型应用高。RC 已经能够满足大多数Web应用所需的读一致性。
    - 这与互联网公司快速响应和高并发需求更加契合。
4. **简化应用架构**：
    - 使用 RC 可以简化应用程序设计，因为应用程序开发人员不需要处理因RR导致的复杂锁定问题。
    - 适用于需要快速开发、快速迭代的应用场景。
5. **数据库和缓存系统的协同**：
    - 许多大厂在架构设计中结合使用缓存系统，缓存系统缓解了数据库的一些一致性压力，让选择更高效处理的数据读取变得可行。
    - RC 降低了数据库负担，而在外层使用缓存保证某种程度的最终一致性。
6. **减少事务开销**：
    - 在 RC 模式下，数据库系统处理事务的开销相对较低，事务可以更快速的提交和回滚。
    - 提高响应速度对电商网站等对响应时间敏感的应用尤其重要。

选择在大厂中将隔离级别调整为 RC 是经过性能测试和业务场景验证的结果。在这样的决策中，公司重点考虑了性能优化的需求以及可以接受的隔离性降低所造成的数据一致性影响。最终的决定往往取决于具体的应用特性和业务需求。在某些事务的关键部分，仍然可以通过在代码中明确指定隔离级别来使用更高级别的隔离性。


# 区分度不高的字段建索引一定没用吗

在数据库设计中，某些区分度（选择性）不高的字段建立索引通常被认为效果不佳，但并不意味着完全没有用。在特定的情况下，这些索引可能仍然有其价值。下面是一些具体的考虑因素：

### 区分度不高的字段建索引的问题
1. **低效的过滤效果**：
    - 如果字段的选择性很低（例如只有几个不同的值），那么通过索引过滤数据的效果可能不明显，因为每个值对应太多的行。
2. **索引维护开销**：
    - 在更新或插入操作时，所有的索引需要同步更新，低选择性字段的索引可能带来不必要的开销，而收益有限。
3. **增大查询成本**：
    - 尽管索引帮助快速定位数据位置，但由于返回的数据集过大，可能会导致后续操作（如排序和过滤）带来额外的系统开销。

### 何时低选择性索引可能有用
1. **固定值查询**：
    - 即使选择性低，如果应用程序中有特定固定的值或者特定过滤条件经常被使用，并要求快速响应（如状态标志字段），索引仍可能提高查询速度。
2. **结合其他高选择性条件**：
    - 当低选择性的字段被结合其他有高选择性的字段一起使用时，可能仍然增益明显。
3. **作为覆盖索引的一部分**：
    - 如果一个多列索引（复合索引）包含一个低选择性字段，同时能使一个查询成为覆盖索引，这依然可以提升性能。
4. **大数据集中的特定场合**：
    - 在非常大的数据集中，占用大量数据的字段索引可能仍有助于减少所需的扫描行数。
5. **统计分析和报告**：
    - 如果索引用于统计或聚合操作中，通过索引可以更高效地进行分组操作。

### 小结
总体而言，低选择性字段单独设置索引的作用有限，因为从成本效益的角度来看，它们的性价比较低。然而，在特定情况下，例如与高选择性字段组合使用，或者需要在复杂查询中提供附加性能优势时，建立索引仍能提供帮助。因此，是否对低选择性的字段建立索引需要结合具体应用场景和查询场景进行权衡和测试。合理的性能测试和监控是优化索引策略的重要手段。


# 为什么不建议使用存储过程

存储过程是一种在数据库中为某些特定任务预编译和存储的一组SQL语句，它们在某些应用场景中可以提高性能和提供便利。然而，许多开发者和架构师在设计大型系统时会犹豫是否使用存储过程，因为它们也有一些局限和潜在的问题：

### 原因和局限性
1. **可移植性差**：
    - 存储过程通常是特定于数据库的，迁移到不同的数据库系统时可能需要重写，阻碍了数据库灵活性。
2. **调试困难**：
    - 调试存储过程通常比调试应用层代码困难。许多开发工具不支持良好的调试功能，难以设置断点或逐步执行。
3. **版本控制挑战**：
    - 与代码库中的源代码不同，存储过程通常不易进行版本控制和团队协作，导致管理复杂性增加。
4. **复杂性和可读性**：
    - 大量的存储过程可能导致业务逻辑分散在数据库中，使得维护和阅读难度增加。尤其是在大型团队中，难以追踪和更新。
5. **性能问题**：
    - 在个别情况下，存储过程的运行性能可能由于数据库执行计划的限制或缓存策略不足而不如应用程序代码。

### 何时使用存储过程
尽管存在以上讨这类问题，存储过程在以下场景中仍然非常有效：

+ **高性能需求**：当需要在数据库层进行复杂计算以减少网络往返时，存储过程能提供显著优势。
+ **复杂事务控制**：对数据库的复杂事务操作需要一致性和原子性，存储过程可更好地管理。
+ **业务规则集中管理**：在某些情况下，将部分业务逻辑下沉到数据库层可以集中管理复杂的数据库规则。
+ **多应用共享逻辑**：多个应用程序需要共享相同的数据操作逻辑时，使用存储过程能确保一致性。

### 总结
选择是否使用存储过程需要权衡系统需求、团队能力和维护复杂性等多个因素。在设计大型系统时，一般建议将存储过程仅用于特定场景，而非业务逻辑核心部分，保持数据库与应用之间的解耦以提高灵活性和可维护性。

[bilibili](https://player.bilibili.com/player.html?bvid=BV1kFpue5Ehj&p=12&page=12&autoplay=0)


# 什么时候索引失效反而提升效率

在大多数情况下，索引在查询中是用于提高性能的，因为它们加速了数据查找。然而，有些特殊情况下，索引的使用会导致性能下降，索引失效反而可能提升查询效率。以下是一些例子：

1. **小表查询**：
   * 对于非常小的表，MySQL可能会选择全表扫描（忽略索引），因为全表扫描的开销可能比通过索引逐行查找还要低。在这种情况下，索引失效不会损害性能，反而简化了查询。
2. **读取大部分或所有行**：
   * 当一个查询返回表中很大比例的行（如 30% 或更多）时，使用索引查找可能会耗时更多，因为数据库必须跳回主数据页以读取完整记录。全表扫描可能更有效，因为它可以逐行顺序读取数据。
3. **低选择性索引**：
   * 如果索引列的选择性非常低，例如一个布尔型字段，许多行有相同的值，那么依赖索引可能会产生不必要的开销。全表扫描可以避免索引的搜索和回表开销。
4. **频繁更新的表**：
   * 对于包含大量更新操作的表，索引的维护成本可能相对较高。尤其是在频繁更新索引列时，通过避免使用或减少复杂的索引可以减轻写操作的负担。
5. **复杂查询的优化选择**：
   * 对于复杂的多表联接查询，优化器有时可以选择执行计划中不使用某个索引（或部分失效）以提高整体联接和计算效率。
6. **数据分布与优化器误判**：
   * 在某些特定情况下，如果索引导致MySQL错误地估计数据分布或行数，手动禁用索引或提示优化器使用不同策略可能提升性能。

### 总结

尽管索引通常用于加速查询，但优化器会根据多种因素（包括表的大小、索引选择性、查询条件等）来选择是否使用索引。有时，跳过索引进行直接扫描能提高查询效率。这通常取决于查询的特性和数据的分布，所以在尝试优化查询性能时，应通过测试评估不同执行计划的得失。使用 EXPLAIN 分析查询计划是了解并优化查询性能的有效手段。

[bilibili](https://player.bilibili.com/player.html?bvid=BV1kFpue5Ehj\&p=8\&page=8\&autoplay=0)


# MySQL中like模糊查询如何优化

在MySQL中，LIKE 模糊查询可能会导致性能问题，特别是当使用通配符 % 开头时，因为这通常会导致全表扫描。以下方法可以帮助优化 LIKE 模糊查询：

### 1. 合理使用索引

* **前缀匹配**：使用LIKE 'prefix%'的形式，这种情况MySQL能够利用索引，比如：

```sql
SELECT * FROM users WHERE username LIKE 'John%';
```

如果username字段有索引，前缀匹配会用到索引。

### 2. 使用反向索引

对于需要匹配后缀的情况（即LIKE '%suffix'），可以创建一个辅助列存储反转字符串，并基于此列进行前缀匹配。

* **创建反向字符串**：

```sql
ALTER TABLE users ADD reversed_username VARCHAR(255);
UPDATE users SET reversed_username = REVERSE(username);
CREATE INDEX idx_reversed_username ON users(reversed_username);
```

### 3. 限制扫描范围

在LIKE查询中，如果可以通过其他条件进一步缩小搜索范围，请尽量加入这些条件。

```sql
SELECT * FROM users WHERE created_at >= '2023-01-01' AND username LIKE 'John%';
```

### 4. 使用缓存

如果相同的查询需要频繁执行，可以考虑在应用层实施缓存策略来减少数据库负载。

### 5. 使用专业工具

对于非常大的数据集或者需要复杂文本处理和搜索功能，可以使用外部全文搜索引擎如Elasticsearch、Solr或者Sphinx来代替MySQL的LIKE操作。

通过这些方法优化LIKE查询，可以显著提升数据库的查询性能。应根据具体场景选择合适的优化策略。使用EXPLAIN分析查询执行计划，可以帮助确认优化效果。

[bilibili](https://player.bilibili.com/player.html?bvid=BV1kFpue5Ehj\&p=5\&page=5\&autoplay=0)


# MySQL的深度分页如何优化

在MySQL中，当涉及到深度分页时（offset较大），性能可能会显著下降。这是因为MySQL需要扫描和跳过大量行才能到达所需的偏移量。这会导致大量的磁盘I/O和内存消耗，进而影响查询性能。以下是一些常用的优化深度分页的方法：

### 1. 基于主键或唯一索引的优化
利用主键或唯一索引可以显著提高深度分页的效率，因为它们能够指向特定的行。

+ **记录上次查询的最大ID**（或其他唯一标识符），并以此为起点进行下一次查询。这种方法需要有连续的、唯一的列（如自增ID）以用于分页。

```sql
SELECT * FROM table WHERE id > last_seen_id ORDER BY id ASC LIMIT page_size;
```

### 2. 使用子查询优化
通过子查询的方式，仅选择需要的记录ID，然后再通过这些ID提取完整记录。

+ **子查询结合JOIN**：

```sql
SELECT t.* FROM table t
JOIN (
  SELECT id FROM table ORDER BY id LIMIT offset, page_size
) sub ON t.id = sub.id;
```

### 3. 覆盖索引
确保分页操作使用的查询能够被覆盖索引满足，从而减少了回表（访问数据页）的次数。这样可以提高查询速度。

### 4. 缓存机制
在应用层面实现结果集缓存，避免重复查询。例如，可以将分页结果缓存到Redis或Memcached中。

### 5. 视业务情况优化
根据特定业务需求，可能可以优化显示的逻辑。例如，一些应用可以通过取得一定范围的结果并在客户端分页来减少数据库的负担。

### 6. 限制最大页数
限制应用程序中最大可翻页数，避免用户访问深度分页。提示数据太旧或已过时，要求用户进行新的查询。

通过结合上述方法，可以有效地减少深度分页带来的性能影响。具体选择何种策略需要考虑数据特性和业务需求。使用EXPLAIN命令分析每个查询计划，以确保优化真正有效。

[bilibili](https://player.bilibili.com/player.html?bvid=BV1kFpue5Ehj&p=9&page=9&autoplay=0)


# Innodb加索引的时候会锁表吗

在 InnoDB 中，操作索引时是否锁表取决于具体的操作类型。有些情况可能会导致表锁，而有些情况则不会。以下是一些需要考虑的方面：

### 1. 添加索引时

* **在线添加索引（Online DDL）**：
  * 从 MySQL 5.6 开始，InnoDB 支持在线添加索引。这意味着在添加索引期间，表可以同时进行读取和写入操作，从而不会锁住整张表。
  * 在线 DDL 的特性允许通过特定配置，让表在加索引的同时保持可用状态（如 LOCK=NONE 选项）。
* **锁级别**：
  * 默认情况下，即使是在线添加索引，也可能会对表的某些部分进行短暂的锁定，但不会长期锁表。
  * 需要注意的是，在不支持在线 DDL 的旧版本中，添加索引通常是涉及锁表的操作，尤其是在大量数据情况下。

### 2. 删除索引

* 删除索引操作通常不需要长时间锁表，但在删除过程中可能进行短暂的锁定以保证元数据更新的一致性。

### 3. 修改索引

* 对于某些索引修改，可能会引发锁表现象，尤其是在不支持在线 DDL 的情况下或在某些特定场景下，需要评估具体MySQL版本和参数配置。

### 4. 操作期间的锁定影响

* 使用在线 DDL 功能时，可能依旧有性能上的影响，比如对 I/O 的消耗增加。
* 因此进行大规模索引修改或添加操作建议在低峰期或通过分片、复制环境测试后实施。

### 小结

在现代 MySQL 版本中，InnoDB 通过支持在线 DDL 特性，在大多数索引相关操作中不需要锁表，这是为了降低对生产环境的影响。在进行索引操作时，务必检查使用的 MySQL 版本支持的功能，并合理配置相关参数以实现并发数据访问和操作的最小化冲突。


# 为什么MySQL8.0要取消查询缓存

MySQL从8.0版本开始移除了查询缓存，主要是由于查询缓存在许多场景下带来的性能问题和复杂性。以下是取消查询缓存的一些主要原因：

1. **全局锁定问题**
    - 查询缓存会在多用户环境中引发全局锁定问题。当一个表被修改时，相应的查询缓存需要被刷新，这会导致查询缓存的全局锁定，从而影响数据库的并发性能。
2. **竞争与争用**
    - 在高并发环境中，由于查询缓存需要锁定来维持一致性，导致了大量竞争和锁争用。这种情况在写操作频繁和查询频繁的环境中尤为明显，因为每次写操作都可能触发缓存失效。
3. **维护与复杂性**
    - 查询缓存的维护引入了额外的复杂性。需要不断监控和刷新缓存，当表更新时需要对缓存进行适当管理，增加了数据库的维护开销。
4. **缓存命中率低**
    - 在许多实际应用中，查询缓存的命中率并不高，尤其是在动态数据系统中。因为数据变更频繁，缓存很容易失效，从而无法提供预期的性能提升。
5. **替代方案的有效性**
    - 随着内存容量的增加及更高效的缓存方案（如应用层缓存和外部缓存工具）的广泛应用，查询缓存不再是提高查询性能的最佳解决方案。
    - 许多现代应用程序使用如Redis、Memcached等专门的缓存系统来缓存查询结果，而不是依赖数据库的查询缓存。
6. **复杂查询的支持**
    - MySQL查询缓存只适用于非常简单的SELECT查询，而不支持复杂查询的缓存。这限制了它在现代应用中广泛使用。

通过取消查询缓存，MySQL 8.0简化了数据库引擎的设计，使其更关注于核心事务处理与数据一致性。同时，开发者也被鼓励采用更灵活和可扩展的外部缓存解决方案，这些方案可能更适合现代应用的需求。

取消查询缓存是朝着提高系统整体稳定性和性能的一步，特别是在高负载和分布式数据库环境中。


# 一条SQL的执行过程是怎样的

一条 SQL 的执行过程可以大致分为以下几个步骤：

1. **连接器：**
    - 客户端与数据库建立连接，并发送 SQL 语句给数据库服务。
    - 连接器验证客户端的身份和权限，确保用户有足够的权限执行该 SQL 语句。
2. **查询缓存：**
    - 连接器首先检查查询缓存，尝试找到与当前 SQL 语句完全相同的查询结果。
    - 如果在缓存中找到匹配的结果，查询缓存直接返回结果，避免了后续的执行过程。
3. **分析器：**
    - 若查询不命中缓存，连接器将 SQL 语句传递给分析器进行处理。
    - 分析器对 SQL 语句进行语法分析，确保语句的结构和语法正确。
    - 分析器还会进行语义分析，检查表、列、函数等对象的存在性和合法性，并进行权限验证。
4. **优化器：**
    - 分析器将经过验证的 SQL 语句传递给优化器。
    - 优化器根据统计信息和数据库的规则，生成多个可能的执行计划，这些计划包括不同的索引选择、连接顺序、筛选条件等。
    - 目的是选出最优的执行路径以提高查询性能。
5. **执行器：**
    - 优化器选择一个最优的执行计划，并将其传递给执行器。
    - 执行器根据执行计划执行具体的查询操作。
    - 它负责调用存储引擎的接口，处理数据的存储、检索和修改。
    - 执行器会根据执行计划从磁盘或内存中获取相关数据，并进行联接、过滤、排序等操作，生成最终的查询结果。
6. **存储引擎：**
    - 执行器将查询请求发送给存储引擎组件。
    - 存储引擎组件负责具体的数据存储、检索和修改操作。
    - 存储引擎根据执行器的请求，从磁盘或内存中读取或写入相关数据。
7. **返回结果：**
    - 存储引擎将查询结果返回给执行器。
    - 执行器将结果返回给连接器。
    - 最后，连接器将结果发送回客户端，完成整个执行过程。

需要注意的是，查询缓存在一些场景下可能不太适用，因为它有一定的缺陷和开销。MySQL 8.0 版本开始，默认情况下查询缓存已被废弃。因此，在实际应用中，需要权衡是否使用查询缓存。


# 说下你对分库分表的理解

MySQL的分库分表拆分策略通常包括**垂直拆分**和**水平拆分**两种方式。下面我将介绍这两种策略以及分库分表面临的问题和解决方案。

+ **水平切分：**水平切分又称为 Sharding，它是将同一个表中的记录拆分到多个结构相同的表中。当一个表的数据不断增多时，Sharding 是必然的选择，它可以将数据分布到集群的不同节点上，从而缓存单个数据库的压力。
+ **垂直切分：**垂直切分是将一张表按列切分成多个表，通常是按照列的关系密集程度进行切分，也可以利用垂直切分将经常被使用的列和不经常被使用的列切分到不同的表中。

**分库分表面临的问题和解决方案如下：**

1. **数据一致性：**由于数据被分布到不同的数据库和表中，分库分表涉及跨节点的事务，需要确保数据的一致性。可以采用两阶段提交（2PC）协议、最终一致性方案或者基于分布式事务的工具来管理分布式事务，确保数据的一致性。
2. **跨分片查询：**当业务需要跨多个分片进行查询时，可能会面临性能问题和复杂的查询逻辑。可以使用分布式查询引擎、数据聚合、缓存和分布式计算框架等技术来处理跨分片查询需求，提高查询效率和简化查询逻辑。
3. **全局唯一性约束：**在分库分表环境下，全局唯一性约束可能受到挑战。可以采用分布式唯一ID生成器（如Snowflake算法）来生成全局唯一ID，避免冲突。

在实施分库分表时，需要根据具体情况选择适合的拆分策略，并结合具体的业务特点进行优化和调整。同时，有效的监控和测试也是必不可少的，以确保分库分表系统的高可用性、性能和稳定性。


# 高并发场景下，如何安全修改同一行数据

在高并发情况下，多事务安全修改同一行数据可以采用以下方法：

1. **乐观锁：在数据表中添加一个版本号（或者时间戳）字段，每次更新数据时都会检查该字段的值。**当多个并发的请求同时修改同一行数据时，只有一个请求能够成功执行更新操作，其他请求需要重新检查数据是否被修改过。如果数据没有被修改，那么它们可以重新尝试更新；如果数据已经被修改，则这些请求需要触发重试等相应的冲突处理逻辑。
2. **悲观锁：**在读取数据之前，使用数据库提供的锁机制，如SELECT ... FOR UPDATE语句，将要修改的行数据进行加锁。这样，其他并发的请求在读取相同行数据时会被阻塞，直到锁释放。这种方法能够确保同一时间只有一个请求在修改数据，但是会影响系统的并发性能。
3. **分布式锁：**通过使用分布式锁服务，如Redis的SETNX命令或ZooKeeper的临时节点，来实现对行级数据的互斥访问。在修改数据前先尝试获取锁，获取成功后执行数据修改操作，修改完成后释放锁。其他请求在获取锁失败时可以等待或执行相应的冲突处理逻辑。
4. **事务：**将对同一行数据的修改操作封装在数据库事务中。在事务中，数据库会自动处理并发修改的冲突，通过锁定相应的数据行来确保数据的一致性和完整性。并发的请求会被串行化执行，保证每个请求都能正确读取并修改数据。

需要注意的是，在进行高并发的数据操作时，要考虑到锁的粒度、性能开销以及可能出现的死锁问题，做好并发控制和冲突处理的容错设计。


# 索引失效的情况有哪些

索引失效是指在使用索引进行查询时，索引无法发挥作用，导致查询性能下降。常见的导致索引失效的情况有以下几种： 口诀 “**模型数空运最快**”

**模**糊查询。like查询以%开头，会导致索引失效。可以有两种方式优化： a. 使用覆盖索引优化，只查询索引列； b. 把%放后面，索引生效

数据类**型**。编写sql时要保证索引字段与匹配数据类型一致。

函**数**。索引字段不做函数处理

**空**。null值需要慎重使用 唯一索引有null值 not null & null（不同版本会有不同。5.7refornull 8组合其他null的大概率能走，不过也可能会all）

**运**算。索引字段不做运算

**最**左匹配。尽量满足最左匹配

索引检索值超过临界比。不走索引遍历整张表反而更快则不会走索引

综上所述，我们要解决索引失效的问题，可以通过合理设计索引、优化查询语句以及避免索引失效的情况发生来提升查询性能。


# 为什么需要数据库连接池呢_

首先，我们要明白数据库连接池是一种管理和维护数据库连接的技术。它在应用程序和数据库之间建立了一个连接的缓冲池，用于存储和复用已经建立好的数据库连接。

那为什么需要数据库连接池呢？

1. **提高性能：**数据库连接的建立和断开是比较耗时的操作，频繁地创建和销毁连接会增加系统的负担。通过使用连接池，可以避免频繁地创建和关闭连接，减少了连接的开销，提高了系统的性能。
2. **资源管理：**数据库连接是有限的资源，如果每个请求都创建一个新的连接，可能导致连接过多而耗尽资源。连接池通过对连接的管理和复用，能够更有效地管理数据库连接，避免资源的浪费。
3. **并发处理：**在高并发的场景下，如果每个请求都去单独连接数据库，可能会导致数据库连接数量过多，从而限制了系统的扩展性。连接池允许多个请求共享连接，减少了数据库连接的数量，提高了并发处理能力。
4. **连接可靠性：**数据库连接可能会因为网络问题或服务器故障而中断，当发生这种情况时，连接池能够检测到连接的失效，并重新创建一个可用的连接，确保应用程序的可靠运行。

**总结来说： **数据库连接池是为了提高性能、更有效地管理资源、提高并发处理能力和增加连接的可靠性而存在的。它通过缓存已经建立好的连接，复用连接以及管理连接的生命周期，从而减少了连接的开销，提高了系统的性能和稳定性。


# 分库分表下如何实现精准分页？

哈喽，大家好，我是JJ，今天给大家分享一道数据库的高频面试题：**分库分表下如何实现精准分页？**

在分库分表的数据库架构中，精准分页是一个有挑战性的问题，因为数据被分散存储在不同的分片和数据库中。

想要实现精准分页就需要解决两个主要问题：**跨分片和跨库的数据访问**。

**跨分片**，常见的方法是使用**记录游标分页**。这种方法会在每个分片中**记录上一页或下一页的分页标识**，比如记录上一页或下一页的最后一条记录的**主键**。

然后，当执行分页查询时，根据游标进行定位，从而实现精准分页。

虽然这种方法相对简单，但是需要在分片中**维护额外的索引或元数据信息**。

**跨库的话**，可以通过**数据同步**或者**查询路由**来实现跨库的数据分页。

**数据同步**意味着将分片中的数据复制到一个统一的主库中，然后在主库上执行分页操作。

**查询路由**则是在查询时根据分页条件将请求发送到对应的分片或库中，然后在各个分片中执行分页操作，最后将结果合并返回给客户端。

这种方法可以**减少数据复制的开销**，但是会**增加系统的复杂性和维护成本**。

在实际应用中，需要进行实际性能测试和优化，确保系统能够满足实际需求。

同时，还需要考虑数据一致性和容错性等方面的问题，保证系统的稳定性和可靠性。


# 什么是最左前缀原则？

最左前缀原则（Leftmost Prefix Rule）是索引在数据库查询中的一种使用规则。它指的是在使用复合索引时，索引的最左边的连续几个列会被用于查询过滤条件的匹配。

具体来说，如果在表中创建了一个复合索引，包含多个列 A、B、C，那么最左前缀原则要求查询中的过滤条件必须从索引的最左边开始，并且不能跳过中间的列。只有当查询中的过滤条件与索引的最左前缀完全匹配时，索引才能被充分利用。

例如，考虑以下复合索引 (A, B, C) 和查询语句：

```plsql
SELECT * FROM my_table WHERE A = 'value1' AND C = 'value2';
```

在这种情况下，最左前缀原则要求查询条件中必须包含列 A，而不能直接使用列 C 进行过滤。因为只有满足最左前缀条件，索引 (A, B, C) 才能被有效地使用。

遵循最左前缀原则的好处包括：

1. **提高查询性能：**通过使用索引的最左前缀，可以最大限度地减少索引扫描的数据量，提高查询的效率和响应时间。
2. **减少索引占用空间：**在某些情况下，使用最左前缀原则可以减少创建多个索引的需求，节省磁盘空间和索引维护的开销。

需要注意的是，最左前缀原则并不适用于所有的情况。有时候，根据具体的查询需求和数据模式，可能需要创建额外的索引来支持更复杂的查询条件。因此，在设计和优化数据库索引时，需要综合考虑查询的特点和性能要求，灵活选择适当的索引策略。


# 并发事务带来哪些问题_

并发事务可以带来以下几个问题：

1. **脏读（Dirty Read）：**一个事务读取了另一个事务未提交的数据。假设事务A修改了一条数据但未提交，事务B却读取了这个未提交的数据，导致事务B基于不准确的数据做出了错误的决策。
2. **不可重复读（Non-repeatable Read）：**一个事务在多次读取同一数据时，得到了不同的结果。假设事务A读取了一条数据，事务B修改或删除了该数据并提交，然后事务A再次读取同一数据，发现与之前的读取结果不一致，造成数据的不一致性。
3. **幻读（Phantom Read）：**一个事务在多次查询同一范围的数据时，得到了不同数量的结果。假设事务A根据某个条件查询了一组数据，事务B插入了符合该条件的新数据并提交，然后事务A再次查询同一条件下的数据，发现结果集发生了变化，产生了幻觉般的新增数据。
4. **丢失修改（Lost Update）：**两个或多个事务同时修改同一数据，并且最终只有一个事务的修改被保留，其他事务的修改被覆盖或丢失。这种情况可能会导致数据的部分更新丢失，造成数据的不一致性。

**不可重复读和幻读区别：**

不可重复读的重点是修改比如多次读取一条记录发现其中某些列的值被修改，幻读的重点在于新增或者删除比如多次读取一条记录发现记录增多或减少了。


# 数据库cpu飙升，你会如何处理

当MySQL数据库的CPU使用率飙升时，可能是由于以下几个原因导致的：

1. **查询性能问题：**某些查询可能没有被正确地优化，导致查询执行时间过长，从而占用大量的CPU资源。可以通过查看慢查询日志和执行计划来分析问题查询，并进行索引优化、重写查询语句或调整数据库配置等方式来改善查询性能。
2. **数据库连接问题：**如果存在大量的数据库连接并发访问，可能会造成CPU负载过高。可以检查应用程序连接池的配置情况、数据库连接数限制以及是否有闲置的连接未关闭等问题，并进行相应调整。
3. **锁和死锁问题：**并发事务之间的锁竞争或死锁可能导致CPU飙升。可以通过查看数据库的锁状态、死锁日志以及事务并发控制的设置来解决锁相关的问题。
4. **配置问题：**不合理的数据库配置可能导致CPU资源浪费和效率低下。可以检查MySQL的配置参数，如缓冲区大小、并发连接数、线程池大小等是否合理设置，并进行相应调整。
5. **资源竞争：**如果服务器的物理资源（如内存、磁盘I/O）不足或受限，可能会导致CPU过度使用。可以通过监控系统资源使用情况，调整或增加资源配置，以满足数据库的需求。

此外，定期进行数据库性能优化和监控也是重要的措施，可以通过数据库性能分析工具、慢查询日志、系统监控工具等来识别和解决性能问题。


# B树和B+树的区别？

B树和B+树是常用的数据结构，用于在数据库中进行索引操作。它们之间的区别主要有以下几个方面：

1. **数据存储方式：**在B树中，每个节点都包含键和对应的值，叶子节点存储了实际的数据记录；而B+树中，只有叶子节点存储了实际的数据记录，非叶子节点只包含键信息和子节点的指针。
2. **数据检索方式：**在B树中，由于非叶子节点也存储了数据，所以查询时可以直接在非叶子节点找到对应的数据，具有更短的查询路径；而B+树的所有数据都存储在叶子节点上，只有通过叶子节点才能获取到完整的数据。
3. **范围查询效率：**由于B+树的所有数据都存储在叶子节点上，并且叶子节点之间使用链表连接，所以范围查询的效率较高。而在B树中，范围查询需要通过遍历多个层级的节点，效率相对较低。
4. **适用场景：**B树适合进行随机读写操作，因为每个节点都包含了数据；而B+树适合进行范围查询和顺序访问，因为数据都存储在叶子节点上，并且叶子节点之间使用链表连接，有利于顺序遍历。

**总结来说：** B树和B+树在数据存储方式、数据检索方式、范围查询效率以及适用场景方面存在区别。B树适合随机读写操作，而B+树适合范围查询和顺序访问。在实际应用中，根据不同的场景和需求选择合适的树结构可以带来更高效的数据处理和索引操作。


# MySQL索引底层结构为什么使用B+树

MySQL使用B+树作为索引的底层结构有以下几个主要原因：

1. **良好的平衡性：**B+树是一种自平衡的树结构，不论是在插入、删除还是查询操作中，它都能保持相对较好的平衡状态。这使得B+树能够快速定位到目标数据，提高查询效率。
2. **顺序访问性：**B+树的所有叶子节点是按照索引键的顺序排序的。这使得范围查询和顺序访问非常高效，因为相邻的数据通常在物理上也是相邻存储的，可以利用磁盘预读提高IO效率。
3. **存储效率：**B+树在内存中的节点大小通常比其他树结构更大，这样可以减少磁盘I/O操作的次数。同时，B+树的非叶子节点只存储索引列的值，而不包含实际数据，这进一步减小了索引的尺寸。
4. **支持高并发：**B+树的特性使得它能够支持高并发的读写操作。通过使用合适的锁或事务隔离级别，多个并发查询和更新操作可以同时进行而不会出现严重的阻塞或冲突。
5. **易于扩展和维护：**B+树的结构相对简单，可以较容易地进行扩展和维护。当插入或删除数据时，B+树只需要调整路径上的少数节点，而不需要整颗树的重构。这样能够有效降低维护成本，并保证索引的高性能。

综上所述，B+树具有良好的平衡性、顺序访问性、存储效率、并发性和可扩展性，使得它成为一种理想的索引底层结构。


# MySQL为什么默认引擎是InnoDB

MySQL 默认的存储引擎是 InnoDB，这是因为 InnoDB 在性能、事务支持和容错能力等方面具有较好的特性，适合大多数应用场景。下面是一些原因：

1. **支持事务：**InnoDB 是一个支持事务的存储引擎。事务是一组数据库操作的原子性执行，可以保证操作的一致性和完整性。
2. **并发控制：**InnoDB 支持行级锁定，在高并发环境下可以最大程度地减少锁冲突，提高并发性能。相比之下，MySQL 的另一个存储引擎 MyISAM 只支持表级锁定，并发性能较低。
3. **外键约束：**InnoDB 支持外键约束，可以保证数据的完整性。外键用于建立表与表之间的连接，通过外键约束可以实现数据之间的关联和参照完整性。
4. **崩溃恢复：**InnoDB 具有自动崩溃恢复的能力。即使在发生意外故障或系统崩溃时，InnoDB 引擎也能够自动进行崩溃恢复，保障数据的一致性。
5. **支持热备份：**InnoDB 支持在线热备份，可以在不停止数据库服务的情况下进行备份操作。这对于需要实时运行且对数据可用性要求高的应用程序非常重要。

需要注意的是，虽然 InnoDB 是 MySQL 默认的存储引擎，但在某些场景下，可以根据实际需求选择其他存储引擎，如 MyISAM、Memory 等。不同的存储引擎适用于不同的应用场景和需求。


# where1=1会不会影响性能？

那当sql的条件是动态的， 很多小伙伴会在where后面跟上1=1以保证语，经常看网上的八股文说1=1会影响性能， 建议用Mybatis的标签.到底是不是这样的呢？

 有需要跳槽面试的小伙伴可以再，。

那where 1=1 和  标签 两种方案，该如何选择？

* 如果 MySQL Server版本小于 5.7，用了 MyBatis的话，建议使用 标签。

* 如果 MySQL版本大于等于 5.7，两个随便选；因为在MySQL5.7后，有一个所谓的（常量折叠优化）可以在编译期消除重言式表达式。什么是重言式表达式，就是任何时候永远都为true的结果， 就会被优化器识别并优化掉，好奇的话你可以通过**show** warnings;查看，就会发现1=1没有了。并且我也在一张100多万的表里面把1=1 和标签分别做了100次查询， 耗时时间相差无几。  所以5.7后两种方式随便选。

  当然现在 MySQL Server版本基本都是 5.7以上了，不是的话那赶紧升级吧还是。好如果视频对你有帮助可以一键三连哦， 我们下期见


# 说下你对数据库事务的理解

数据库事务是指一系列数据库操作的逻辑单元，这些操作要么**全部成功执行**，**要么全部回滚**。它的目的是确保数据的一致性和完整性。**事务具备4大特性，即原子性、一致性、隔离性和持久性：**

**原子性：**事务中的所有操作要么全部执行成功，要么全部回滚到事务开始前的状态。如果在事务执行期间发生错误，系统将回滚所有已执行的操作，以保持数据的一致性。

**一致性：**事务的执行不会破坏数据库的完整性约束。在事务开始和结束时，数据库必须处于一致的状态。

如小李转账100元给小白，不管操作是否成功，小李和小白的账户总额是不变的。

**隔离性：**事务的执行是相互隔离的，即每个事务对其他事务是透明的。并发执行的多个事务不会相互干扰，每个事务感知不到其他事务的存在。

**持久性：**一旦事务提交成功，事务中的所有操作都必须持久化到数据库中。

以上就是我对数据库事务的理解。


# mysql中in和exists的区别

当谈到 MySQL 中的 IN 和 EXISTS 时，它们都是用于查询和筛选数据的条件语句，但有一些重要的区别：

1. **IN关键字：**使用 IN 条件时，我们提供一个固定的值列表，然后将其与指定列的值进行比较。如果列中的值与列表中的任何一个值匹配，就会返回结果。IN 条件适合用于确定某个字段的值是否在给定的值列表中。

例如，SELECT * FROM table_name WHERE column_name IN (value1, value2, value3);

如果 column_name 的值与 value1、value2 或 value3 中的任何一个相匹配，那么这条记录将会被返回。

2. **EXISTS关键字：**使用 EXISTS 条件时，我们需要指定一个子查询。查询的结果并不重要，而是判断子查询是否返回了至少一行结果。如果子查询返回了结果，EXISTS 条件就会被认为是满足的。EXISTS 条件适合用于判断某个条件是否至少存在于子查询的结果中。

例如，SELECT * FROM table_name WHERE EXISTS (SELECT * FROM another_table WHERE condition);

如果子查询(SELECT * FROM another_table WHERE condition)返回了至少一行结果，那么主查询中的记录将会被返回。

**总结来说：**

+ 使用 IN 条件时，比较的是指定列的值是否在给定的值列表中。
+ 使用 EXISTS 条件时，判断的是子查询是否返回了至少一行结果。


# 数据库三大范式是什么

数据库三大范式是关系数据库设计中的一组规范，旨在提高数据结构的合理性、减少数据冗余和提高数据操作的效率。它们分别是：

+ **第一范式（1NF）**：确保每个数据列都是不可再分的原子值，即每个单元格中只包含一个值。这可以通过将表拆分为更小的表来实现，每个表都包含一个实体的属性。
+ **第二范式（2NF）**：建立在第一范式的基础上，要求表中的每个非主键列完全依赖于主键列，而不是依赖于其他非主键列。换句话说，每个表应该只描述一个实体的信息。如果有部分信息依赖于表中的一部分主键，那么需要将这些信息拆分到另一个表中。
+ **第三范式（3NF）**：在第二范式的基础上，要求表中的每个非主键列之间不应该存在传递依赖关系。也就是说，非主键列之间不应该相互依赖，而是直接依赖于主键列。如果存在传递依赖，需要将其转化为直接依赖关系。

这三个范式是逐步规范化设计数据库的步骤，目的是**提高数据的一致性、完整性和减少冗余**，从而**提高数据库的性能和可维护性**。但要注意，范式化设计并不是一成不变的，根据具体的业务需求和应用场景，有时也需要对范式进行适度的调整和冗余处理。


# MyISAM索引与InnoDB索引的区别？

MyISAM和InnoDB是MySQL中两种常见的存储引擎，它们在索引实现上存在以下区别：

1. **存储方式：**MyISAM使用非聚簇索引，索引文件和数据文件是分开的；而InnoDB使用聚簇索引，将索引和数据一起存储在同一个文件中。
2. **锁机制：**MyISAM采用表级锁定，意味着当对表进行写操作时，整个表都会被锁定，因此可能导致并发写操作的性能较差。而InnoDB采用行级锁定，只锁定需要修改的行，可以提供更好的并发性能和多用户写入的支持。
3. **事务支持：**MyISAM不支持事务处理，而InnoDB支持事务和ACID特性（原子性、一致性、隔离性和持久性），可以进行事务管理、回滚和恢复操作。
4. **引用完整性：**MyISAM不支持外键约束，而InnoDB支持外键约束，可以设置关联关系来保证数据的完整性。
5. **性能特点：**MyISAM在读取频繁、插入和更新较少的场景下性能较好，特别适合于读密集型应用；而InnoDB在并发写入和更新较多的情况下性能较好，适合于写入密集型应用或需要事务支持的场景。

以上就是MyISAM索引与InnoDB索引的五点区别，我们在实际使用时需要根据具体的应用需求和场景来选择适合的存储引擎和索引类型。


# 如何解决MySQL死锁问题

MySQL在并发环境下可能会出现死锁问题。死锁是指两个或多个事务互相等待对方释放资源，导致无法继续执行的情况。

解决死锁问题的方法通常有以下几种：

1. **调整事务隔离级别：**通过将事务隔离级别降低为读未提交（或读已提交，可以减少死锁的发生概率。但是要注意隔离级别的降低可能引发脏读、不可重复读等数据一致性问题，在选择时需要权衡利弊。
2. **优化查询和事务逻辑：**分析造成死锁的原因，优化查询语句和事务逻辑，尽量缩短事务持有锁的时间，减少死锁的可能性。比如按照相同的顺序获取锁，避免跨事务的循环依赖等。
3. **使用行级锁：**行级锁可以较小地限制锁的范围，从而减少死锁的可能性。将表的锁粒度调整为行级别，可以减少事务之间的冲突。
4. **设置合理的超时时间和重试机制：**当发生死锁时，可以设置适当的超时时间，在一定时间内尝试解锁操作。如果超过设定的时间仍未成功，则进行死锁处理，如终止较早请求的事务或进行回滚等。

需要根据具体情况分析和实施相应的解决方案，并进行测试和验证，以确保解决死锁问题，并提高数据库的并发性能。


# MySQL多表查询时有哪些连接方式

当进行多表查询时，在 MySQL 中常用的连接方式有以下几种：

1. **内连接（INNER JOIN）：**返回同时满足连接条件的行。它通过比较连接列的值，将两个或多个表中匹配的行组合在一起。
2. **左外连接（LEFT JOIN）：**返回左表中的所有行，以及与左表匹配的右表的行。如果右表中没有匹配的行，对应的列将填充为 NULL。
3. **右外连接（RIGHT JOIN）：**返回右表中的所有行，以及与右表匹配的左表的行。如果左表中没有匹配的行，对应的列将填充为 NULL。
4. **全外连接（FULL JOIN）：**返回左右两个表中的所有行。如果某个表中没有匹配的行，对应的列将填充为 NULL。需要注意 MySQL 不支持 FULL JOIN 可以使用UNION ALL 模拟。
5. **自连接（Self JOIN）：**将单个表视为两个独立的表，使用别名来引用同一个表。这种连接适用于在同一个表中根据某些条件关联不同的行。
6. **交叉连接（CROSS JOIN）：**返回两个表的笛卡尔积，即所有可能的组合。它将第一个表的每一行与第二个表的每一行进行组合。

在实际使用中我们可以根据具体的需求选择合适的方式来联合多个表，获取所需的数据。


# 创建索引时需要注意什么？

在创建索引时，需要注意以下几点：

1. **选择适当的列：**根据实际查询需求和数据特点，选择合适的列作为索引列。通常情况下，选择经常被用于查询条件、排序或聚合操作的列作为索引列可以获得更好的性能。
2. **避免过多的索引：**过多的索引会增加存储空间的开销，并且在数据写入时需要维护多个索引结构，导致性能下降。因此，只创建必要的索引，避免不必要的冗余索引。
3. **考虑联合索引：**对于多个列的组合查询条件，可以考虑创建复合索引。复合索引可以覆盖多个列，减少查询时需要访问的索引数量，提高查询效率。
4. **注意索引的顺序：**对于多列索引，考虑索引的顺序。将最常用的列放在索引的前面，以提高查询性能。
5. **使用合适的数据类型：**选择合适的数据类型可以减小索引的大小，提高索引的效率。尽量避免使用过长或过大的数据类型作为索引列。

综上所述，创建索引需要根据具体的查询需求、数据特点和系统环境来进行权衡和决策。合理创建索引可以提升数据库的性能，但也需要注意索引的维护成本和更新操作的影响。


# MySQL记录货币用什么字段类型

在MySQL中记录货币金额，一般推荐使用DECIMAL字段类型。

DECIMAL字段类型用于存储精确的定点数值，可以指定总共的位数和小数点后的位数。这使得它非常适合用于存储货币金额，因为货币金额通常需要精确到小数点后几位。

以下是一个示例创建DECIMAL字段类型的语句：

```plsql
CREATE TABLE my_table (
   amount DECIMAL(18, 2)
);
```

上述语句创建了一个名为amount的DECIMAL字段，总共有18位，其中小数点后有2位。

使用DECIMAL字段类型的好处包括：

1. **精确性：**DECIMAL字段类型可以确保货币金额的精确性，避免由于浮点数运算带来的精度问题。
2. **可控性：**通过指定总位数和小数位数，可以精确控制存储的金额范围和精度。
3. **计算准确性：**DECIMAL字段类型支持数值计算，如加法、减法和乘法等，保证计算结果的准确性。

需要注意的是，DECIMAL字段类型占用的存储空间相对较大，因此在设计表结构时需要考虑存储和性能需求，合理选择DECIMAL字段的位数。另外，应根据具体业务需求和国际化要求，考虑货币符号和货币转换等问题。


# 什么时候不要使用索引？

在大多数情况下，使用索引可以提高数据库查询的性能和效率。但也有一些情况下，不使用索引可能更合适：

+ **小型表：**对于非常小的表，可能不需要使用索引。因为索引的维护需要额外的存储空间和计算资源，而对于小型表来说，全表扫描的开销可能相对较小。
+ **插入、更新和删除频繁的表：**如果表的插入、更新和删除操作非常频繁，而且对查询性能的要求相对较低，则可以考虑不使用索引。因为索引的维护会增加写操作的开销，可能导致性能下降。
+ **查询条件不经常使用：**如果某个字段很少用作查询条件，而且表的数据量较小，那么为该字段创建索引可能没有太大的性能提升。
+ **需要频繁更新索引的表：**对于频繁进行大量写操作（插入、更新、删除）的表，索引的维护成本可能会超过索引带来的查询性能提升，此时可以考虑不使用索引。

需要注意的是，实际情况还需结合具体的业务需求、数据规模和性能要求来综合考虑。在设计数据库时，综合权衡索引的使用与否，并进行性能测试和优化是非常重要的。


# 讲讲主从复制原理与延迟

**MySQL 的主从复制原理如下：**

首先，主库将变更写入 binlog 日志。

从库连接到主库后，有一个 IO 线程负责将**主库的 binlog 日志**复制到自己本地，并写入到**中继日志**中。

然后，从库中有一个 SQL 线程会从中继日志读取 binlog，并执行其中的 SQL 内容，即在从库上再次执行一遍。

以上就是主从复制的原理。那么**主从延迟的原因有哪些呢？ **

1. 主库的从库太多，主库需要将 binlog 日志传输给多个从库，导致复制延迟。
2. 在从库执行的 SQL 中存在慢查询语句，会导致整体复制进程的延迟。
3. 如果主库的读写压力过大，会导致主库处理 binlog 的速度减慢，进而影响复制延迟。

**为了优化主从复制的延迟，我们可以采取以下措施：**

1. 减少从库的数量，降低主库的负载，减少复制延迟。
2. 优化慢查询语句，减少从库执行SQL 的延迟。
3. 对主库进行性能优化，减少主库的读写压力，提高 binlog 写入速度。

通过以上措施可以帮助降低主从复制的延迟，提高复制的效率和一致性。


# 什么是索引？索引有哪些优缺点？

索引是数据库中用于**提高数据检索性能**的**排好序的数据结构**。它类似于书籍的目录，通过建立特定的数据结构将列或多个列的值与它们在数据表中对应的行关联起来，以加快查询速度。

**索引的优点包括：**

1. **提高查询性能：**索引可以加快数据库查找数据的速度，通过快速定位到符合查询条件的数据行，减少了数据库进行全表扫描的开销，从而显著提高查询效率。
2. **唯一性约束：**通过在索引上设置唯一性约束，可以确保数据的唯一性，防止重复数据的插入。

**然而，索引也有一些缺点：**

1. **占用存储空间：**索引通常需要占用一定的磁盘空间。过多的索引可能会增加存储成本。
2. **索引维护的开销：**当对数据表进行插入、更新或删除操作时，索引也需要进行相应的维护操作，这可能导致数据写入的性能下降，更新缓慢。

因此，在设计数据库时，需要根据具体的查询需求、数据特点和系统环境来决定是否以及如何建立索引，以平衡查询性能和维护成本。


# 分表后非分片键的查询、排序怎么处理

在使用分表后，非分片键的查询和排序可以通过以下方式进行处理：

1. **联合查询：**如果需要执行涉及多个分表的查询，可以使用联合查询（UNION）或者连接查询（JOIN）来合并结果。将查询条件应用到对应的分表，然后将结果联合起来返回给用户。
2. **扫描所有分表：**如果查询涉及到的数据无法通过分片键进行过滤，那么可能需要扫描所有的分表来获取满足条件的数据。这样的查询会比较慢，因为需要访问所有的分表并合并结果，但在某些场景下是必要的。
3. **手动分页和排序：**如果需要对分表后的数据进行排序和分页，可以在每个分表上执行独立的排序和分页操作，然后将结果合并或者按需返回给用户。这需要在应用程序中进行额外的逻辑处理。
4. **使用全局索引：**如果有一些特定的查询需要在非分片键上执行，并且这些查询非常频繁，可以考虑创建全局索引。全局索引不关心分片键，而是在整个集群上创建索引，可以加速这类查询的执行速度。


# Undolog是如何回滚事务的

在数据库中，**Undo Log通常用于实现事务的回滚操作**。当事务执行更新操作时，数据库会将相应的旧数据记录在Undo Log中，用于回滚事务时还原到事务开始前的状态。以下是Undo Log回滚事务的一般步骤：

**首先，**获取事务的回滚指针或Undo Log的起始位置。

从Undo Log的末尾开始逆向扫描，按照事务操作的逆序依次处理每个日志记录。

**然后，**针对 INSERT 操作，执行 DELETE 操作来撤销插入的数据。对于 UPDATE 操作，使用Undo Log 中记录的旧值将数据还原到之前的状态。

在回滚过程中，对于已经提交的其他事务所做的修改需要跳过，只处理属于当前回滚事务的 Undo Log 记录。

按照逆序依次处理所有的日志记录，直到达到回滚指针位置或 Undo Log 的起始位置。

**回滚完成后，**清除或标记已回滚的 Undo Log 记录。

总体而言，事务回滚是通过执行 Undo Log 中记录的反向操作，将事务的修改操作撤销，恢复到事务开始前的状态。


# 了解MySQL锁升级吗

**MySQL锁升级是指在并发事务执行过程中，当某个事务无法满足当前所需的锁级别时，系统会自动将该事务的锁级别升级为更高级别的锁。**

通常情况下，MySQL 会根据事务的需求和操作的对象**自动选择**合适的锁级别。然而，在某些情况下，事务无法获取到所需的锁级别，就会触发锁升级。

例如以下两种常见的锁升级场景：

1. 当某个事务需要获取的是行级锁，但由于并发冲突或其他原因无法满足事务的要求时，系统会将该事务的锁级别升级为表级锁，从而保证数据的一致性和并发性能。
2. 当某个事务操作的对象不符合行锁加锁规则，比如没有走索引或非唯一索引记录数达到一定数量，系统也会将该事务的锁级别升级为表级锁，以确保数据的完整性和一致性。

所以在实际应用时，合理的索引设计、适当的事务隔离级别设置可以帮助减少锁升级的发生，从而提高并发性能和系统吞吐量。


# MySQL索引分类_

在MySQL中，索引按照索引列的类型可以分为以下几种：

+ **主键索引：**用于唯一标识每一条记录，主键索引的值不允许重复且不能为空，并且一个表只能有一个主键索引。
+ **唯一索引：**用于保证索引列的值唯一，允许为空值，但是一个表可以有多个唯一索引。
+ **普通索引：**没有唯一性限制，允许重复值和空值，是最基本的索引类型。
+ **组合索引：**在多个字段上创建的索引，可以包含多个列。组合索引可以提高多列查询的性能，但查询条件必须符合最左前缀原则，即查询从左到右使用组合索引中的列。

以上就是MySQL常见的四种索引，这些不同类型的索引在数据库中起到了加速数据检索操作的作用，可以根据具体的需求和使用场景选择适当的索引类型。同时，需要注意索引的创建对写操作（如插入、更新、删除）可能会产生额外的开销，因此需要权衡索引的使用与数据操作的平衡。


# 如何快速定位慢SQL

要查询慢SQL产生的原因，可以采取以下4个步骤：

1. **启用慢查询日志：**在MySQL配置中启用慢查询日志，这样可以记录执行时间超过阈值的查询语句。通过分析慢查询日志，可以找到执行时间较长的SQL语句。
2. **使用EXPLAIN分析执行计划：**对于慢查询的SQL语句，使用EXPLAIN命令来查看其执行计划。通过分析执行计划，确定查询是否有效利用了索引以及是否存在性能瓶颈。
3. **检查索引使用情况：**确保查询中涉及的列都有适当的索引，并且查询条件能够充分利用索引。可以使用SHOW INDEX命令或查询表的索引信息来检查索引情况。
4. **分析查询语句：**仔细分析查询语句本身，检查是否存在冗余的操作、重复的子查询、不必要的排序、大量的JOIN操作等。

通过这些步骤的分析，找出慢查询产生的原因，并针对性地进行优化和调整，来提升查询性能。


# UNION与UNIONALL的区别？

UNION和UNION ALL是在SQL中用于合并查询结果集的操作符，它们之间存在以下区别：

1. **UNION：**UNION用于合并两个或多个查询结果集，并去除重复的行。它将多个查询的结果**合并为一个结果集，并自动去除重复的行。**在执行UNION操作时，数据库会进行额外的去重操作，这可能会带来一定的性能开销。
2. **UNION ALL：**UNION ALL同样**用于合并查询结果集，但不去除重复的行。**它将多个查询的结果简单地合并在一起，包括重复的行。相比于UNION，UNION ALL不进行去重操作，因此执行效率更高。

**总结来说：**在使用时，可以根据具体的需求来选择合适的操作符。如果需要去除重复的行，可以使用UNION；如果不需要去重，或者对性能要求较高，可以使用UNION ALL。需要注意的是，使用UNION或UNION ALL时，要求被合并的查询结果的列数和列类型保持一致。


# 事务的隔离级别有哪些

MySQL支持以下四个事务隔离级别：

1. **读未提交**：最低的隔离级别。事务可以读取到其他事务尚未提交的数据，可能会出现脏读、不可重复读和幻读问题。
2. **读已提交**：事务只能读取到已经提交的数据。但在同一事务中，多次读取同一行的数据结果可能会不一致，可能会出现不可重复读和幻读问题。
3. **可重复读**：在同一个事务内，多次读取同一行的数据结果始终保持一致。MySQL的**默认隔离级别就是可重复读**。通过使用MVCC机制来实现，在读操作期间不会看到其他事务的修改，有效地解决了不可重复读问题。
4. **串行化**：最高的隔离级别。事务串行执行，避免了脏读、不可重复读和幻读等问题。但是并发性能较差，可能导致大量的锁竞争和资源争用。


# MySQL有哪些高可用方案

MySQL的高可用方案主要有以下几种：

1. **主从复制：**这是最常见的高可用方案。主库负责处理写操作，并将数据变更记录到binlog日志。从库将主库的binlog复制到自己的中继日志，然后执行中继日志中的事件，以达到与主库数据一致的目的。当主库出现故障时，可以将从库提升为新的主库，实现服务的高可用。
2. **集群：**MySQL集群是一个高可用、高性能的数据库集群解决方案。它使用了共享无关的架构，可以在节点之间自动分割和复制数据，实现了数据的高可用和高性能。


# CHAR和VARCHAR的区别？

CHAR和VARCHAR的区别可以总结如下：

1. **存储方式：**CHAR是固定长度的字符类型，而VARCHAR是可变长度的字符类型。
2. **占用空间：**CHAR会以固定的长度存储数据，不论实际存储的字符数目，而VARCHAR则根据实际需要的空间动态分配存储。
3. **尾随空格：**CHAR在存储时会用空格填充到指定长度，并在检索时需要删除尾随空格，而VARCHAR没有这个问题。
4. **长度限制：**CHAR的长度范围为1到255个字符，而VARCHAR的长度范围也是255个字符，但可以根据需求设定更长的长度。
5. **访问效率：**由于CHAR是固定长度的，它在某些情况下可能会比VARCHAR稍微快一些。

综上所述，CHAR适合存储长度固定且固定大小的数据，而VARCHAR适用于长度可变的数据。


# 什么数据用hash存储

在诸葛老师的公开课中就讲到了， hash结构不支持范围查询，  所以哈希索引只能做等于查找，但是无论多大的Hash表，查找复杂度都是O(1)。

![1724316517627-4bbb90be-7297-48a4-8409-bb21e1ea1862.png](images/1724316517627-4bbb90be-7297-48a4-8409-bb21e1ea1862.png)

## 为什么范围不行：

* 哈希算法将输入映射到一个固定大小的哈希值，不同的输入可能会产生相同的哈希值（哈希碰撞）。因此，哈希表并不保留输入数据的顺序，这使得进行范围查询（如`BETWEEN`、`>`、`<`等）变得非常困难。

