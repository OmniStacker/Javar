# Redis 持久化机制有哪些

## <font style="color:rgb(0, 0, 0);">1. 引言</font>

<font style="color:rgb(0, 0, 0);">Redis 作为高性能的纯内存数据库，其核心优势在于</font>**<font style="color:rgb(0, 0, 0) !important;">内存级读写速度</font>**<font style="color:rgb(0, 0, 0);">（远超传统磁盘数据库），但这一特性也带来了 “内存数据易失性” 的天生短板 —— 当 Redis 服务崩溃、服务器断电或重启时，内存中的数据会直接丢失，可能导致业务中断（如电商购物车清空、缓存雪崩）。</font>

<font style="color:rgb(0, 0, 0);">为解决这一问题，Redis 提供了</font>**<font style="color:rgb(0, 0, 0) !important;">持久化机制</font>**<font style="color:rgb(0, 0, 0);">：在数据写入内存的同时，异步或同步地将数据持久化到磁盘文件中。其核心目标是平衡 “数据安全性”（尽可能少丢数据）、“Redis 性能”（不拖慢读写速度）与 “存储开销”（避免磁盘占用过度），确保 Redis 宕机重启后可从磁盘恢复数据，降低业务损失。</font>

## <font style="color:rgb(0, 0, 0);">2. 为什么需要 Redis 持久化</font>

### <font style="color:rgb(0, 0, 0);">2.1 内存数据易失的风险</font>

<font style="color:rgb(0, 0, 0);">Redis 数据默认仅存储于内存，若未开启持久化：</font>

* <font style="color:rgb(0, 0, 0);">服务异常终止（如进程崩溃、机器断电）后，所有数据直接丢失；</font>
* <font style="color:rgb(0, 0, 0);">重启 Redis 后需重新加载数据（如从数据库全量同步），可能引发 “缓存雪崩”（大量请求穿透到数据库，导致数据库过载）。</font>

![1758523424877-e6e4d407-e151-46b8-a4cc-e6eb5bc15cab.png](./img/gpDTcYMH4QQ76RUP/1758523424877-e6e4d407-e151-46b8-a4cc-e6eb5bc15cab-830269.png)

### <font style="color:rgb(0, 0, 0);">2.2 持久化的核心价值</font>

1. **<font style="color:rgb(0, 0, 0) !important;">数据恢复</font>**<font style="color:rgb(0, 0, 0);">：Redis 重启时自动加载磁盘中的持久化文件，无需 “从零开始”，快速恢复服务；</font>
2. **<font style="color:rgb(0, 0, 0) !important;">灾备保障</font>**<font style="color:rgb(0, 0, 0);">：持久化文件可备份至其他服务器，应对单机硬件故障（如硬盘损坏）；</font>
3. **<font style="color:rgb(0, 0, 0) !important;">避免缓存雪崩</font>**<font style="color:rgb(0, 0, 0);">：恢复数据后，缓存层可继续承接请求，减少对数据库的冲击。</font>

![1758523447678-2a19dbab-c9f8-44be-bde0-f58824235116.png](./img/gpDTcYMH4QQ76RUP/1758523447678-2a19dbab-c9f8-44be-bde0-f58824235116-297862.png)

## <font style="color:rgb(0, 0, 0);">3. Redis 持久化的两种核心方式</font>

<font style="color:rgb(0, 0, 0);">Redis 持久化分为两大类：</font>**<font style="color:rgb(0, 0, 0) !important;">RDB 持久化</font>**<font style="color:rgb(0, 0, 0);">（默认开启）和</font><font style="color:rgb(0, 0, 0);"> </font>**<font style="color:rgb(0, 0, 0) !important;">AOF 持久化</font>**<font style="color:rgb(0, 0, 0);">（需手动开启），二者实现逻辑与适用场景差异显著。</font>

### <font style="color:rgb(0, 0, 0);">3.1 RDB 持久化（Redis Database）</font>

