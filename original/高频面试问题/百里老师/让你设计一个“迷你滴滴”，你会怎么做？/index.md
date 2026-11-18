# 让你设计一个“迷你滴滴”，你会怎么做？

<font style="color:rgb(38, 38, 38);">在系统设计（System Design）面试中，“设计一个打车软件”是出现频率极高的题目。它不仅考察候选人对高并发的理解，还涉及地理位置服务（LBS）、实时消息推送、分布式锁等多个硬核技术点。</font>

![1765095786709-74dcccaf-1035-4df7-9b18-68ee44aef432.png](./img/BWptV-CPt_IGvgYU/1765095786709-74dcccaf-1035-4df7-9b18-68ee44aef432-715076.png)

<font style="color:rgb(38, 38, 38);">本文将剥离细枝末节，从上帝视角带你拆解一个“迷你滴滴”的核心架构演进。</font>

***

### <font style="color:rgb(38, 38, 38);">1. 宏观视角：领域驱动设计</font>

![1765095797783-e8000d5f-006a-43ca-9042-90cda8f49afe.png](./img/BWptV-CPt_IGvgYU/1765095797783-e8000d5f-006a-43ca-9042-90cda8f49afe-252605.png)

<font style="color:rgb(38, 38, 38);">在动手写代码前，首先要进行业务领域的拆解。</font>

<font style="color:rgb(38, 38, 38);">不同于传统的电商系统，打车业务的核心在于\*\*“动态调度”</font>**<font style="color:rgb(38, 38, 38);">。如上图所示，我们将系统拆分为六边形架构，其中</font>**<font style="color:rgb(38, 38, 38);">“调度大脑”\*\*处于绝对的核心位置。</font>

* **<font style="color:rgb(38, 38, 38);">解耦设计的必要性</font>**<font style="color:rgb(38, 38, 38);">：我们将“订单”、“支付”、“消息”拆分为独立微服务。这样做的好处是，即使“支付服务”短暂宕机，用户依然可以下单、司机依然可以接单，实现了故障隔离。</font>
* **<font style="color:rgb(38, 38, 38);">核心链路</font>**<font style="color:rgb(38, 38, 38);">：用户发单 -> 调度大脑计算 -> 锁定司机 -> 消息触达。这个链路必须保证极高的可用性。</font>

***

### <font style="color:rgb(38, 38, 38);">2. 流量漏斗：分层架构落地</font>

![1765095808269-eff547b6-8da1-4e86-9549-10bfe1658344.png](./img/BWptV-CPt_IGvgYU/1765095808269-eff547b6-8da1-4e86-9549-10bfe1658344-737172.png)

<font style="color:rgb(38, 38, 38);">为了承载千万级的日活流量，我们需要一个清晰的分层架构来作为骨架。</font>

* **<font style="color:rgb(38, 38, 38);">接入层（Gateway）</font>**<font style="color:rgb(38, 38, 38);">：这是系统的“防盗门”。除了基本的路由转发，更重要的是在此处做</font>**<font style="color:rgb(38, 38, 38);">限流</font>**<font style="color:rgb(38, 38, 38);">和</font>**<font style="color:rgb(38, 38, 38);">鉴权</font>**<font style="color:rgb(38, 38, 38);">。在早晚高峰期，通过网关层的令牌桶算法，可以有效拦截恶意流量，保护后端服务不被压垮。</font>
* **<font style="color:rgb(38, 38, 38);">基础层与业务层分离</font>**<font style="color:rgb(38, 38, 38);">：我们将通用的能力（如 LBS 计算、Netty 推送）下沉为基础服务（Infra Layer）。上层的业务逻辑（如拼车、专车、快车）只需调用基础层的接口，无需关心底层的复杂实现，极大地提升了研发效率。</font>

***

### <font style="color:rgb(38, 38, 38);">3. LBS 引擎：如何从百万司机中秒级圈人？</font>

![1765095824953-a692a9af-529e-487a-9a1e-982ea20d369a.png](./img/BWptV-CPt_IGvgYU/1765095824953-a692a9af-529e-487a-9a1e-982ea20d369a-502734.png)

<font style="color:rgb(38, 38, 38);">这是整个系统最硬核的技术难点：</font>**<font style="color:rgb(38, 38, 38);">如何高效地存储和查询地理位置？</font>**

<font style="color:rgb(38, 38, 38);">如果在 MySQL 中使用 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">WHERE latitude > ? AND longitude < ?</font></code><font style="color:rgb(38, 38, 38);"> 进行范围查询，在数据量达到百万级时，索引效率会急剧下降，导致数据库崩溃。</font>

**<font style="color:rgb(38, 38, 38);">解决方案：Redis GEO</font>**<font style="color:rgb(38, 38, 38);"> 我们利用 Redis 的 GEO 模块（底层基于 GeoHash 算法）：</font>

1. **<font style="color:rgb(38, 38, 38);">降维打击</font>**<font style="color:rgb(38, 38, 38);">：GeoHash 将二维的经纬度映射为一维的 52 位整数。</font>
2. **<font style="color:rgb(38, 38, 38);">高效检索</font>**<font style="color:rgb(38, 38, 38);">：利用 ZSET（有序集合）存储，通过</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">GEORADIUS</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">命令，系统可以在 $O(\log N)$ 的时间复杂度内，瞬间计算出乘客附近 3km 内的所有司机，并按距离排序。</font>

***

### <font style="color:rgb(38, 38, 38);">4. 并发挑战：防止订单超卖与撞单</font>

