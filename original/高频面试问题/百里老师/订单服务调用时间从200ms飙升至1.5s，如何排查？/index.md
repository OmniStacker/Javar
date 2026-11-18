# 订单服务调用时间从200ms飙升至1.5s，如何排查？

### ![1760250411207-cf5f638f-19da-4d8a-8411-1c2dc8212da5.png](./img/TDzekBWJG2C017Pa/1760250411207-cf5f638f-19da-4d8a-8411-1c2dc8212da5-239520.png)<font style="color:rgb(38, 38, 38);">一、事故背景：风平浪静下的告警风暴</font>

<font style="color:rgb(38, 38, 38);">一个平静的工作日下午，监控系统突然告警齐发，指向我们的核心服务 ——“订单服务”。监控仪表盘呈现出三个诡异的现象：</font>

1. **<font style="color:rgb(38, 38, 38);">接口响应时间 (RT) 飙升</font>**<font style="color:rgb(38, 38, 38);">：核心接口的 P99 响应时间从日常的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">~150ms</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">飙升至</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">1.5s</font></code><font style="color:rgb(38, 38, 38);">，性能下降了近 900%。</font>
2. **<font style="color:rgb(38, 38, 38);">业务错误率激增</font>**<font style="color:rgb(38, 38, 38);">：API 网关出现大量</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">HTTP 429 (Too Many Requests)</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">错误，意味着下游服务因无法处理请求而拒绝了流量。</font>
3. **<font style="color:rgb(38, 38, 38);">基础资源指标“正常”</font>**<font style="color:rgb(38, 38, 38);">：出乎意料的是，服务器的</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">CPU 使用率</font>**<font style="color:rgb(38, 38, 38);">、</font>**<font style="color:rgb(38, 38, 38);">内存</font>**<font style="color:rgb(38, 38, 38);">、</font>**<font style="color:rgb(38, 38, 38);">网络 I/O</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">等关键指标均处于低位，没有任何异常。</font>

<font style="color:rgb(38, 38, 38);">这就构成了本次排查的核心矛盾：</font>**<font style="color:rgb(38, 38, 38);">计算资源明明很空闲，为什么应用却无法处理请求，表现得如此缓慢？</font>**<font style="color:rgb(38, 38, 38);"> 这感觉就像一条高速公路，明明不堵车，但所有汽车都在以10公里的时速爬行。</font>

### <font style="color:rgb(38, 38, 38);">二、排查之旅：抽丝剥茧，四步定位根源</font>

<font style="color:rgb(38, 38, 38);">面对这个谜团，我们展开了一场从应用到数据库的深度排查。</font>

#### <font style="color:rgb(38, 38, 38);">第一步：深入线程栈，探寻等待的根源</font>

**<font style="color:rgb(38, 38, 38);">思考逻辑 (Why):</font>**<font style="color:rgb(38, 38, 38);"> CPU 不忙但请求慢，首要怀疑方向就是：</font>**<font style="color:rgb(38, 38, 38);">线程并非在执行计算，而是在“等待”</font>**<font style="color:rgb(38, 38, 38);">。CPU 是执行计算的单元，它空闲就证明计算任务不多。请求慢则证明任务从开始到结束耗时很长。这两者结合，强烈指向了线程的等待状态（如 I/O 等待、锁等待等）。</font>

**<font style="color:rgb(38, 38, 38);">排查动作 (How):</font>**<font style="color:rgb(38, 38, 38);"> 我们立即登陆到目标服务器，对应用的 Java 进程执行了 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">jstack</font></code><font style="color:rgb(38, 38, 38);"> 命令，以获取一份实时的线程快照 (Thread Dump)，并统计了所有线程的状态。</font>

**<font style="color:rgb(38, 38, 38);">核心发现 (What & So What?):</font>**<font style="color:rgb(38, 38, 38);"> 分析结果非常明确：</font>**<font style="color:rgb(38, 38, 38);">海量线程（超过80%）都处于 </font>**<code>**<font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">BLOCKED</font>**</code>**<font style="color:rgb(38, 38, 38);"> 状态</font>**<font style="color:rgb(38, 38, 38);">。</font>

![1760250427085-4acfd085-6d2d-4c9f-bcca-973e30596c50.png](./img/TDzekBWJG2C017Pa/1760250427085-4acfd085-6d2d-4c9f-bcca-973e30596c50-579539.png)