#### <font style="color:rgb(0, 0, 0);">3.1.1 定义</font>

<font style="color:rgb(0, 0, 0);">RDB 是</font>**<font style="color:rgb(0, 0, 0) !important;">快照式持久化</font>**<font style="color:rgb(0, 0, 0);">：在 “特定时间点” 生成内存中所有数据的</font>**<font style="color:rgb(0, 0, 0) !important;">全量二进制快照</font>**<font style="color:rgb(0, 0, 0);">，并保存为</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">.rdb</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">文件（默认文件名</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">dump.rdb</font></code><font style="color:rgb(0, 0, 0);">）。</font>

![1758523523377-070476e2-06d7-4725-b8a5-c5c80b8c3156.png](./img/gpDTcYMH4QQ76RUP/1758523523377-070476e2-06d7-4725-b8a5-c5c80b8c3156-273544.png)

#### <font style="color:rgb(0, 0, 0);">3.1.2 触发方式</font>

<font style="color:rgb(0, 0, 0);">RDB 触发分为 “自动触发” 和 “手动触发”，核心依赖</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">bgsave</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">命令（异步无阻塞），仅</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">save</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">命令（同步阻塞）用于特殊场景。</font>

| **<font style="color:rgb(0, 0, 0) !important;">触发类型</font>** | **<font style="color:rgb(0, 0, 0) !important;">具体方式</font>** | **<font style="color:rgb(0, 0, 0) !important;">核心逻辑</font>** | **<font style="color:rgb(0, 0, 0) !important;">注意事项</font>** |
| :--- | :--- | :--- | :--- |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">手动触发</font> | <code><font style="color:rgb(0, 0, 0);">save</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">命令</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">由 Redis 主线程直接执行快照生成，期间会</font>**<font style="color:rgb(0, 0, 0) !important;">阻塞所有客户端请求</font>** | <font style="color:rgba(0, 0, 0, 0.85) !important;">线上环境禁止使用（可能导致服务不可用）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">手动触发</font> | <code><font style="color:rgb(0, 0, 0);">bgsave</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">命令</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">主线程</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">fork</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">一个子进程，由子进程执行快照生成，主线程继续处理请求</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">无阻塞，推荐线上使用</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">自动触发</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">配置文件规则</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">在</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">redis.conf</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">中预设 “时间间隔 + 写操作数” 规则，满足任一规则时自动执行</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">bgsave</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">默认规则如下表</font> |

**<font style="color:rgb(0, 0, 0) !important;">RDB 自动触发默认规则</font>**<font style="color:rgb(0, 0, 0);">（</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">redis.conf</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">配置）：</font>

| **<font style="color:rgb(0, 0, 0) !important;">条件序号</font>** | **<font style="color:rgb(0, 0, 0) !important;">时间间隔（秒）</font>** | **<font style="color:rgb(0, 0, 0) !important;">最少写操作次数</font>** | **<font style="color:rgb(0, 0, 0) !important;">触发逻辑</font>** |
| :--- | :--- | :--- | :--- |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">1</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">3600（1 小时）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">1</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">1 小时内有 1 次写操作，触发</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">bgsave</font></code> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">2</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">300（5 分钟）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">100</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">5 分钟内有 100 次写操作，触发</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">bgsave</font></code> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">3</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">60（1 分钟）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">10000</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">1 分钟内有 10000 次写操作，触发</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">bgsave</font></code> |

#### <font style="color:rgb(0, 0, 0);">3.1.3 工作流程（以</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">bgsave</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">为例）</font>