![1765095837201-9abd7aad-b728-45b0-8313-efba916a0724.png](./img/BWptV-CPt_IGvgYU/1765095837201-9abd7aad-b728-45b0-8313-efba916a0724-582280.png)

<font style="color:rgb(38, 38, 38);">在“派单模式”或“抢单模式”下，同一个订单可能会被推给多个司机。如果两个司机在同一毫秒点击“抢单”，如何保证数据一致性？</font>

<font style="color:rgb(38, 38, 38);">这里必须引入</font>**<font style="color:rgb(38, 38, 38);">分布式锁</font>**<font style="color:rgb(38, 38, 38);">机制。</font>

* **<font style="color:rgb(38, 38, 38);">互斥性</font>**<font style="color:rgb(38, 38, 38);">：利用 Redis 的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SETNX</font></code><font style="color:rgb(38, 38, 38);">（Set if Not Exists）特性。只有第一个成功写入 Key 的请求才算抢锁成功，后续请求直接驳回。</font>
* **<font style="color:rgb(38, 38, 38);">死锁兜底</font>**<font style="color:rgb(38, 38, 38);">：必须为锁设置 TTL（过期时间）。防止某个服务节点在持有锁的状态下宕机，导致锁永远无法释放，后续业务卡死。</font>

***

### <font style="color:rgb(38, 38, 38);">5. 实时触达：Netty 长连接通道</font>

![1765095846526-9b6d8d1f-dbda-4e4a-ab35-979d71a791d0.png](./img/BWptV-CPt_IGvgYU/1765095846526-9b6d8d1f-dbda-4e4a-ab35-979d71a791d0-661162.png)

<font style="color:rgb(38, 38, 38);">抢单成功后，系统需要立刻通知司机。传统的 HTTP 轮询（Polling）方式延迟高且浪费服务器资源，无法满足打车场景对“实时性”的苛刻要求。</font>

**<font style="color:rgb(38, 38, 38);">解决方案：WebSocket + Netty</font>**<font style="color:rgb(38, 38, 38);"> 我们需要在司机端 App 与服务端之间建立一条全双工的</font>**<font style="color:rgb(38, 38, 38);">长连接</font>**<font style="color:rgb(38, 38, 38);">。</font>

* **<font style="color:rgb(38, 38, 38);">IO模型</font>**<font style="color:rgb(38, 38, 38);">：采用 Netty 的 NIO（非阻塞 IO）模型，配合 Epoll 机，单机即可轻松支撑 10w+ 的在线连接。</font>
* **<font style="color:rgb(38, 38, 38);">协议优化</font>**<font style="color:rgb(38, 38, 38);">：在传输层使用 Protobuf 替代 JSON，大幅减少数据包体积，降低网络带宽消耗，提升弱网环境下的送达率。</font>

***

### <font style="color:rgb(38, 38, 38);">6. 数据治理：冷热分离策略</font>

![1765095856036-fabacfc8-9af9-4b79-941a-efb812531033.png](./img/BWptV-CPt_IGvgYU/1765095856036-fabacfc8-9af9-4b79-941a-efb812531033-766614.png)

<font style="color:rgb(38, 38, 38);">随着业务发展，订单表和轨迹表的数据量会呈指数级增长。单表超过 2000 万行后，MySQL 的性能会显著下降。</font>

<font style="color:rgb(38, 38, 38);">我们采用</font>**<font style="color:rgb(38, 38, 38);">冷热分离</font>**<font style="color:rgb(38, 38, 38);">的存储策略：</font>

* **<font style="color:rgb(38, 38, 38);">热数据（MySQL）</font>**<font style="color:rgb(38, 38, 38);">：最近 3 个月的订单，用户查询频率高，需要事务支持，继续留在 MySQL 中，并配合 ShardingSphere 进行分库分表。</font>
* **<font style="color:rgb(38, 38, 38);">冷数据（HBase/TiDB）</font>**<font style="color:rgb(38, 38, 38);">：3 个月前的历史订单，查询频率极低。通过 DataX 定时任务迁移至成本更低、扩展性更强的 NoSQL 数据库中归档。</font>
* **<font style="color:rgb(38, 38, 38);">轨迹数据（MongoDB）</font>**<font style="color:rgb(38, 38, 38);">：一次行程包含数百个坐标点，写多读少，且无强事务需求，MongoDB 的 Sharded Cluster 是最佳归宿。</font>

***

### <font style="color:rgb(38, 38, 38);">7. 总结</font>

![1765095865021-95675145-151b-4829-a003-f69daa2edddb.png](./img/BWptV-CPt_IGvgYU/1765095865021-95675145-151b-4829-a003-f69daa2edddb-687699.png)

<font style="color:rgb(38, 38, 38);">设计一个迷你滴滴，本质上是在做</font>**<font style="color:rgb(38, 38, 38);">空间换时间</font>**<font style="color:rgb(38, 38, 38);">与</font>**<font style="color:rgb(38, 38, 38);">分层治理</font>**<font style="color:rgb(38, 38, 38);">的权衡。</font>

1. **<font style="color:rgb(38, 38, 38);">Redis GEO</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">解决了空间搜索的效率问题。</font>
2. **<font style="color:rgb(38, 38, 38);">Netty 长连接</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">解决了实时通信的延迟问题。</font>
3. **<font style="color:rgb(38, 38, 38);">分布式锁</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">解决了高并发下的资源竞争问题。</font>
4. **<font style="color:rgb(38, 38, 38);">冷热分离</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">解决了海量数据的存储成本问题。</font>

<font style="color:rgb(38, 38, 38);">掌握这套架构组合拳，足以应对大多数 LBS 类应用的系统设计挑战。</font>
