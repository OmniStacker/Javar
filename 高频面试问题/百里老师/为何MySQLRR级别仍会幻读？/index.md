# 为何 MySQL RR 级别仍会幻读？

<font style="color:rgb(38, 38, 38);">众所周知，MySQL InnoDB 存储引擎在可重复读（Repeatable Read, RR）隔离级别下，通过多版本并发控制（MVCC）和 Next-Key Lock 机制，在很大程度上解决了幻读问题。然而，这并非绝对。在特定并发场景下，当事务内混合使用“快照读”和“当前读”时，幻读依然会不期而至。本文将通过一系列可视化图解，深入剖析这一问题的根源，并给出明确的解决方案和最佳实践。</font>

***

### **<font style="color:rgb(38, 38, 38);">一、问题的提出：看似“完美”的 RR 隔离级别下的幻读魅影</font>**

<font style="color:rgb(38, 38, 38);">在日常开发中，我们常常依赖于 RR 隔离级别来保证事务的一致性。一个典型的场景是“读后写”：我们先查询某些记录是否存在，如果不存在，就插入一条新记录。在 RR 级别下，我们期望事务内多次读取相同范围的结果是一致的。但事实果真如此吗？</font>

![1762930150394-6538ac3c-126c-4b9e-a0c8-20eb829f9a50.png](./img/m3DrcnXg96FzFyIX/1762930150394-6538ac3c-126c-4b9e-a0c8-20eb829f9a50-009048.png)

<font style="color:rgb(38, 38, 38);">上图生动地展示了一个经典的幻读场景。让我们拆解这个过程背后的逻辑：</font>

1. **<font style="color:rgb(38, 38, 38);">事务 A 的初始认知</font>**<font style="color:rgb(38, 38, 38);">：事务 A 使用一条普通的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">语句（即</font>**<font style="color:rgb(38, 38, 38);">快照读</font>**<font style="color:rgb(38, 38, 38);">）检查</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">id > 100</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的产品。基于 MVCC 机制，它得到的是事务启动时的一个数据快照。在这个快照中，满足条件的记录为 0 条。</font>
2. **<font style="color:rgb(38, 38, 38);">并发的“搅局者”</font>**<font style="color:rgb(38, 38, 38);">：在事务 A 继续执行之前，事务 B 插入了一条</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">id = 101</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的新记录并迅速提交。由于事务隔离，正在执行快照读的事务 A 对此毫不知情。</font>
3. **<font style="color:rgb(38, 38, 38);">矛盾的爆发</font>**<font style="color:rgb(38, 38, 38);">：事务 A 认为</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">id = 101</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">不存在，于是尝试执行</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">INSERT</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">操作。然而，</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">INSERT</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">语句在执行时，为了保证主键的唯一性，会进行一次</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">来检查记录是否已存在。这次检查会读取数据库的最新状态，于是发现了事务 B 刚刚提交的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">id = 101</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的记录，导致主键冲突（Duplicate entry）而失败。</font>
4. **<font style="color:rgb(38, 38, 38);">幻读的确认</font>**<font style="color:rgb(38, 38, 38);">：此时的事务 A 陷入了困惑：快照读告诉我没有，但插入时却提示已存在。为了验证，它使用</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT ... FOR UPDATE</font></code><font style="color:rgb(38, 38, 38);">（另一种</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">）再次查询</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">id = 101</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的记录，结果竟然真的查询到了一条数据。这条如同“幻影”般出现的数据，就是我们所说的</font>**<font style="color:rgb(38, 38, 38);">幻读</font>**<font style="color:rgb(38, 38, 38);">。</font>

<font style="color:rgb(38, 38, 38);">这个场景的核心矛盾在于：</font>**<font style="color:rgb(38, 38, 38);">事务 A 在同一个事务中，通过不同的读取方式（快照读 vs 当前读），看到了关于同一数据范围的两个完全不同的“现实”</font>**<font style="color:rgb(38, 38, 38);">。</font>

***

### **<font style="color:rgb(38, 38, 38);">二、RR 隔离级别的两大防线：MVCC 与 Next-Key Lock</font>**