1. <font style="color:rgb(0, 0, 0);">客户端发送</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">bgsave</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">命令或满足自动触发规则；</font>
2. <font style="color:rgb(0, 0, 0);">Redis 主线程</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">fork</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">子进程（子进程继承父进程的内存数据段）；</font>
3. <font style="color:rgb(0, 0, 0);">主线程返回 “Background saving started”，继续处理客户端请求；</font>
4. <font style="color:rgb(0, 0, 0);">子进程遍历内存数据，序列化生成二进制快照，写入临时文件；</font>
5. <font style="color:rgb(0, 0, 0);">临时文件生成完成后，覆盖旧的</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">.rdb</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">文件，持久化完成。</font>
6. ![1758523639251-69eb7df6-5842-4d02-905b-812d4c8c1288.png](./img/gpDTcYMH4QQ76RUP/1758523639251-69eb7df6-5842-4d02-905b-812d4c8c1288-212192.png)
7. ![1758523620417-bb0c7828-abb2-451e-b30f-dc1cb04e5f3d.png](./img/gpDTcYMH4QQ76RUP/1758523620417-bb0c7828-abb2-451e-b30f-dc1cb04e5f3d-531517.png)

#### <font style="color:rgb(0, 0, 0);">3.1.4 优缺点</font>

| **<font style="color:rgb(0, 0, 0) !important;">优点</font>** | **<font style="color:rgb(0, 0, 0) !important;">缺点</font>** |
| :--- | :--- |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">二进制格式紧凑，</font><code><font style="color:rgb(0, 0, 0);">.rdb</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">文件体积小，磁盘占用低</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">数据安全性低：两次快照间若宕机，会丢失这段时间的所有写数据（如 1 小时快照一次，最多丢 1 小时数据）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">数据恢复速度快：直接加载全量二进制文件，无需解析命令</font> | <code><font style="color:rgb(0, 0, 0);">fork</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">子进程开销：内存数据量大时，</font><code><font style="color:rgb(0, 0, 0);">fork</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">耗时可能短暂阻塞主线程</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">异步执行（</font><code><font style="color:rgb(0, 0, 0);">bgsave</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">）对 Redis 读写性能影响极小</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">不支持实时持久化，无法满足 “零数据丢失” 需求</font> |

### <font style="color:rgb(0, 0, 0);">3.2 AOF 持久化（Append Only File）</font>

#### <font style="color:rgb(0, 0, 0);">3.2.1 定义</font>

<font style="color:rgb(0, 0, 0);">AOF 是</font>**<font style="color:rgb(0, 0, 0) !important;">日志式持久化</font>**<font style="color:rgb(0, 0, 0);">：记录 Redis 执行的 “每一次写操作”（如</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">set</font></code><font style="color:rgb(0, 0, 0);">、</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">del</font></code><font style="color:rgb(0, 0, 0);">、</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">hmset</font></code><font style="color:rgb(0, 0, 0);">），以 “文本协议格式”（可直接打开查看）追加到</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">.aof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">文件中。</font>

![1758523549235-47b39234-48fa-48ee-a1e0-264a5eecf533.png](./img/gpDTcYMH4QQ76RUP/1758523549235-47b39234-48fa-48ee-a1e0-264a5eecf533-902589.png)

#### <font style="color:rgb(0, 0, 0);">3.2.2 工作流程</font>

<font style="color:rgb(0, 0, 0);">AOF 核心通过 “缓冲区 + 刷盘策略” 平衡性能与安全性，流程如下：</font>

1. **<font style="color:rgb(0, 0, 0) !important;">命令追加</font>**<font style="color:rgb(0, 0, 0);">：Redis 执行写命令后，先将命令追加到内存中的</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">aof_buf</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">缓冲区（避免直接写磁盘导致频繁 IO）；</font>
2. **<font style="color:rgb(0, 0, 0) !important;">缓冲区刷盘</font>**<font style="color:rgb(0, 0, 0);">：根据配置的</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">fsync</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">策略，将</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">aof_buf</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">中的数据写入系统内核缓冲区，再由内核同步到磁盘的</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">.aof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">文件；</font>
3. **<font style="color:rgb(0, 0, 0) !important;">文件重写</font>**<font style="color:rgb(0, 0, 0);">：随着写命令累积，</font><code><font style="color:rgb(0, 0, 0);">.aof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">文件会越来越大（如 100 次</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">set name</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">会存 100 条命令），需通过</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">bgrewriteaof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">命令生成 “仅包含最终数据的精简命令”（如 100 次</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">set</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">合并为 1 条），替换旧</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">.aof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">文件。</font>

