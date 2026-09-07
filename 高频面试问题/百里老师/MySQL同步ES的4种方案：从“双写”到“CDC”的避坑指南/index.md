# MySQL 同步 ES 的 4种方案：从“双写”到“CDC”的避坑指南

<font style="color:rgb(38, 38, 38);">在微服务架构中，</font>**<font style="color:rgb(38, 38, 38);">“关系型数据库（MySQL）做存储，搜索引擎（Elasticsearch）做检索”</font>**<font style="color:rgb(38, 38, 38);"> 几乎是处理海量数据查询的标准范式。然而，如何保证两者之间的数据一致性，却是让无数架构师头秃的难题。</font>

![1766560621852-58140bbe-0f0a-40ac-9898-7b8b2a5fafc5.png](./img/uNT57LeKMPXsJYkU/1766560621852-58140bbe-0f0a-40ac-9898-7b8b2a5fafc5-418385.png)

<font style="color:rgb(38, 38, 38);">从早期的同步双写，到引入 MQ 解耦，再到如今主流的 CDC（Change Data Capture）方案，每一次架构演进的背后，都是对</font>**<font style="color:rgb(38, 38, 38);">性能、解耦</font>**<font style="color:rgb(38, 38, 38);">与</font>**<font style="color:rgb(38, 38, 38);">一致性</font>**<font style="color:rgb(38, 38, 38);">这三者之间平衡点的重新考量。</font>

<font style="color:rgb(38, 38, 38);">本文将结合生产环境的实战经验，拆解四种同步方案的优劣与演进路径。</font>

***

## <font style="color:rgb(38, 38, 38);">一、 初始阶段：同步双写的诱惑与代价</font>

<font style="color:rgb(38, 38, 38);">在项目初期，数据量不大，开发周期紧，很多团队会选择最直观的“同步双写”方案。即在业务代码的事务逻辑中，直接调用 ES 的 SDK 进行写入。</font>

![1766560634044-a6770146-ce5b-4926-9412-5c7b1ad7a76f.png](./img/uNT57LeKMPXsJYkU/1766560634044-a6770146-ce5b-4926-9412-5c7b1ad7a76f-909104.png)

### <font style="color:rgb(38, 38, 38);">1. 为什么它是“架构陷阱”？</font>

<font style="color:rgb(38, 38, 38);">看似简单的代码背后，隐藏着两个致命的系统性风险：</font>

* **<font style="color:rgb(38, 38, 38);">性能雪崩风险（Performance Critical）</font>**<font style="color:rgb(38, 38, 38);">： MySQL 的事务性能是极其宝贵的资源。如果在事务作用域内插入了 ES 的网络 I/O 操作，一旦 ES 集群发生 Full GC 卡顿或网络抖动，会导致 MySQL 的事务提交被阻塞。 这就好比在高速公路上设了一个红绿灯，瞬间会导致数据库连接池耗尽，进而拖垮整个主业务系统。</font>
* **<font style="color:rgb(38, 38, 38);">分布式一致性死结</font>**<font style="color:rgb(38, 38, 38);">： 在没有引入重型分布式事务（如 XA/Seata）的前提下，双写无法保证原子性。</font>
  * <font style="color:rgb(38, 38, 38);">如果 MySQL 成功，ES 失败，你回滚吗？（业务明明成功了，回滚不合理）</font>
  * <font style="color:rgb(38, 38, 38);">如果不回滚，数据就不一致了。 这种方案在流量稍微增大后，几乎必然导致数据漂移。</font>

***

## <font style="color:rgb(38, 38, 38);">二、 过渡阶段：引入 MQ 进行异步解耦</font>

<font style="color:rgb(38, 38, 38);">为了解决“同步双写”带来的性能问题，引入消息队列（Kafka/RocketMQ）是自然的演进方向。主线程将变更事件写入 MQ 后立即返回，由消费者异步写入 ES。</font>

![1766560641847-c4ae4413-e162-4faa-a1e3-76bc504c2f08.png](./img/uNT57LeKMPXsJYkU/1766560641847-c4ae4413-e162-4faa-a1e3-76bc504c2f08-756845.png)

### <font style="color:rgb(38, 38, 38);">1. 性能提升与新的痛点</font>

<font style="color:rgb(38, 38, 38);">引入 MQ 后，接口响应时间（RT）确实会从几百毫秒骤降至几十毫秒，系统的吞吐量得到了显著提升。但这只是把问题转移了，并未根除：</font>