<font style="color:rgb(38, 38, 38);">要理解为何防线会被突破，我们首先需要了解 InnoDB 的两大核心防御机制。</font>

![1762930256660-c7120e6b-a133-4f4c-894c-f0f69a395b8a.png](./img/m3DrcnXg96FzFyIX/1762930256660-c7120e6b-a133-4f4c-894c-f0f69a395b8a-889511.png)

#### **<font style="color:rgb(38, 38, 38);">1. MVCC (多版本并发控制)</font>**

<font style="color:rgb(38, 38, 38);">MVCC 是 InnoDB 实现高并发读性能的基石，它主要服务于</font>**<font style="color:rgb(38, 38, 38);">快照读</font>**<font style="color:rgb(38, 38, 38);">（如普通的 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT</font></code><font style="color:rgb(38, 38, 38);">）。其核心思想可以概括为“空间换时间”，通过保存数据的多个历史版本（Undo Log），为每个事务提供一个一致性的数据快照（Read View）。</font>

* **<font style="color:rgb(38, 38, 38);">优点</font>**<font style="color:rgb(38, 38, 38);">：读操作不加锁，读写不冲突，极大地提升了数据库的并发处理能力。</font>
* **<font style="color:rgb(38, 38, 38);">作用</font>**<font style="color:rgb(38, 38, 38);">：在事务的生命周期内，保证了多次快照读的结果都是基于事务启动时的那个“版本”，从而避免了其他事务的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">UPDATE</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">和</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">DELETE</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">导致的不可重复读，以及部分幻读。</font>

#### **<font style="color:rgb(38, 38, 38);">2. Next-Key Lock (临键锁)</font>**

<font style="color:rgb(38, 38, 38);">Next-Key Lock 是 InnoDB 为</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">（如 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT ... FOR UPDATE/LOCK IN SHARE MODE</font></code><font style="color:rgb(38, 38, 38);">, </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">UPDATE</font></code><font style="color:rgb(38, 38, 38);">, </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">DELETE</font></code><font style="color:rgb(38, 38, 38);">, </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">INSERT</font></code><font style="color:rgb(38, 38, 38);">）设计的锁机制，它是 Record Lock（记录锁）和 Gap Lock（间隙锁）的结合体。</font>

* **<font style="color:rgb(38, 38, 38);">Record Lock</font>**<font style="color:rgb(38, 38, 38);">：锁定已存在的具体记录。</font>
* **<font style="color:rgb(38, 38, 38);">Gap Lock</font>**<font style="color:rgb(38, 38, 38);">：锁定一个开区间范围，防止其他事务在这个范围内插入新记录。</font>
* **<font style="color:rgb(38, 38, 38);">Next-Key Lock</font>**<font style="color:rgb(38, 38, 38);">：同时锁定记录本身及其之前的间隙，形成一个左开右闭的区间。</font>

<font style="color:rgb(38, 38, 38);">当我们的</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">操作覆盖一个范围时，Next-Key Lock 会将这个范围内的所有记录和间隙全部锁定。任何试图在这个范围内插入新记录的事务都会被阻塞，直到持有锁的事务提交。这正是 RR 级别宣称能解决幻读的关键所在。</font>

***

### **<font style="color:rgb(38, 38, 38);">三、防线如何被突破：混合读模式下的机制失效</font>**

<font style="color:rgb(38, 38, 38);">既然有如此精妙的设计，为何幻读依然发生？问题就出在“混合使用”上。</font>

![1762930323989-689bbbc3-8410-4af6-bca8-ca5013f10940.png](./img/m3DrcnXg96FzFyIX/1762930323989-689bbbc3-8410-4af6-bca8-ca5013f10940-598747.png)

<font style="color:rgb(38, 38, 38);">上图详细描绘了问题发生时的完整并发时序。关键的转折点在于事务 A 内部读取模式的切换：</font>