![1758523675769-727f82de-fa9f-4f0d-b658-3738ce242eaf.png](./img/gpDTcYMH4QQ76RUP/1758523675769-727f82de-fa9f-4f0d-b658-3738ce242eaf-996421.png)

#### <font style="color:rgb(0, 0, 0);">3.2.3 关键配置：</font><code><font style="color:rgb(0, 0, 0);">fsync</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">刷盘策略</font>

<code><font style="color:rgba(0, 0, 0, 0.85) !important;">fsync</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">策略决定 AOF 的数据安全性与性能，Redis 提供 3 种选项（配置项</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">appendfsync</font></code><font style="color:rgb(0, 0, 0);">）：</font>

| **<font style="color:rgb(0, 0, 0) !important;">策略类型</font>** | **<font style="color:rgb(0, 0, 0) !important;">核心逻辑</font>** | **<font style="color:rgb(0, 0, 0) !important;">数据安全性</font>** | **<font style="color:rgb(0, 0, 0) !important;">性能影响</font>** | **<font style="color:rgb(0, 0, 0) !important;">适用场景</font>** |
| :--- | :--- | :--- | :--- | :--- |
| <code><font style="color:rgb(0, 0, 0);">always</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">每执行 1 条写命令，立即调用</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">fsync</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">同步到磁盘</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">最高（几乎零数据丢失）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">最大（频繁磁盘 IO，阻塞主线程）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">金融、支付等对数据安全性要求极高的场景</font> |
| <code><font style="color:rgb(0, 0, 0);">everysec</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">每秒调用 1 次</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">fsync</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">同步到磁盘（默认策略）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">较高（最多丢失 1 秒数据）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">中等（后台线程执行</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">fsync</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">，不阻塞主线程）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">绝大多数业务场景（平衡安全与性能）</font> |
| <code><font style="color:rgb(0, 0, 0);">no</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">不主动</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">fsync</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">，由操作系统决定何时同步到磁盘</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">最低（OS 崩溃可能丢失大量数据）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">最低（无额外 IO 开销）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">非核心缓存场景（如临时会话数据）</font> |

#### <font style="color:rgb(0, 0, 0);">3.2.4 优缺点</font>

| **<font style="color:rgb(0, 0, 0) !important;">优点</font>** | **<font style="color:rgb(0, 0, 0) !important;">缺点</font>** |
| :--- | :--- |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">数据安全性高：</font><code><font style="color:rgb(0, 0, 0);">everysec</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">策略下最多丢失 1 秒数据，支持近实时持久化</font> | <code><font style="color:rgb(0, 0, 0);">.aof</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">文件体积大（文本格式 + 冗余命令），磁盘占用高</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">文件可读性强：文本格式可直接编辑（如误删数据后手动恢复特定命令）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">数据恢复速度慢：需逐行执行</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">.aof</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">中的所有命令</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">支持文件重写，可压缩冗余数据，降低存储开销</font> | <code><font style="color:rgb(0, 0, 0);">always</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">策略会显著影响 Redis 读写性能</font> |

## <font style="color:rgb(0, 0, 0);">4. Redis 4.0+ 混合持久化（RDB + AOF）</font>

<font style="color:rgb(0, 0, 0);">为兼顾 RDB 的 “快速恢复” 与 AOF 的 “高安全性”，Redis 4.0 及以上版本支持</font>**<font style="color:rgb(0, 0, 0) !important;">混合持久化</font>**<font style="color:rgb(0, 0, 0);">（默认开启，配置项</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">aof-use-rdb-preamble yes</font></code><font style="color:rgb(0, 0, 0);">）。</font>