<font style="color:rgb(38, 38, 38);">这是本次排查的</font>**<font style="color:rgb(38, 38, 38);">第一个关键突破口</font>**<font style="color:rgb(38, 38, 38);">。它有力地证明了应用正陷于严重的内部等待瓶颈，而不是CPU资源不足。这个发现让我们</font>**<font style="color:rgb(38, 38, 38);">排除了代码死循环、计算量过大等消耗CPU的场景</font>**<font style="color:rgb(38, 38, 38);">，并将调查焦点缩小到两个主要可能性：</font>

1. <font style="color:rgb(38, 38, 38);">应用内部的锁竞争。</font>
2. <font style="color:rgb(38, 38, 38);">缓慢的外部 I/O 调用（如数据库、缓存、下游服务）。</font>

#### <font style="color:rgb(38, 38, 38);">第二步：排查外部依赖，收窄怀疑范围</font>

**<font style="color:rgb(38, 38, 38);">思考逻辑 (Why):</font>**<font style="color:rgb(38, 38, 38);"> 为了判断线程是在等待“内部锁”还是“外部I/O”，我们首先需要检查所有外部依赖的健康状况。如果下游服务变慢，自然会导致我们的应用线程在等待响应时被阻塞。</font>

**<font style="color:rgb(38, 38, 38);">排查动作 (How):</font>**<font style="color:rgb(38, 38, 38);"> 我们打开了全链路监控系统（如 SkyWalking / Prometheus），查看订单服务的服务依赖拓扑图以及所有下游服务的响应时间。</font>

**<font style="color:rgb(38, 38, 38);">核心发现 (What & So What?):</font>**<font style="color:rgb(38, 38, 38);"> 监控显示，所有外部依赖（数据库、Redis缓存、其他微服务）的</font>**<font style="color:rgb(38, 38, 38);">响应时间均在正常范围内</font>**<font style="color:rgb(38, 38, 38);">。</font>

![1760250437880-137762fd-7cf0-4bca-8ce0-3467442c4ef0.png](./img/TDzekBWJG2C017Pa/1760250437880-137762fd-7cf0-4bca-8ce0-3467442c4ef0-595260.png)

<font style="color:rgb(38, 38, 38);">这个发现意义重大，它帮助我们</font>**<font style="color:rgb(38, 38, 38);">排除了所有外部因素</font>**<font style="color:rgb(38, 38, 38);">。问题根源不在别处，就在订单服务应用本身或它直连的数据库上。调查范围被进一步缩小。</font>

#### <font style="color:rgb(38, 38, 38);">第三步：审视JVM内部，发现关键暂停</font>

**<font style="color:rgb(38, 38, 38);">思考逻辑 (Why):</font>**<font style="color:rgb(38, 38, 38);"> 既然排除了外部依赖，那么会不会是JVM自身在“拖后腿”？最常见的元凶就是 </font>**<font style="color:rgb(38, 38, 38);">垃圾回收 (Garbage Collection)</font>**<font style="color:rgb(38, 38, 38);">，尤其是会造成“Stop-The-World” (STW) 的 </font>**<font style="color:rgb(38, 38, 38);">Full GC</font>**<font style="color:rgb(38, 38, 38);">。一次长时间的 Full GC 会冻结所有应用线程，完全可以解释RT的突然飙升。</font>

**<font style="color:rgb(38, 38, 38);">排查动作 (How):</font>**<font style="color:rgb(38, 38, 38);"> 我们使用 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">jstat -gcutil <PID> 1000</font></code><font style="color:rgb(38, 38, 38);"> 命令实时监控GC活动，并检查了GC日志。</font>

**<font style="color:rgb(38, 38, 38);">核心发现 (What & So What?):</font>**<font style="color:rgb(38, 38, 38);"> 我们捕捉到了一个惊人的现象：</font>**<font style="color:rgb(38, 38, 38);">一次耗时高达 </font>**<code>**<font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">1.2秒</font>**</code>**<font style="color:rgb(38, 38, 38);"> 的 Full GC</font>**<font style="color:rgb(38, 38, 38);">！</font>

![1760250446013-4008a0ec-abdb-4e41-8c97-9d6c658ca89b.png](./img/TDzekBWJG2C017Pa/1760250446013-4008a0ec-abdb-4e41-8c97-9d6c658ca89b-078227.png)

<font style="color:rgb(38, 38, 38);">这个发现是</font>**<font style="color:rgb(38, 38, 38);">第二个关键突破口</font>**<font style="color:rgb(38, 38, 38);">。</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">1.2秒</font></code><font style="color:rgb(38, 38, 38);">的全局暂停，与我们观察到的 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">1.5秒</font></code><font style="color:rgb(38, 38, 38);"> RT 高度吻合。它直接解释了请求为何会突然卡住。</font>

