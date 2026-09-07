# Redis 极限调优：如何在不扩容的情况下实现 QPS 翻倍？

## <font style="color:rgb(38, 38, 38);">1. 引言：从“资源堆砌”到“架构压榨”</font>

![1764159090128-d93df62f-a15b-430a-a37c-acd90fc79c20.png](./img/J82lP_RbnZ7Ryhw9/1764159090128-d93df62f-a15b-430a-a37c-acd90fc79c20-123731.png)

<font style="color:rgb(38, 38, 38);">大家好。面对“不扩容、不加机器、QPS 翻倍”这个命题，初级工程师可能会觉得是刁难，但对于架构师来说，这正是</font>**<font style="color:rgb(38, 38, 38);">审视系统熵增</font>**<font style="color:rgb(38, 38, 38);">的最佳时机。</font>

<font style="color:rgb(38, 38, 38);">今天我们不谈那些虚无缥缈的理论，我将从</font>**<font style="color:rgb(38, 38, 38);">网络模型、内存架构、数据协议、线程模型</font>**<font style="color:rgb(38, 38, 38);">四个维度，为大家拆解一套在生产环境验证过的“组合拳”。</font>

***

## <font style="color:rgb(38, 38, 38);">2. 第一刀：斩断网络延迟 (Pipeline & Batching)</font>

![1764159114483-4e3e8f48-157f-4a78-8418-4e24fbab5bf6.png](./img/J82lP_RbnZ7Ryhw9/1764159114483-4e3e8f48-157f-4a78-8418-4e24fbab5bf6-161297.png)

<font style="color:rgb(38, 38, 38);">大家先看屏幕上的对比。这看似简单的“打包”，背后隐藏着 Redis 性能最大的杀手——</font>**<font style="color:rgb(38, 38, 38);">RTT（往返时延）与系统调用开销</font>**<font style="color:rgb(38, 38, 38);">。</font>

* **<font style="color:rgb(38, 38, 38);">表象</font>**<font style="color:rgb(38, 38, 38);">：如上图所示，串行模式下，Client 和 Server 像是在打乒乓球，大量时间浪费在“路上”。</font>
* **<font style="color:rgb(38, 38, 38);">深度解析</font>**<font style="color:rgb(38, 38, 38);">：</font>
  * **<font style="color:rgb(38, 38, 38);">系统调用（Syscall）</font>**<font style="color:rgb(38, 38, 38);">：每一次 Redis 请求，应用服务器都要进行</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">write</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">和</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">read</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">系统调用，意味着要发生两次</font>**<font style="color:rgb(38, 38, 38);">用户态与内核态的上下文切换</font>**<font style="color:rgb(38, 38, 38);">。如果你执行 1000 次 SET，就是 2000 次上下文切换，这比 Redis 执行命令本身的开销大得多。</font>
  * **<font style="color:rgb(38, 38, 38);">Pipeline 的本质</font>**<font style="color:rgb(38, 38, 38);">：它不仅仅是减少网络包，更是将 N 次系统调用合并为 1 次。</font>
* **<font style="color:rgb(38, 38, 38);">实战建议</font>**<font style="color:rgb(38, 38, 38);">：</font>
  * **<font style="color:rgb(38, 38, 38);">不要贪杯</font>**<font style="color:rgb(38, 38, 38);">：Pipeline 虽然好，但不要一次打包几万条命令，这会导致网络缓冲区溢出，甚至造成 Head-of-line blocking（队头阻塞）。建议控制在</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">50-100 条</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">为一组。</font>
  * **<font style="color:rgb(38, 38, 38);">区分场景</font>**<font style="color:rgb(38, 38, 38);">：如果是集群模式（Cluster），要注意 Pipeline 中的 Key 必须落在同一个 Slot，否则需要客户端（如 Jedis/Lettuce）进行复杂的计算和分发。</font>

***

## <font style="color:rgb(38, 38, 38);">3. 第二刀：空间换时间，架构降维 (Local Cache)</font>

![1764159124668-fc82713b-9f63-47e1-9d00-056dc060d10b.png](./img/J82lP_RbnZ7Ryhw9/1764159124668-fc82713b-9f63-47e1-9d00-056dc060d10b-528642.png)

<font style="color:rgb(38, 38, 38);">如果网络层优化到了极致，瓶颈依然存在，我们就必须引入架构层面的核武器——</font>**<font style="color:rgb(38, 38, 38);">多级缓存（Near Cache）</font>**<font style="color:rgb(38, 38, 38);">。</font>