* **<font style="color:rgb(38, 38, 38);">阶段一 (T1)</font>**<font style="color:rgb(38, 38, 38);">：事务 A 执行</font>**<font style="color:rgb(38, 38, 38);">快照读</font>**<font style="color:rgb(38, 38, 38);">。此时，InnoDB 仅启用 MVCC 机制，为事务 A 提供了一个一致性的数据视图，但</font>**<font style="color:rgb(38, 38, 38);">并未施加任何锁</font>**<font style="color:rgb(38, 38, 38);">。这相当于一个手持旧地图的观察者，他只能看到地图绘制那一刻的世界。</font>
* **<font style="color:rgb(38, 38, 38);">阶段二 (T2)</font>**<font style="color:rgb(38, 38, 38);">：事务 B 执行插入并提交。由于阶段一没有加锁，事务 B 的操作畅通无阻，数据库的“真实世界”已经被改变。</font>
* **<font style="color:rgb(38, 38, 38);">阶段三 (T3)</font>**<font style="color:rgb(38, 38, 38);">：事务 A 尝试</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">INSERT</font></code><font style="color:rgb(38, 38, 38);">。这个操作触发了</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">。它不再依赖旧地图（Read View），而是直接去探查“真实世界”，并试图在</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">id = 101</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的位置上施工。此时，它立刻发现了事务 B 留下的“建筑”，导致主键冲突。</font>
* **<font style="color:rgb(38, 38, 38);">阶段四 (T4)</font>**<font style="color:rgb(38, 38, 38);">"：事务 A 为了搞清楚状况，再次执行了</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT ... FOR UPDATE</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">，这一次，它明确地看到了那个本不该在它的“世界”里存在的“幻影”记录。</font>

**<font style="color:rgb(38, 38, 38);">根源分析</font>**<font style="color:rgb(38, 38, 38);">：RR 级别的幻读防线（Next-Key Lock）只有在执行</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">时才会被激活。如果事务以一个不加锁的</font>**<font style="color:rgb(38, 38, 38);">快照读</font>**<font style="color:rgb(38, 38, 38);">开始，就相当于为其他事务敞开了一个可以插入“幻影记录”的时间窗口。一旦后续操作（如 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">INSERT</font></code><font style="color:rgb(38, 38, 38);"> 或显式加锁的 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT</font></code><font style="color:rgb(38, 38, 38);">）切换到当前读模式，就会与这个时间窗口内产生的新数据发生冲突，从而导致幻读。</font>

***

### **<font style="color:rgb(38, 38, 38);">四、终极解决方案：统一读取模式，提前锁定</font>**

<font style="color:rgb(38, 38, 38);">解决问题的思路非常直接：杜绝混合使用带来的不一致性，从一开始就采用正确的读取模式。</font>

![1762930366383-614b60bc-8638-4b85-bc5d-a37423fd78d0.png](./img/m3DrcnXg96FzFyIX/1762930366383-614b60bc-8638-4b85-bc5d-a37423fd78d0-455702.png)

<font style="color:rgb(38, 38, 38);">修正后的流程展示了如何通过统一使用</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">来彻底避免幻读：</font>

1. **<font style="color:rgb(38, 38, 38);">修正步骤一</font>**<font style="color:rgb(38, 38, 38);">：事务 A 不再使用普通的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT</font></code><font style="color:rgb(38, 38, 38);">，而是直接使用</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT * FROM products WHERE id > 100 FOR UPDATE;</font></code><font style="color:rgb(38, 38, 38);">。这个操作会触发</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);">。</font>
2. **<font style="color:rgb(38, 38, 38);">激活锁机制</font>**<font style="color:rgb(38, 38, 38);">：InnoDB 立即启用 Next-Key Lock，将</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">(100, +∞)</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">这个范围内的所有间隙全部锁定。此时，事务 A 不仅查询了数据，更重要的是，它向整个数据库宣告：“这片区域归我管了，在我结束之前，谁也别想在这里插入新东西。”</font>
3. **<font style="color:rgb(38, 38, 38);">并发事务被阻塞</font>**<font style="color:rgb(38, 38, 38);">：当事务 B 尝试插入</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">id = 101</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的记录时，它会发现该位置所在的间隙已被事务 A 锁定，因此只能进入等待状态，直到事务 A 提交或回滚。</font>
4. **<font style="color:rgb(38, 38, 38);">保证一致性</font>**<font style="color:rgb(38, 38, 38);">：由于事务 B 被阻塞，事务 A 可以安全地执行后续的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">INSERT</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">操作，因为它确信在自己事务期间，查询范围内的状态不会被任何其他事务所改变。事务的一致性和隔离性得到了完全的保证。</font>