![1758523733935-9a69055e-9bd7-439c-b070-4a444b10b66b.png](./img/gpDTcYMH4QQ76RUP/1758523733935-9a69055e-9bd7-439c-b070-4a444b10b66b-959682.png)

### <font style="color:rgb(0, 0, 0);">4.1 核心逻辑</font>

* **<font style="color:rgb(0, 0, 0) !important;">持久化过程</font>**<font style="color:rgb(0, 0, 0);">：执行</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">bgrewriteaof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">重写 AOF 时，先以 RDB 格式生成内存全量快照，写入</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">.aof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">文件开头；后续的写命令以 AOF 文本格式追加到文件末尾。</font>
* **<font style="color:rgb(0, 0, 0) !important;">恢复过程</font>**<font style="color:rgb(0, 0, 0);">：Redis 重启时，先加载</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">.aof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">开头的 RDB 快照（快速恢复全量数据），再执行后续的 AOF 命令（补充恢复增量数据）。</font>

### <font style="color:rgb(0, 0, 0);">4.2 优势</font>

* <font style="color:rgb(0, 0, 0);">数据安全性：等同于 AOF（最多丢失 1 秒数据）；</font>
* <font style="color:rgb(0, 0, 0);">恢复速度：接近 RDB（避免全量解析 AOF 命令）；</font>
* <font style="color:rgb(0, 0, 0);">存储开销：比纯 AOF 小（RDB 部分紧凑压缩）。</font>

## <font style="color:rgb(0, 0, 0);">5. RDB 与 AOF 对比及选择建议</font>

### <font style="color:rgb(0, 0, 0);">5.1 核心维度对比表</font>

| **<font style="color:rgb(0, 0, 0) !important;">对比维度</font>** | **<font style="color:rgb(0, 0, 0) !important;">RDB</font>** | **<font style="color:rgb(0, 0, 0) !important;">AOF</font>** | **<font style="color:rgb(0, 0, 0) !important;">混合持久化（RDB+AOF）</font>** |
| :--- | :--- | :--- | :--- |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">数据安全性</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">低（丢两次快照间数据）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">高（最多丢 1 秒）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">高（同 AOF）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">文件体积</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">小（二进制压缩）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">大（文本 + 冗余）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">中（RDB 紧凑 + AOF 增量）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">恢复速度</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">快</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">慢</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">快（同 RDB）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">可读性</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">无（二进制）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">高（文本可编辑）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">中（开头 RDB 不可读，结尾 AOF 可读）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">性能影响</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">小（仅</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">bgsave</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">时</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">fork</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">开销）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">中 / 高（</font><code><font style="color:rgb(0, 0, 0);">fsync</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><font style="color:rgba(0, 0, 0, 0.85) !important;">策略决定）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">小（同 RDB）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">默认开启</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">否</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是（需先开启 AOF）</font> |

### <font style="color:rgb(0, 0, 0);">5.2 选择建议</font>

1. **<font style="color:rgb(0, 0, 0) !important;">选择 RDB</font>**<font style="color:rgb(0, 0, 0);">：</font>
   * <font style="color:rgb(0, 0, 0);">场景：非核心缓存（如首页商品列表、临时会话）、对性能要求极高且可接受少量数据丢失；</font>
   * <font style="color:rgb(0, 0, 0);">优势：最小化性能损耗，快速备份与恢复。</font>
2. **<font style="color:rgb(0, 0, 0) !important;">选择 AOF（纯）</font>**<font style="color:rgb(0, 0, 0);">：</font>
   * <font style="color:rgb(0, 0, 0);">场景：无 RDB 版本支持（<4.0）、需手动编辑持久化文件（如数据恢复）；</font>
   * <font style="color:rgb(0, 0, 0);">注意：需定期执行</font><font style="color:rgb(0, 0, 0);"> </font><code><font style="color:rgb(0, 0, 0);">bgrewriteaof</font></code><font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">控制文件体积。</font>