* **<font style="color:rgb(38, 38, 38);">架构哲学</font>**<font style="color:rgb(38, 38, 38);">：</font>**<font style="color:rgb(38, 38, 38);">最快的 Redis 请求，是根本不发请求。</font>**
* **<font style="color:rgb(38, 38, 38);">深度解析</font>**<font style="color:rgb(38, 38, 38);">：</font>
  * **<font style="color:rgb(38, 38, 38);">L1 (JVM 堆内)</font>**<font style="color:rgb(38, 38, 38);">：访问速度是纳秒级（ns）。</font>
  * **<font style="color:rgb(38, 38, 38);">L2 (Redis)</font>**<font style="color:rgb(38, 38, 38);">：访问速度是毫秒级（ms）。</font>
  * <font style="color:rgb(38, 38, 38);">两者相差</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">1000 倍</font>**<font style="color:rgb(38, 38, 38);">。</font>
* **<font style="color:rgb(38, 38, 38);">关键权衡 (Trade-off)</font>**<font style="color:rgb(38, 38, 38);">：引入本地缓存最大的挑战是</font>**<font style="color:rgb(38, 38, 38);">数据一致性</font>**<font style="color:rgb(38, 38, 38);">。</font>
  * **<font style="color:rgb(38, 38, 38);">解决方案</font>**<font style="color:rgb(38, 38, 38);">：我们通常采用“</font>**<font style="color:rgb(38, 38, 38);">短 TTL + 惰性更新</font>**<font style="color:rgb(38, 38, 38);">”策略。对于热点 Key（如秒杀商品的库存、配置开关），设置 1-3 秒的过期时间。</font>
  * **<font style="color:rgb(38, 38, 38);">W-TinyLFU 算法</font>**<font style="color:rgb(38, 38, 38);">：建议使用 Caffeine 而不是 Guava Cache，因为 Caffeine 引入了 Window TinyLFU 算法，能更精准地识别出那些“刚进来就变冷”的伪热点数据，防止本地内存被污染。</font>
* **<font style="color:rgb(38, 38, 38);">收益</font>**<font style="color:rgb(38, 38, 38);">：这不仅是 QPS 的翻倍，更是对 Redis 的一种</font>**<font style="color:rgb(38, 38, 38);">保护机制</font>**<font style="color:rgb(38, 38, 38);">，防止热点 Key 击穿压垮整个集群。</font>

***

## <font style="color:rgb(38, 38, 38);">4. 第三刀：拒绝“虚胖”，协议瘦身 (Serialization)</font>

![1764159135408-6128fabe-f579-451c-85e2-b86948198648.png](./img/J82lP_RbnZ7Ryhw9/1764159135408-6128fabe-f579-451c-85e2-b86948198648-339990.png)

<font style="color:rgb(38, 38, 38);">解决了“怎么取”的问题，我们再来看“取什么”。</font>

* **<font style="color:rgb(38, 38, 38);">生产痛点</font>**<font style="color:rgb(38, 38, 38);">：我见过太多系统，为了图方便，直接把巨大的 Java 对象转成 JSON 扔进 Redis。</font>
* **<font style="color:rgb(38, 38, 38);">深度解析</font>**<font style="color:rgb(38, 38, 38);">：</font>
  * **<font style="color:rgb(38, 38, 38);">带宽瓶颈</font>**<font style="color:rgb(38, 38, 38);">：在万兆网卡普及的今天，带宽依然昂贵。一个 1MB 的 BigKey，并发 1000 就是 1GB/s 的流量，瞬间打满网卡。</font>
  * **<font style="color:rgb(38, 38, 38);">主线程阻塞</font>**<font style="color:rgb(38, 38, 38);">：Redis 是单线程处理命令的。</font>**<font style="color:rgb(38, 38, 38);">大 Key 的分配（Malloc）和释放（Free）</font>**<font style="color:rgb(38, 38, 38);">，以及从内核态拷贝数据到用户态，都会长时间占用主线程。</font>
* **<font style="color:rgb(38, 38, 38);">实战建议</font>**<font style="color:rgb(38, 38, 38);">：</font>
  * **<font style="color:rgb(38, 38, 38);">序列化选型</font>**<font style="color:rgb(38, 38, 38);">：放弃 Java 原生序列化和纯文本 JSON。推荐使用</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Protobuf</font>**<font style="color:rgb(38, 38, 38);">、</font>**<font style="color:rgb(38, 38, 38);">MsgPack</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">或</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Kryo</font>**<font style="color:rgb(38, 38, 38);">。它们不仅体积小（通常减少 50%-80%），而且\*\*编解码速度（CPU Cost）\*\*也更快。</font>
  * **<font style="color:rgb(38, 38, 38);">压缩策略</font>**<font style="color:rgb(38, 38, 38);">：对于超过 1KB 的文本数据，开启 Snappy 或 Gzip 压缩，以 CPU 换带宽是划算的。</font>