* **<font style="color:rgb(38, 38, 38);">代码侵入性（Intrusiveness）</font>**<font style="color:rgb(38, 38, 38);">： 正如上图代码所示，业务 Service 层依然不纯粹。开发人员在写</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">userMapper.insert</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的同时，必须时刻记得写一行</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">kafkaTemplate.send</font></code><font style="color:rgb(38, 38, 38);">。这种</font>**<font style="color:rgb(38, 38, 38);">逻辑耦合</font>**<font style="color:rgb(38, 38, 38);">导致业务代码难以维护，且容易遗漏。</font>
* **<font style="color:rgb(38, 38, 38);">“双写”问题的变种</font>**<font style="color:rgb(38, 38, 38);">： 我们只是把“双写 MySQL + ES”变成了“双写 MySQL + MQ”。如果数据库事务提交了，但 MQ 发送失败（例如网络闪断），数据依然会丢失。虽然可以通过“本地消息表”来保证可靠投递，但这又引入了额外的开发和运维成本。</font>

***

## <font style="color:rgb(38, 38, 38);">三、 成熟阶段：CDC 变更数据捕获</font>

<font style="color:rgb(38, 38, 38);">这是目前业界公认的“黄金标准”。CDC（Change Data Capture）技术的核心思想是：</font>**<font style="color:rgb(38, 38, 38);">不要让业务层感知同步逻辑，而是去监听数据库的“核心心跳”——Binlog。</font>**

![1766560649029-37b6e9bf-937e-46f2-8adf-f3ec2b07d1db.png](./img/uNT57LeKMPXsJYkU/1766560649029-37b6e9bf-937e-46f2-8adf-f3ec2b07d1db-811794.png)

### <font style="color:rgb(38, 38, 38);">1. 像“从库”一样思考</font>

<font style="color:rgb(38, 38, 38);">利用 Canal、Debezium 或 Flink CDC 等组件，将自己伪装成 MySQL 的 Slave 节点。MySQL 发生任何变更，都会通过 Binlog 协议实时推送给消费者。</font>

### <font style="color:rgb(38, 38, 38);">2. 核心优势</font>

* **<font style="color:rgb(38, 38, 38);">真正的零侵入（Zero Intrusion）</font>**<font style="color:rgb(38, 38, 38);">： 业务代码回归纯净（如上图代码所示），只关注数据库操作。同步逻辑与业务逻辑在物理上完全隔离，实现了关注点分离。</font>
* **<font style="color:rgb(38, 38, 38);">断点续传能力</font>**<font style="color:rgb(38, 38, 38);">： Binlog 拥有严格的顺序和位点（Position/Offset）。即使同步服务宕机，重启后依然可以从上次中断的位点继续消费，理论上保证了“至少一次（At Least Once）”的投递。</font>

***

## <font style="color:rgb(38, 38, 38);">四、 深度挑战：乱序与幂等性设计</font>

<font style="color:rgb(38, 38, 38);">选择了 CDC + MQ 的链路，就意味着选择了分布式系统的复杂性。其中最棘手的问题就是</font>**<font style="color:rgb(38, 38, 38);">消息乱序（Ordering）</font>**<font style="color:rgb(38, 38, 38);">。</font>

![1766560660491-1fba20ec-46a3-4ce8-a3cc-20df1b408528.png](./img/uNT57LeKMPXsJYkU/1766560660491-1fba20ec-46a3-4ce8-a3cc-20df1b408528-894461.png)

### <font style="color:rgb(38, 38, 38);">1. 场景复现</font>

<font style="color:rgb(38, 38, 38);">假设用户在极短时间内连续修改了两次数据：</font>

1. <code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">v1</font></code><font style="color:rgb(38, 38, 38);">: name = "Alice"</font>
2. <code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">v2</font></code><font style="color:rgb(38, 38, 38);">: name = "Bob"</font>

<font style="color:rgb(38, 38, 38);">在网络传输中，</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">v1</font></code><font style="color:rgb(38, 38, 38);"> 包可能因为路由拥塞迟到了，导致 ES 先收到了 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">v2</font></code><font style="color:rgb(38, 38, 38);">，后收到了 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">v1</font></code><font style="color:rgb(38, 38, 38);">。如果不做处理，ES 的数据最终会被覆盖为 "Alice"（旧数据），导致严重的数据回退。</font>

### <font style="color:rgb(38, 38, 38);">2. 解决方案：乐观锁与版本控制</font>

<font style="color:rgb(38, 38, 38);">解决乱序问题的核心在于</font>**<font style="color:rgb(38, 38, 38);">“只接受未来的数据”</font>**<font style="color:rgb(38, 38, 38);">。我们需要在 ES 文档中维护一个外部版本号字段（如 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">update_time</font></code><font style="color:rgb(38, 38, 38);"> 或 Binlog 的 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">offset</font></code><font style="color:rgb(38, 38, 38);">）。</font>