3. **<font style="color:rgb(0, 0, 0) !important;">选择混合持久化</font>**<font style="color:rgb(0, 0, 0);">：</font>
   * <font style="color:rgb(0, 0, 0);">场景：核心业务（如用户余额、订单数据）、既需高安全性又需快速恢复；</font>
   * <font style="color:rgb(0, 0, 0);">优势：兼顾所有核心需求，是 Redis 4.0+ 的最优解。</font>

## <font style="color:rgb(0, 0, 0);">6. 关键配置与操作命令</font>

### <font style="color:rgb(0, 0, 0);">6.1 核心配置（</font><code><font style="color:rgb(0, 0, 0);">redis.conf</font></code><font style="color:rgb(0, 0, 0);">）</font>

| **<font style="color:rgb(0, 0, 0) !important;">配置项</font>** | **<font style="color:rgb(0, 0, 0) !important;">说明</font>** | **<font style="color:rgb(0, 0, 0) !important;">默认值</font>** |
| :--- | :--- | :--- |
| <code><font style="color:rgb(0, 0, 0);">save 3600 1 300 100 60 10000</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">RDB 自动触发规则</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">启用</font> |
| <code><font style="color:rgb(0, 0, 0);">appendonly</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是否开启 AOF</font> | <code><font style="color:rgb(0, 0, 0);">no</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">（需手动设为</font><font style="color:rgba(0, 0, 0, 0.85) !important;"> </font><code><font style="color:rgb(0, 0, 0);">yes</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">）</font> |
| <code><font style="color:rgb(0, 0, 0);">appendfsync</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">AOF 刷盘策略</font> | <code><font style="color:rgb(0, 0, 0);">everysec</font></code> |
| <code><font style="color:rgb(0, 0, 0);">aof-use-rdb-preamble</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是否开启混合持久化</font> | <code><font style="color:rgb(0, 0, 0);">yes</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">（Redis 4.0+）</font> |
| <code><font style="color:rgb(0, 0, 0);">dbfilename</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">RDB 文件名</font> | <code><font style="color:rgb(0, 0, 0);">dump.rdb</font></code> |
| <code><font style="color:rgb(0, 0, 0);">appendfilename</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">AOF 文件名</font> | <code><font style="color:rgb(0, 0, 0);">appendonly.aof</font></code> |

### <font style="color:rgb(0, 0, 0);">6.2 常用操作命令</font>

| **<font style="color:rgb(0, 0, 0) !important;">命令</font>** | **<font style="color:rgb(0, 0, 0) !important;">功能</font>** |
| :--- | :--- |
| <code><font style="color:rgb(0, 0, 0);">config get save</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">查看 RDB 自动触发规则</font> |
| <code><font style="color:rgb(0, 0, 0);">config get appendonly</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">查看 AOF 是否开启</font> |
| <code><font style="color:rgb(0, 0, 0);">bgsave</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">手动触发 RDB 持久化（异步）</font> |
| <code><font style="color:rgb(0, 0, 0);">bgrewriteaof</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">手动触发 AOF 重写（异步）</font> |
| <code><font style="color:rgb(0, 0, 0);">redis-cli shutdown save</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">关闭 Redis 时强制生成 RDB 快照</font> |

## <font style="color:rgb(0, 0, 0);">7. 总结</font>

1. <font style="color:rgb(0, 0, 0);">Redis 持久化的本质是解决 “内存数据易失” 问题，核心目标是平衡安全、性能与存储开销；</font>
2. <font style="color:rgb(0, 0, 0);">RDB 是 “快照式” 持久化（默认开启），快但安全性低；AOF 是 “日志式” 持久化（需手动开启），安全但恢复慢；</font>
3. <font style="color:rgb(0, 0, 0);">混合持久化（Redis 4.0+）结合二者优势，是核心业务的最优选择；</font>
4. <font style="color:rgb(0, 0, 0);">选择原则：无 “最优方案”，仅 “适配业务”—— 根据数据重要性、性能要求与版本支持选择合适的持久化方式。</font>