***

## <font style="color:rgb(38, 38, 38);">5. 第四刀：引擎升级，释放多核 (Threaded I/O)</font>

![1764159170916-cab7bf80-4ba3-48c2-a514-009ebd068c20.png](./img/J82lP_RbnZ7Ryhw9/1764159170916-cab7bf80-4ba3-48c2-a514-009ebd068c20-187339.png)

<font style="color:rgb(38, 38, 38);">最后，我们深入到 Redis 引擎的演进。</font>

* **<font style="color:rgb(38, 38, 38);">历史包袱</font>**<font style="color:rgb(38, 38, 38);">：Redis 6.0 之前之所以坚持单线程，是因为 CPU 不是瓶颈，内存和网络才是。但随着网络硬件（10G/40G网卡）的发展，</font>**<font style="color:rgb(38, 38, 38);">网络中断处理和协议解析</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">成了新的瓶颈。</font>
* **<font style="color:rgb(38, 38, 38);">技术内幕</font>**<font style="color:rgb(38, 38, 38);">：</font>
  * <font style="color:rgb(38, 38, 38);">请注意，Redis 6.0 的多线程是</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">I/O Thread</font>**<font style="color:rgb(38, 38, 38);">，而不是 Execution Thread。</font>
  * **<font style="color:rgb(38, 38, 38);">Main Thread</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">依然负责命令的执行（保证了原子性，无需锁机制）。</font>
  * **<font style="color:rgb(38, 38, 38);">IO Threads</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">负责从 Socket 读取数据、解析协议、以及将结果写回 Socket。</font>
* **<font style="color:rgb(38, 38, 38);">配置指南</font>**<font style="color:rgb(38, 38, 38);">：</font>
  * <font style="color:rgb(38, 38, 38);">在</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">redis.conf</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">中设置</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">io-threads 4</font></code><font style="color:rgb(38, 38, 38);">（建议设置为 CPU 核数的 3/4）。</font>
  * <font style="color:rgb(38, 38, 38);">必须显式开启</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">io-threads-do-reads yes</font></code><font style="color:rgb(38, 38, 38);">。</font>
* **<font style="color:rgb(38, 38, 38);">预期收益</font>**<font style="color:rgb(38, 38, 38);">：在重 I/O（大包、高并发）场景下，这能让 Redis 突破单核性能天花板，QPS 提升</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">100% - 200%</font>**<font style="color:rgb(38, 38, 38);">。</font>

***

## <font style="color:rgb(38, 38, 38);">6. 总结：架构师的决策树</font>

![1764159182284-c60fc536-ddbb-4ed2-aea1-647ef65e1f58.png](./img/J82lP_RbnZ7Ryhw9/1764159182284-c60fc536-ddbb-4ed2-aea1-647ef65e1f58-707395.png)

<font style="color:rgb(38, 38, 38);">最后，总结一下这套组合拳的决策逻辑：</font>

1. **<font style="color:rgb(38, 38, 38);">低成本、高收益</font>**<font style="color:rgb(38, 38, 38);">：优先检查客户端，上</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Pipeline</font>**<font style="color:rgb(38, 38, 38);">，这是最快见效的。</font>
2. **<font style="color:rgb(38, 38, 38);">抗高并发、防击穿</font>**<font style="color:rgb(38, 38, 38);">：必须上</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Local Cache</font>**<font style="color:rgb(38, 38, 38);">，这是架构稳定性的基石。</font>
3. **<font style="color:rgb(38, 38, 38);">降本增效</font>**<font style="color:rgb(38, 38, 38);">：优化</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">序列化协议</font>**<font style="color:rgb(38, 38, 38);">，消灭 BigKey，节省带宽和内存。</font>
4. **<font style="color:rgb(38, 38, 38);">压榨硬件</font>**<font style="color:rgb(38, 38, 38);">：升级</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Redis 6.0+</font>**<font style="color:rgb(38, 38, 38);">，开启多线程 I/O，吃满 CPU 红利。</font>

<font style="color:rgb(38, 38, 38);">技术没有银弹，但有最佳实践。希望这些方案能为各位的系统优化提供弹药。谢谢。</font>


> 更新: 2025-11-28 15:36:55  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/yo0mhznqfy6wir00>