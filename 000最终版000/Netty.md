# Netty知识汇总

## 目录

1. [Netty概述](#1-netty概述)
2. [Reactor线程模型](#2-reactor线程模型)
3. [零拷贝机制](#3-零拷贝机制)
4. [内存管理](#4-内存管理)
5. [无锁化设计](#5-无锁化设计)
6. [粘包与拆包](#6-粘包与拆包)
7. [心跳与闲置连接](#7-心跳与闲置连接)
8. [性能调优](#8-性能调优)

---

## 1. Netty概述

### 1.1 Netty为何是Java网络编程的性能之王？

Netty在高性能方面的五大核心优化：

1. **IO模型**：NIO + Reactor模式
2. **内存层**：Zero-Copy + Direct Memory
3. **分配层**：Jemalloc + 对象池
4. **线程层**：串行化设计 + 无锁编程
5. **微观层**：FastThreadLocal + 字节码优化

### 1.2 Netty的应用场景

- Dubbo、RocketMQ、Zookeeper底层通信
- 高性能网络应用开发
- 即时通讯系统
- 游戏服务器
- 物联网通信

---

## 2. Reactor线程模型

### 2.1 传统BIO的痛点

- 每个连接需要一个独立线程
- 连接数达到数万时，线程上下文切换开销耗尽CPU

### 2.2 Netty的Reactor模式

**主从Reactor多线程模型**：

- **BossGroup (Main Reactor)**：
  - 处理OP_ACCEPT事件（连接请求）
  - 连接建立后注册到WorkerGroup

- **WorkerGroup (Sub Reactor)**：
  - 处理OP_READ/OP_WRITE事件
  - 每个Worker线程绑定一个Selector
  - 通过EventLoop轮询管理连接

**性能优势**：
- 极少的线程数（CPU核心数×2）
- 非阻塞I/O，CPU利用率高
- 轻松应对百万级并发

---

## 3. 零拷贝机制

### 3.1 操作系统层面的零拷贝

**FileRegion + transferTo**：
- 传统方式：硬盘 -> 内核缓冲 -> 用户缓冲 -> 内核Socket缓冲 -> 网卡（4次拷贝）
- Netty方式：硬盘 -> 内核缓冲 -> 网卡（数据不经过JVM内存）

### 3.2 应用层面的零拷贝

**CompositeByteBuf**：
- 逻辑上组合多个Buffer
- 物理上不发生字节复制
- 适用于Header + Body场景

### 3.3 Direct Memory

- 默认使用DirectByteBuf
- 在堆外（Native Memory）分配内存
- 省去堆内存到堆外的拷贝

---

## 4. 内存管理

### 4.1 内存池化

**PooledByteBufAllocator**：
- 参考Jemalloc内存分配算法
- 预先申请大块内存（Arena/Chunk）
- 切分成小块（Page/SubPage）按需分配
- 用完放回池中，等待复用

**优势**：
- 对象创建几乎无开销
- 减少内存碎片
- 降低GC压力

### 4.2 引用计数

- retain()：增加引用计数
- release()：减少引用计数
- 手动管理生命周期，确保内存及时回收

---

## 5. 无锁化设计

### 5.1 串行化执行设计

**设计哲学**：与其加锁，不如不共享

- 一个EventLoop内所有事件串行执行
- 处理同一个Channel的业务逻辑时天然线程安全
- 避免上下文切换和锁竞争

### 5.2 高性能数据结构

**FastThreadLocal**：
- 重新实现Java的ThreadLocal
- 使用数组下标索引，访问速度O(1)
- 无哈希冲突

**MpscQueue**：
- Multi-Producer Single-Consumer队列
- 针对多生产者-单消费者场景优化
- 性能远超LinkedBlockingQueue

---

## 6. 粘包与拆包

### 6.1 什么是粘包与拆包？

- **粘包**：多个数据包粘在一起
- **拆包**：一个数据包被拆成多个

### 6.2 Netty如何处理？

**解决方案**：
1. **固定长度拆包**：FixedLengthFrameDecoder
2. **分隔符拆包**：DelimiterBasedFrameDecoder
3. **长度字段拆包**：LengthFieldBasedFrameDecoder（推荐）

---

## 7. 心跳与闲置连接

### 7.1 Netty如何处理闲置连接？

**IdleStateHandler**：
- 检测读空闲、写空闲、读写空闲
- 触发IdleStateEvent事件
- 可以在事件中关闭连接或发送心跳

### 7.2 心跳机制实现

```java
// 添加IdleStateHandler
pipeline.addLast(new IdleStateHandler(0, 0, 60, TimeUnit.SECONDS));

// 处理心跳事件
pipeline.addLast(new MyHeartbeatHandler());
```

---

## 8. 性能调优

### 8.1 Netty线上如何做性能调优？

**系统层面**：
1. 增加文件描述符限制
2. 调整TCP参数
3. 开启TCP_NODELAY
4. 调整SO_RCVBUF/SO_SNDBUF

**JVM层面**：
1. 合理设置堆内存
2. 使用G1垃圾回收器
3. 调整Direct Memory大小
4. 减少GC频率

**Netty层面**：
1. 使用PooledByteBufAllocator
2. 调整EventLoopGroup线程数
3. 合理设置SO_BACKLOG
4. 使用Epoll（Linux）

### 8.2 ByteBuf与ByteBuffer相比的优势

| 特性 | ByteBuf | ByteBuffer |
|------|---------|------------|
| **容量** | 动态扩展 | 固定 |
| **读写指针** | 分离 | 共享 |
| **零拷贝** | 支持 | 不支持 |
| **内存池** | 支持 | 不支持 |
| **API友好** | 是 | 否 |

---

## 总结

本文档系统性地汇总了Netty的核心知识点，包括：

1. **Netty概述**：性能优势、应用场景
2. **Reactor线程模型**：主从Reactor、BossGroup、WorkerGroup
3. **零拷贝机制**：操作系统层面、应用层面、Direct Memory
4. **内存管理**：内存池化、引用计数
5. **无锁化设计**：串行化执行、FastThreadLocal、MpscQueue
6. **粘包与拆包**：解决方案
7. **心跳与闲置连接**：IdleStateHandler
8. **性能调优**：系统、JVM、Netty层面

通过本文档，可以系统性地掌握Netty的核心概念和性能优化方法。