<font style="color:rgb(38, 38, 38);">然而，这还不是根源。健康的JVM不应如此频繁或长时间地进行Full GC。</font>**<font style="color:rgb(38, 38, 38);">一定有其他原因导致了内存的异常</font>**<font style="color:rgb(38, 38, 38);">，进而触发了这次代价高昂的GC。同时，它也还未解释 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">HTTP 429</font></code><font style="color:rgb(38, 38, 38);"> 错误。我们需要继续深挖。</font>

#### <font style="color:rgb(38, 38, 38);">第四步：关联现象，发现最终瓶颈</font>

**<font style="color:rgb(38, 38, 38);">思考逻辑 (Why):</font>**<code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">HTTP 429</font></code><font style="color:rgb(38, 38, 38);"> 错误通常意味着资源耗尽。线程在 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">BLOCKED</font></code><font style="color:rgb(38, 38, 38);">，外部依赖正常，我们还剩下最后一个关键资源没有检查：</font>**<font style="color:rgb(38, 38, 38);">数据库连接池</font>**<font style="color:rgb(38, 38, 38);">。如果大量线程因为拿不到数据库连接而被阻塞，这完全符合我们观察到的所有现象。</font>

**<font style="color:rgb(38, 38, 38);">排查动作 (How):</font>**<font style="color:rgb(38, 38, 38);"> 我们打开了应用内嵌的 Druid 连接池监控页面。</font>

**<font style="color:rgb(38, 38, 38);">核心发现 (What & So What?):</font>**<font style="color:rgb(38, 38, 38);"> 监控页面惨不忍睹：</font>**<font style="color:rgb(38, 38, 38);">连接池中的80个连接全部被占用，还有数百个线程正在排队等待获取连接</font>**<font style="color:rgb(38, 38, 38);">。</font>

![1760250459997-bf1505d9-9889-4177-b3a1-70cf7611a398.png](./img/TDzekBWJG2C017Pa/1760250459997-bf1505d9-9889-4177-b3a1-70cf7611a398-102315.png)

<font style="color:rgb(38, 38, 38);">至此，所有线索都汇集到了一起。这解释了为何线程会 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">BLOCKED</font></code><font style="color:rgb(38, 38, 38);">，也解释了为何新来的请求因拿不到任何资源而被拒绝（</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">HTTP 429</font></code><font style="color:rgb(38, 38, 38);">）。</font>

### <font style="color:rgb(38, 38, 38);">三、真相大白：一条SQL引发的“血案”</font>

<font style="color:rgb(38, 38, 38);">我们已经知道，是数据库连接池耗尽导致了系统雪崩。那么，为什么连接会全部被占用且不释放呢？唯一的解释是：</font>**<font style="color:rgb(38, 38, 38);">有非常慢的SQL事务长时间占用了连接</font>**<font style="color:rgb(38, 38, 38);">。</font>

<font style="color:rgb(38, 38, 38);">我们立即开启了数据库的慢查询日志（Slow Query Log），并检查了当前正在执行的查询列表。</font>

**<font style="color:rgb(38, 38, 38);">最终原因 (The Root Cause):</font>**<font style="color:rgb(38, 38, 38);"> 一条 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">UPDATE</font></code><font style="color:rgb(38, 38, 38);"> 语句浮出水面。它正在更新一个拥有数百万行数据的大表，但其 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">WHERE</font></code><font style="color:rgb(38, 38, 38);"> 子句中的 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">status</font></code><font style="color:rgb(38, 38, 38);"> 字段</font>**<font style="color:rgb(38, 38, 38);">竟然没有索引</font>**<font style="color:rgb(38, 38, 38);">！</font>

![1760250469102-e7e37055-390a-4025-a5a9-733e21bc766d.png](./img/TDzekBWJG2C017Pa/1760250469102-e7e37055-390a-4025-a5a9-733e21bc766d-984297.png)

<font style="color:rgb(38, 38, 38);">在数据库中，对没有索引的字段进行更新，会导致</font>**<font style="color:rgb(38, 38, 38);">行锁升级为表锁</font>**<font style="color:rgb(38, 38, 38);">，锁住了整张表。</font>

<font style="color:rgb(38, 38, 38);">现在，我们可以完整地串联起整个事故的因果链了：</font>