**<font style="color:rgb(38, 38, 38);">核心思想</font>**<font style="color:rgb(38, 38, 38);">：对于所有“读后写”的业务场景，必须在第一次读取时就明确意图，使用 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">FOR UPDATE</font></code><font style="color:rgb(38, 38, 38);"> 或 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">FOR SHARE</font></code><font style="color:rgb(38, 38, 38);"> 将数据锁定，将幻读的可能性扼杀在摇篮里。</font>

***

### **<font style="color:rgb(38, 38, 38);">五、总结与决策指南：如何选择正确的读策略？</font>**

<font style="color:rgb(38, 38, 38);">理解了问题的根源和解决方案后，我们可以总结出一套清晰的决策指南，以应对不同的业务场景。</font>

![1762930412575-eef14c0d-93bb-4501-a19f-f04f23a464db.png](./img/m3DrcnXg96FzFyIX/1762930412575-eef14c0d-93bb-4501-a19f-f04f23a464db-340369.png)

<font style="color:rgb(38, 38, 38);">上图为我们提供了一个清晰的决策流程图和场景对比。总而言之，我们应该遵循以下核心原则：</font>

1. **<font style="color:rgb(38, 38, 38);">识别业务意图</font>**<font style="color:rgb(38, 38, 38);">：在执行查询时，问自己一个问题：“我查询这些数据，是为了后续的写入（</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">INSERT</font></code><font style="color:rgb(38, 38, 38);">, </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">UPDATE</font></code><font style="color:rgb(38, 38, 38);">, </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">DELETE</font></code><font style="color:rgb(38, 38, 38);">）做判断吗？”</font>
   * **<font style="color:rgb(38, 38, 38);">如果“是”</font>**<font style="color:rgb(38, 38, 38);">：那么这属于“读后写”的关键业务逻辑。</font>**<font style="color:rgb(38, 38, 38);">必须</font>**<font style="color:rgb(38, 38, 38);">从一开始就使用</font>**<font style="color:rgb(38, 38, 38);">当前读</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">(</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT ... FOR UPDATE</font></code><font style="color:rgb(38, 38, 38);">)。例如：检查用户名是否存在后注册、扣减库存、处理账户余额等。</font>
   * **<font style="color:rgb(38, 38, 38);">如果“否”</font>**<font style="color:rgb(38, 38, 38);">：这属于纯粹的数据读取或分析。</font>**<font style="color:rgb(38, 38, 38);">应该</font>**<font style="color:rgb(38, 38, 38);">使用</font>**<font style="color:rgb(38, 38, 38);">快照读</font>**<font style="color:rgb(38, 38, 38);">（普通</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">SELECT</font></code><font style="color:rgb(38, 38, 38);">），以利用 MVCC 带来的高并发性能，避免不必要的锁开销。例如：生成报表、数据展示、后台分析等。</font>
2. **<font style="color:rgb(38, 38, 38);">保持模式一致</font>**<font style="color:rgb(38, 38, 38);">：在一个事务中，尤其是涉及关键业务逻辑时，应尽量保持读取模式的一致性。避免先用快照读探路，再用当前读操作的“混合模式”，因为这正是导致幻读的温床。</font>
3. **<font style="color:rgb(38, 38, 38);">相信锁而非巧合</font>**<font style="color:rgb(38, 38, 38);">：不要寄希望于“并发冲突通常不会发生”。在需要保证数据强一致性的场景下，锁是唯一可靠的机制。</font>

<font style="color:rgb(38, 38, 38);">通过遵循这些原则，我们就能在享受 RR 隔离级别带来的便利的同时，精准地规避其潜在的并发陷阱，构建出更加健壮和可靠的系统。</font>


> 更新: 2025-11-12 20:15:11  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/qep9qkp033dczn16>