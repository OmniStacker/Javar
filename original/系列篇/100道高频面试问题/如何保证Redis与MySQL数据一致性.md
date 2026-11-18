# 如何保证Redis与MySQL数据一致性

[bilibili](https://player.bilibili.com/player.html?bvid=BV1FG411Z7Wk\&autoplay=0)

### <font style="color:rgba(6, 8, 31, 0.88);">1. 面试官的出发点（Why they ask this?）</font>

<font style="color:rgba(6, 8, 31, 0.88);">面试官通过这个问题，主要想考察你以下几点能力：</font>

* **<font style="color:rgba(6, 8, 31, 0.88);">系统设计能力</font>**<font style="color:rgba(6, 8, 31, 0.88);">：你是否理解在高并发场景下，缓存和数据库协同工作的重要性？这不仅仅是一个技术问题，更是一个架构设计问题。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">知识广度与深度</font>**<font style="color:rgba(6, 8, 31, 0.88);">：你是否知道至少2-3种解决方案？你是否能深入分析每种方案的实现细节，以及它们在特定场景下的优缺点？</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">权衡与取舍（Trade-off）</font>**<font style="color:rgba(6, 8, 31, 0.88);">：没有银弹。你是否明白每种方案都有其适用场景，并且能在性能、一致性、开发成本之间做出合理的选择？这体现了你的架构决策能力。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">实际经验</font>**<font style="color:rgba(6, 8, 31, 0.88);">：你是否在项目中真正处理过类似问题？你能否结合实际业务场景（比如：是强一致性要求的金融场景，还是最终一致性可接受的电商场景）来阐述你的选择？</font>

***

### <font style="color:rgba(6, 8, 31, 0.88);">2. 所有主流方案及其优劣对比</font>

<font style="color:rgba(6, 8, 31, 0.88);">核心问题在于：</font>**<font style="color:rgba(6, 8, 31, 0.88);">更新操作时，是先操作数据库还是先操作缓存？</font>**<font style="color:rgba(6, 8, 31, 0.88);"> </font><font style="color:rgba(6, 8, 31, 0.88);">由此衍生出几种主流模式。</font>

<font style="color:rgba(6, 8, 31, 0.88);">我们通常使用\*\*缓存淘汰（Cache-Aside Pattern）\*\*策略，即读操作时，缓存没有就从数据库读并加载到缓存；写操作时，更新数据库，并让缓存失效。</font>

<font style="color:rgba(6, 8, 31, 0.88);">关键点在于</font>**<font style="color:rgba(6, 8, 31, 0.88);">写操作</font>**<font style="color:rgba(6, 8, 31, 0.88);">，这里有几种方案：</font>

#### <font style="color:rgba(6, 8, 31, 0.88);">方案一：先更新数据库，再删除缓存 (Cache-Aside)</font>

<font style="color:rgba(6, 8, 31, 0.88);">这是最经典、最常用的方案。</font>

* **<font style="color:rgba(6, 8, 31, 0.88);">流程</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  1. <font style="color:rgba(6, 8, 31, 0.88);">更新数据库中的数据。</font>
  2. <font style="color:rgba(6, 8, 31, 0.88);">删除Redis中的缓存。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">优点</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  * <font style="color:rgba(6, 8, 31, 0.88);">操作简单，符合逻辑。</font>
  * <font style="color:rgba(6, 8, 31, 0.88);">当第二步删除缓存失败时，数据库中是新数据，缓存中是旧数据，虽然有短期不一致，但下次缓存过期或被动淘汰后，能重新加载新数据，系统有“自我修复”能力。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">缺点</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">高并发下的问题</font>**<font style="color:rgba(6, 8, 31, 0.88);">：假设线程A更新数据库，线程B在A更新完数据库但还未删除缓存时读取数据，B会读到旧缓存。然后B去更新数据库（可能基于旧值），A再删除缓存。这在高并发读写混合场景下可能发生。但更常见的问题是</font>**<font style="color:rgba(6, 8, 31, 0.88);">读写并发</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
    1. <font style="color:rgba(6, 8, 31, 0.88);">线程A发起读请求，发现缓存为空。</font>
    2. <font style="color:rgba(6, 8, 31, 0.88);">线程A去数据库读取旧值。</font>
    3. <font style="color:rgba(6, 8, 31, 0.88);">线程B发起写请求，更新了数据库，并删除了缓存。</font>
    4. <font style="color:rgba(6, 8, 31, 0.88);">线程A将刚刚从数据库读到的旧值写入了缓存。\ </font><font style="color:rgba(6, 8, 31, 0.88);">此时，数据库是新值，缓存是旧值，产生数据不一致。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">应对策略</font>**<font style="color:rgba(6, 8, 31, 0.88);">：这种读写并发的概率极低，因为它要求在写操作（更新DB+删缓存）的极短时间内，发生一次缓存失效+读DB+回写缓存的操作。但如果业务对一致性要求极高，就需要引入更复杂的方案。</font>

#### <font style="color:rgba(6, 8, 31, 0.88);">方案二：延时双删策略 (方案一的变种)</font>

<font style="color:rgba(6, 8, 31, 0.88);">为了解决方案一中的读写并发问题。</font>

* **<font style="color:rgba(6, 8, 31, 0.88);">流程</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  1. <font style="color:rgba(6, 8, 31, 0.88);">先删除缓存。</font>
  2. <font style="color:rgba(6, 8, 31, 0.88);">再更新数据库。</font>
  3. <font style="color:rgba(6, 8, 31, 0.88);">延迟N秒后，再次删除缓存。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">优点</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  * <font style="color:rgba(6, 8, 31, 0.88);">通过第二次删除，可以大概率清除掉在更新过程中产生的脏数据。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">缺点</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">“延迟N秒”的N很难确定</font>**<font style="color:rgba(6, 8, 31, 0.88);">：N要大于一次读操作+回写缓存的时间。在复杂的网络和系统负载下，这个时间无法精确评估。</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">降低了吞吐量</font>**<font style="color:rgba(6, 8, 31, 0.88);">：引入了</font><code><font style="color:rgba(6, 8, 31, 0.88);background-color:rgba(175, 184, 193, 0.2);">sleep</font></code><font style="color:rgba(6, 8, 31, 0.88);">等待，应用的性能会受影响。</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">非原子性</font>**<font style="color:rgba(6, 8, 31, 0.88);">：如果第二次删除失败，依然会数据不一致。</font>

**<font style="color:rgb(87, 96, 106);">小结</font>**<font style="color:rgb(87, 96, 106);">：由于“先删缓存再更新数据库”问题更大（如果更新数据库失败，缓存被删了，将永久不一致），所以业界普遍采用“先更新数据库，再删除缓存”。而“延时双删”作为补充，实现复杂且有性能损耗，并非首选。</font>

#### <font style="color:rgba(6, 8, 31, 0.88);">方案三：基于消息队列（MQ）的异步通知</font>

<font style="color:rgba(6, 8, 31, 0.88);">这是一种实现最终一致性的经典方案，将缓存操作与业务逻辑解耦。</font>

* **<font style="color:rgba(6, 8, 31, 0.88);">流程</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  1. <font style="color:rgba(6, 8, 31, 0.88);">应用更新数据库。</font>
  2. <font style="color:rgba(6, 8, 31, 0.88);">应用向消息队列（如RabbitMQ、Kafka）发送一条“数据已更新”的消息（可以携带数据ID）。</font>
  3. <font style="color:rgba(6, 8, 31, 0.88);">一个专门的消费者服务订阅该消息。</font>
  4. <font style="color:rgba(6, 8, 31, 0.88);">消费者收到消息后，去执行删除缓存的操作。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">优点</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">高吞吐量和解耦</font>**<font style="color:rgba(6, 8, 31, 0.88);">：应用主流程执行速度快，无需等待缓存操作。</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">高可靠性</font>**<font style="color:rgba(6, 8, 31, 0.88);">：即使消费者服务宕机或缓存删除失败，消息队列的重试机制（ACK）能保证消息最终被消费，从而保证了最终一致性。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">缺点</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">架构更复杂</font>**<font style="color:rgba(6, 8, 31, 0.88);">：引入了消息队列中间件，增加了系统的维护成本。</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">最终一致性</font>**<font style="color:rgba(6, 8, 31, 0.88);">：从数据库更新到缓存删除，存在毫秒级到秒级的延迟。对于无法容忍短暂不一致的业务场景（如银行余额）不适用。</font>

#### <font style="color:rgba(6, 8, 31, 0.88);">方案四：基于订阅数据库Binlog的异步方案 (Alibaba Canal)</font>

<font style="color:rgba(6, 8, 31, 0.88);">这是方案三的终极进化版，实现了对应用代码的零侵入。</font>

* **<font style="color:rgba(6, 8, 31, 0.88);">流程</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  1. <font style="color:rgba(6, 8, 31, 0.88);">应用只管更新数据库。</font>
  2. <font style="color:rgba(6, 8, 31, 0.88);">一个名为Canal的中间件（或其他类似工具）伪装成MySQL的从库，订阅主库的binlog（二进制日志）。</font>
  3. <font style="color:rgba(6, 8, 31, 0.88);">当Canal监听到数据库有数据变更（insert, update, delete）时，它会抓取这些变更。</font>
  4. <font style="color:rgba(6, 8, 31, 0.88);">Canal将这些变更消息投递到消息队列，或者由一个服务直接消费Canal的数据。</font>
  5. <font style="color:rgba(6, 8, 31, 0.88);">消费服务根据数据变更的类型和ID，精确地更新或删除Redis缓存。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">优点</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">对应用零侵入</font>**<font style="color:rgba(6, 8, 31, 0.88);">：业务代码完全不需要关心缓存和数据库的一致性问题，只操作数据库即可。</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">极高的可靠性和解耦</font>**<font style="color:rgba(6, 8, 31, 0.88);">：逻辑完全下沉到基础架构层，是目前业界最优雅的方案之一。</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">通用性强</font>**<font style="color:rgba(6, 8, 31, 0.88);">：任何业务对数据库的修改都能被捕捉到，统一处理。</font>
* **<font style="color:rgba(6, 8, 31, 0.88);">缺点</font>**<font style="color:rgba(6, 8, 31, 0.88);">：</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">架构最复杂</font>**<font style="color:rgba(6, 8, 31, 0.88);">：需要部署和维护Canal集群以及相关的消费服务，技术门槛和运维成本最高。</font>
  * **<font style="color:rgba(6, 8, 31, 0.88);">最终一致性</font>**<font style="color:rgba(6, 8, 31, 0.88);">：同样存在延迟，延迟程度取决于整个链路的处理速度。</font>

<font style="color:rgba(6, 8, 31, 0.88);"></font>