1. **<font style="color:rgb(38, 38, 38);">触发点</font>**<font style="color:rgb(38, 38, 38);">：一个没有索引的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">UPDATE</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">SQL被执行。</font>
2. **<font style="color:rgb(38, 38, 38);">锁升级</font>**<font style="color:rgb(38, 38, 38);">：该SQL导致数据库发生</font>**<font style="color:rgb(38, 38, 38);">表锁</font>**<font style="color:rgb(38, 38, 38);">，所有其他针对该表的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT</font></code><font style="color:rgb(38, 38, 38);">、</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">INSERT</font></code><font style="color:rgb(38, 38, 38);">、</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">UPDATE</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">操作全部被阻塞。</font>
3. **<font style="color:rgb(38, 38, 38);">连接占用</font>**<font style="color:rgb(38, 38, 38);">：执行这些被阻塞操作的线程，其持有的数据库连接无法释放。</font>
4. **<font style="color:rgb(38, 38, 38);">连接池耗尽</font>**<font style="color:rgb(38, 38, 38);">：短时间内，连接池中的所有连接都被这些等待表锁的事务所占用。</font>
5. **<font style="color:rgb(38, 38, 38);">应用线程阻塞</font>**<font style="color:rgb(38, 38, 38);">：新的业务请求涌入，在尝试获取数据库连接时，因连接池已空而全部进入</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">BLOCKED</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">状态，等待连接释放。</font>
6. **<font style="color:rgb(38, 38, 38);">Full GC 触发</font>**<font style="color:rgb(38, 38, 38);">：大量线程被阻塞，导致其栈上引用的对象（如请求上下文、业务数据）长时间存活，无法在Young GC中被回收，最终被晋升到老年代。老年代空间被迅速填满，触发了耗时极长的</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Full GC</font>**<font style="color:rgb(38, 38, 38);">。</font>
7. **<font style="color:rgb(38, 38, 38);">最终表现</font>**<font style="color:rgb(38, 38, 38);">：Full GC 的长暂停（</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">1.2s</font></code><font style="color:rgb(38, 38, 38);">）和获取连接的漫长等待，共同导致了接口RT飙升至</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">1.5s</font></code><font style="color:rgb(38, 38, 38);">。而后续不断涌入的请求，因线程池和连接池均已饱和，被服务直接拒绝，返回</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">HTTP 429</font></code><font style="color:rgb(38, 38, 38);">。</font>

### <font style="color:rgb(38, 38, 38);">四、总结与反思</font>

<font style="color:rgb(38, 38, 38);">这次事故是一次典型的由“一个点的疏忽”引发“整个面崩溃”的案例。我们将其排查路径和核心发现总结如下：</font>

![1760250481523-f9531b8f-4de6-42a9-92ce-8c6cb47642c0.png](./img/TDzekBWJG2C017Pa/1760250481523-f9531b8f-4de6-42a9-92ce-8c6cb47642c0-946912.png)

<font style="color:rgb(38, 38, 38);">为了防止此类问题再次发生，我们制定了以下改进措施：</font>

1. **<font style="color:rgb(38, 38, 38);">SQL上线规范</font>**<font style="color:rgb(38, 38, 38);">：所有非</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">语句，尤其是对大表的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">UPDATE</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">和</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">DELETE</font></code><font style="color:rgb(38, 38, 38);">，必须强制进行</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">EXPLAIN</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">评审，确保</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">WHERE</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">条件和</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">JOIN</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">字段都命中了索引。</font>
2. **<font style="color:rgb(38, 38, 38);">核心表索引巡检</font>**<font style="color:rgb(38, 38, 38);">：建立自动化脚本，定期巡检核心业务表的索引覆盖情况，防止遗漏。</font>
3. **<font style="color:rgb(38, 38, 38);">超时配置优化</font>**<font style="color:rgb(38, 38, 38);">：为数据库连接池设置合理的获取连接超时时间 (</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">maxWait</font></code><font style="color:rgb(38, 38, 38);">)，并为核心业务的数据库事务设置更短的执行超时。这可以在问题发生时快速失败，避免整个应用被拖垮，实现“熔断”。</font>
4. **<font style="color:rgb(38, 38, 38);">监控告警增强</font>**<font style="color:rgb(38, 38, 38);">：除了CPU、内存等基础指标，将</font>**<font style="color:rgb(38, 38, 38);">数据库连接池的等待线程数</font>**<font style="color:rgb(38, 38, 38);">和</font>**<font style="color:rgb(38, 38, 38);">JVM老年代使用率的增长速率</font>**<font style="color:rgb(38, 38, 38);">也纳入核心告警指标。</font>

<font style="color:rgb(38, 38, 38);">通过这次深刻的教训，我们不仅修复了一个隐蔽的Bug，更重要的是完善了我们的技术流程和监控体系，让系统变得更加健壮。</font>
