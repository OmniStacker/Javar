# Oracle知识汇总

## 目录

1. [Oracle概述](#1-oracle概述)
2. [共享池（Shared Pool）](#2-共享池shared-pool)
3. [并行查询（Parallel Query）](#3-并行查询parallel-query)
4. [REF CURSOR处理](#4-ref-cursor处理)

---

## 1. Oracle概述

Oracle是关系型数据库管理系统（RDBMS），广泛应用于企业级应用。

---

## 2. 共享池（Shared Pool）

### 2.1 什么是共享池？

**共享池**是Oracle SGA（System Global Area）的重要组成部分，用于缓存：
- SQL语句的解析结果（库缓存）
- 数据字典信息（字典缓存）

### 2.2 共享池的作用

1. **减少硬解析**：缓存SQL执行计划，避免重复解析
2. **提高性能**：快速访问数据字典信息
3. **降低CPU消耗**：减少SQL解析开销

### 2.3 共享池管理

- 使用LRU算法管理
- 通过SHARED_POOL_SIZE参数设置大小
- 监控共享池命中率

---

## 3. 并行查询（Parallel Query）

### 3.1 什么是并行查询？

**并行查询**是Oracle的并行执行机制，将一个查询任务分解为多个子任务，由多个进程并行执行。

### 3.2 并行查询机制

**工作原理**：
1. 查询分解为多个子任务
2. 多个进程并行执行
3. 结果汇总返回

**适用场景**：
- 大数据量查询
- 全表扫描
- 聚合操作

### 3.3 并行查询配置

```sql
-- 启用并行查询
ALTER SESSION ENABLE PARALLEL QUERY;

-- 指定并行度
SELECT /*+ PARALLEL(table_name, 4) */ * FROM table_name;
```

---

## 4. REF CURSOR处理

### 4.1 什么是REF CURSOR？

**REF CURSOR**是Oracle的引用游标类型，用于在Java中处理存储过程返回的游标结果集。

### 4.2 Java中处理REF CURSOR

**使用CallableStatement**：
```java
CallableStatement cs = connection.prepareCall("{call my_proc(?)}");
cs.registerOutParameter(1, OracleTypes.CURSOR);
cs.execute();
ResultSet rs = (ResultSet) cs.getObject(1);
```

**使用Spring JDBC**：
```java
jdbcTemplate.execute("{call my_proc(?)}", 
    new CallableStatementCallback() {
        public Object doInCallableStatement(CallableStatement cs) {
            cs.registerOutParameter(1, OracleTypes.CURSOR);
            cs.execute();
            ResultSet rs = (ResultSet) cs.getObject(1);
            // 处理结果集
            return rs;
        }
    });
```

---

## 总结

本文档汇总了Oracle的核心知识点：

1. **共享池**：SQL缓存、数据字典缓存、性能优化
2. **并行查询**：并行执行机制、适用场景、配置方法
3. **REF CURSOR**：引用游标、Java处理方法

通过本文档，可以了解Oracle的核心概念和Java处理方法。