* **<font style="color:rgb(38, 38, 38);">写入前检查</font>**<font style="color:rgb(38, 38, 38);">：消费者在处理消息时，对比消息中的版本号与 ES 现有文档的版本号。</font>
* **<font style="color:rgb(38, 38, 38);">策略执行</font>**<font style="color:rgb(38, 38, 38);">：</font>
  * <font style="color:rgb(38, 38, 38);">如果</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">Msg.version > Doc.version</font></code><font style="color:rgb(38, 38, 38);">：执行更新（Upsert）。</font>
  * <font style="color:rgb(38, 38, 38);">如果</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">Msg.version <= Doc.version</font></code><font style="color:rgb(38, 38, 38);">：说明是过期数据，直接丢弃（Ack & Ignore）。</font>

***

## <font style="color:rgb(38, 38, 38);">五、 兜底防线：反熵（Anti-Entropy）机制</font>

<font style="color:rgb(38, 38, 38);">即便架构设计得再完美，也无法避免“黑天鹅”事件：Binlog 意外被清理、代码逻辑 Bug、人为误删数据等。因此，系统必须具备</font>**<font style="color:rgb(38, 38, 38);">自我修复能力</font>**<font style="color:rgb(38, 38, 38);">。</font>

![1766560667480-da1f821a-03dd-431e-abb7-29fa1f5241fd.png](./img/uNT57LeKMPXsJYkU/1766560667480-da1f821a-03dd-431e-abb7-29fa1f5241fd-489371.png)

### <font style="color:rgb(38, 38, 38);">1. T+1 全量比对</font>

<font style="color:rgb(38, 38, 38);">我们需要引入一个“反熵”机制（Anti-Entropy），通常是一个定时运行的批处理任务：</font>

* **<font style="color:rgb(38, 38, 38);">游标扫描</font>**<font style="color:rgb(38, 38, 38);">：利用主键 ID 或时间游标，分批次拉取 MySQL 和 ES 的数据。</font>
* **<font style="color:rgb(38, 38, 38);">高效比对</font>**<font style="color:rgb(38, 38, 38);">：不需要比对所有字段，通常比对</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">update_time</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">或关键字段的 Hash 值即可。</font>
* **<font style="color:rgb(38, 38, 38);">强制修复</font>**<font style="color:rgb(38, 38, 38);">：一旦发现不一致（如图中红色的异常数据），以 MySQL 为“Source of Truth”（唯一真理源），强制覆盖 ES 数据。</font>

<font style="color:rgb(38, 38, 38);">这道防线保证了系统在经历任何故障后，都能在 T+1 时间内回归一致，实现了</font>**<font style="color:rgb(38, 38, 38);">最终一致性</font>**<font style="color:rgb(38, 38, 38);">。</font>

***

## <font style="color:rgb(38, 38, 38);">六、 总结</font>

![1766560693327-667fe4ae-f6ee-47d3-afb3-1615cca3d512.png](./img/uNT57LeKMPXsJYkU/1766560693327-667fe4ae-f6ee-47d3-afb3-1615cca3d512-578182.png)

<font style="color:rgb(38, 38, 38);">构建一个生产级的高可靠同步架构，并非一蹴而就，而是一个不断做减法和加法的过程：</font>

1. **<font style="color:rgb(38, 38, 38);">做减法</font>**<font style="color:rgb(38, 38, 38);">：通过</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">CDC</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">去掉业务代码中的同步逻辑，实现解耦。</font>
2. **<font style="color:rgb(38, 38, 38);">做加法</font>**<font style="color:rgb(38, 38, 38);">：通过</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">版本控制</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">增加对乱序的处理能力。</font>
3. **<font style="color:rgb(38, 38, 38);">做保障</font>**<font style="color:rgb(38, 38, 38);">：通过</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">反熵机制</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">增加系统的容错底线。</font>

<font style="color:rgb(38, 38, 38);">最终，我们得到的是一个既具备</font>**<font style="color:rgb(38, 38, 38);">实时性（CDC+MQ）</font>**<font style="color:rgb(38, 38, 38);">，又具备</font>**<font style="color:rgb(38, 38, 38);">逻辑闭环（Version Control）</font>**<font style="color:rgb(38, 38, 38);">，且拥有</font>**<font style="color:rgb(38, 38, 38);">安全底线（Anti-Entropy）</font>**<font style="color:rgb(38, 38, 38);">的健壮架构。</font>


> 更新: 2025-12-24 19:31:36  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/gz0olxp5ikyu96p1>