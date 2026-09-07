# Redis 如何同时执行多条命令？

<font style="color:rgb(0, 0, 0);">在 Redis 中，“同时执行多条命令” 的需求通常涉及两种场景：</font>**<font style="color:rgb(0, 0, 0) !important;">提高执行效率（减少网络往返）</font>**<font style="color:rgb(0, 0, 0);"> 和</font>**<font style="color:rgb(0, 0, 0) !important;">保证命令的原子性（避免中间被其他命令打断）</font>**<font style="color:rgb(0, 0, 0);">。针对不同场景，Redis 提供了 3 种核心方案：</font>**<font style="color:rgb(0, 0, 0) !important;">批量命令（如 MSET/MGET）</font>**<font style="color:rgb(0, 0, 0);">、</font>**<font style="color:rgb(0, 0, 0) !important;">管道（Pipeline）</font>**<font style="color:rgb(0, 0, 0);">、</font>**<font style="color:rgb(0, 0, 0) !important;">事务（Transaction）</font>**<font style="color:rgb(0, 0, 0);"> 和</font>**<font style="color:rgb(0, 0, 0) !important;">Lua 脚本</font>**<font style="color:rgb(0, 0, 0);">。以下是具体实现方式、适用场景及优缺点解析：</font>

### <font style="color:rgb(0, 0, 0);">一、批量命令：Redis 原生的 “同类型命令批量执行”</font>

<font style="color:rgb(0, 0, 0);">Redis 针对部分高频操作提供了</font>**<font style="color:rgb(0, 0, 0) !important;">原生批量命令</font>**<font style="color:rgb(0, 0, 0);">，这些命令专门用于一次性处理多个键或值，底层经过优化，效率极高。</font>

#### <font style="color:rgb(0, 0, 0);">典型命令及示例：</font>

| **<font style="color:rgb(0, 0, 0) !important;">数据结构</font>** | **<font style="color:rgb(0, 0, 0) !important;">批量命令</font>** | **<font style="color:rgb(0, 0, 0) !important;">作用</font>** | **<font style="color:rgb(0, 0, 0) !important;">示例</font>** |
| :--- | :--- | :--- | :--- |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">字符串</font> | <code><font style="color:rgb(0, 0, 0);">MSET</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">/</font><code><font style="color:rgb(0, 0, 0);">MGET</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">批量设置 / 获取多个键值对</font> | <code><font style="color:rgb(0, 0, 0);">MSET k1 v1 k2 v2 k3 v3</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">（设置 3 个键）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">哈希表</font> | <code><font style="color:rgb(0, 0, 0);">HMSET</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">/</font><code><font style="color:rgb(0, 0, 0);">HMGET</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">批量设置 / 获取哈希表的多个字段</font> | <code><font style="color:rgb(0, 0, 0);">HMSET user:1 name "zs" age 20</font></code> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">集合</font> | <code><font style="color:rgb(0, 0, 0);">SADD</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">/</font><code><font style="color:rgb(0, 0, 0);">SMEMBERS</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">批量添加集合元素 / 获取所有元素</font> | <code><font style="color:rgb(0, 0, 0);">SADD set1 a b c</font></code><br/><font style="color:rgba(0, 0, 0, 0.85) !important;">（添加 3 个元素）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">有序集合</font> | <code><font style="color:rgb(0, 0, 0);">ZADD</font></code> | <font style="color:rgba(0, 0, 0, 0.85) !important;">批量添加有序集合的元素及分数</font> | <code><font style="color:rgb(0, 0, 0);">ZADD zset1 10 a 20 b</font></code> |

#### <font style="color:rgb(0, 0, 0);">特点：</font>

* **<font style="color:rgb(0, 0, 0) !important;">优点</font>**<font style="color:rgb(0, 0, 0);">：原生支持，无需额外操作；单条命令即可完成批量处理，网络往返仅 1 次，效率最高；原子性执行（Redis 单线程，单条命令天然原子）。</font>
* **<font style="color:rgb(0, 0, 0) !important;">缺点</font>**<font style="color:rgb(0, 0, 0);">：仅支持</font>**<font style="color:rgb(0, 0, 0) !important;">同类型命令</font>**<font style="color:rgb(0, 0, 0);">（如</font><code><font style="color:rgb(0, 0, 0);">MSET</font></code><font style="color:rgb(0, 0, 0);">只能处理字符串，无法混合</font><code><font style="color:rgb(0, 0, 0);">HSET</font></code><font style="color:rgb(0, 0, 0);">）；命令参数长度有限制（受 Redis 配置</font><code><font style="color:rgb(0, 0, 0);">client-query-buffer-limit</font></code><font style="color:rgb(0, 0, 0);">和网络包大小限制）。</font>

#### <font style="color:rgb(0, 0, 0);">适用场景：</font>

<font style="color:rgb(0, 0, 0);">需要批量操作</font>**<font style="color:rgb(0, 0, 0) !important;">同一种数据结构</font>**<font style="color:rgb(0, 0, 0);">的场景（如批量设置多个字符串键、批量获取多个哈希表字段）。</font>

### <font style="color:rgb(0, 0, 0);">二、管道（Pipeline）：“多类型命令批量执行，提高效率”</font>

<font style="color:rgb(0, 0, 0);">如果需要执行</font>**<font style="color:rgb(0, 0, 0) !important;">不同类型的命令</font>**<font style="color:rgb(0, 0, 0);">（如同时执行</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">SET</font></code><font style="color:rgb(0, 0, 0);">、</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">HSET</font></code><font style="color:rgb(0, 0, 0);">、</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">SADD</font></code><font style="color:rgb(0, 0, 0);">），且不严格要求原子性（允许中间被其他命令插入），可以用</font>**<font style="color:rgb(0, 0, 0) !important;">管道（Pipeline）</font>**<font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">减少网络往返次数。</font>

#### <font style="color:rgb(0, 0, 0);">原理：</font>

<font style="color:rgb(0, 0, 0);">正常情况下，客户端发送 1 条命令→等待 Redis 响应→再发下 1 条，每条命令都有 1 次网络往返。管道则是</font>**<font style="color:rgb(0, 0, 0) !important;">客户端一次性发送多条命令</font>**<font style="color:rgb(0, 0, 0);">，Redis 批量处理后一次性返回结果，将 “N 次网络往返” 压缩为 “1 次”，大幅提升效率（尤其在客户端与 Redis 网络延迟高的场景）。</font>

#### <font style="color:rgb(0, 0, 0);">示例（以 Python 的</font><code><font style="color:rgb(0, 0, 0);">redis-py</font></code><font style="color:rgb(0, 0, 0);">库为例）：</font>

```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0)

# 用管道执行3条不同命令
pipe = r.pipeline()
pipe.set('k1', 'v1')       # 字符串命令
pipe.hset('user:1', 'age', 20)  # 哈希命令
pipe.sadd('set1', 'a', 'b')     # 集合命令
result = pipe.execute()    # 一次性发送并获取结果
print(result)  # [True, 1, 2]（分别对应3条命令的返回值）
```

#### <font style="color:rgb(0, 0, 0);">特点：</font>

* **<font style="color:rgb(0, 0, 0) !important;">优点</font>**<font style="color:rgb(0, 0, 0);">：支持混合执行不同类型命令；减少网络往返，效率比单条执行高 10-100 倍（取决于命令数量）；使用简单，大多数客户端都支持。</font>
* **<font style="color:rgb(0, 0, 0) !important;">缺点</font>**<font style="color:rgb(0, 0, 0);">：</font>**<font style="color:rgb(0, 0, 0) !important;">不保证原子性</font>**<font style="color:rgb(0, 0, 0);">（Redis 处理管道中命令时，可能被其他客户端的命令插入，导致中间结果被干扰）；管道中命令过多可能导致客户端缓冲区溢出（需控制命令数量）。</font>

#### <font style="color:rgb(0, 0, 0);">适用场景：</font>

* <font style="color:rgb(0, 0, 0);">非原子性要求的批量操作（如批量初始化数据、批量统计）；</font>
* <font style="color:rgb(0, 0, 0);">网络延迟较高的场景（如客户端与 Redis 不在同一机房）。</font>

### <font style="color:rgb(0, 0, 0);">三、事务（Transaction）：“多命令原子执行，避免中间干扰”</font>

<font style="color:rgb(0, 0, 0);">如果需要</font>**<font style="color:rgb(0, 0, 0) !important;">多条命令要么全部执行，要么全部不执行</font>**<font style="color:rgb(0, 0, 0);">（原子性），且不允许被其他命令打断，Redis 的</font>**<font style="color:rgb(0, 0, 0) !important;">事务（MULTI/EXEC）</font>**<font style="color:rgb(0, 0, 0);"> </font><font style="color:rgb(0, 0, 0);">是核心方案。</font>

#### <font style="color:rgb(0, 0, 0);">原理：</font>

<font style="color:rgb(0, 0, 0);">事务通过</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">MULTI</font></code><font style="color:rgb(0, 0, 0);">（标记事务开始）、</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">EXEC</font></code><font style="color:rgb(0, 0, 0);">（执行事务中所有命令）两个命令包裹多条命令，Redis 会将事务中的命令</font>**<font style="color:rgb(0, 0, 0) !important;">放入队列缓存</font>**<font style="color:rgb(0, 0, 0);">，直到</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">EXEC</font></code><font style="color:rgb(0, 0, 0);">被调用时，才一次性执行所有命令，且执行期间不会被其他客户端的命令插入（保证原子性）。</font>

#### <font style="color:rgb(0, 0, 0);">示例（Redis-cli 中操作）：</font>

```bash
# 开始事务
127.0.0.1:6379> MULTI
OK

# 向事务中添加命令
127.0.0.1:6379> SET k1 v1
QUEUED  # 命令被缓存，未执行
127.0.0.1:6379> HSET user:1 name zs
QUEUED
127.0.0.1:6379> SADD set1 a
QUEUED

# 执行事务（所有命令一次性执行）
127.0.0.1:6379> EXEC
1) OK
2) (integer) 1
3) (integer) 1
```

#### <font style="color:rgb(0, 0, 0);">关键细节：</font>

* **<font style="color:rgb(0, 0, 0) !important;">原子性保证</font>**<font style="color:rgb(0, 0, 0);">：事务中的命令要么全执行，要么全不执行（若</font><code><font style="color:rgb(0, 0, 0);">EXEC</font></code><font style="color:rgb(0, 0, 0);">前 Redis 崩溃，事务不会执行；</font><code><font style="color:rgb(0, 0, 0);">EXEC</font></code><font style="color:rgb(0, 0, 0);">后崩溃，已执行的命令不会回滚，但 Redis 会保证命令执行的完整性）。</font>
* **<font style="color:rgb(0, 0, 0) !important;">错误处理</font>**<font style="color:rgb(0, 0, 0);">：</font>
  * <font style="color:rgb(0, 0, 0);">若事务中存在</font>**<font style="color:rgb(0, 0, 0) !important;">语法错误</font>**<font style="color:rgb(0, 0, 0);">（如命令写错），</font><code><font style="color:rgb(0, 0, 0);">EXEC</font></code><font style="color:rgb(0, 0, 0);">会直接返回错误，所有命令都不执行；</font>
  * <font style="color:rgb(0, 0, 0);">若事务中存在</font>**<font style="color:rgb(0, 0, 0) !important;">运行时错误</font>**<font style="color:rgb(0, 0, 0);">（如对字符串执行</font><code><font style="color:rgb(0, 0, 0);">HSET</font></code><font style="color:rgb(0, 0, 0);">），错误命令会失败，但其他命令仍会执行（Redis 事务不支持回滚，需手动处理）。</font>
* **<font style="color:rgb(0, 0, 0) !important;">放弃事务</font>**<font style="color:rgb(0, 0, 0);">：可用</font><code><font style="color:rgb(0, 0, 0);">DISCARD</font></code><font style="color:rgb(0, 0, 0);">命令清空事务队列，放弃执行。</font>

#### <font style="color:rgb(0, 0, 0);">特点：</font>

* **<font style="color:rgb(0, 0, 0) !important;">优点</font>**<font style="color:rgb(0, 0, 0);">：保证多条命令的原子性（执行期间不被其他命令干扰）；支持混合命令类型。</font>
* **<font style="color:rgb(0, 0, 0) !important;">缺点</font>**<font style="color:rgb(0, 0, 0);">：不支持回滚（运行时错误需手动处理）；性能略低于管道（事务执行时会阻塞其他命令，建议事务命令数量不宜过多）。</font>

#### <font style="color:rgb(0, 0, 0);">适用场景：</font>

* <font style="color:rgb(0, 0, 0);">有原子性要求的操作（如转账：扣减 A 的余额→增加 B 的余额，必须同时成功）；</font>
* <font style="color:rgb(0, 0, 0);">避免中间状态被其他命令读取（如批量更新多个关联键，不允许其他客户端读取到 “部分更新” 的状态）。</font>

### <font style="color:rgb(0, 0, 0);">四、Lua 脚本：“复杂逻辑的原子执行，替代事务”</font>

<font style="color:rgb(0, 0, 0);">对于更复杂的多命令逻辑（如需要根据前一条命令的结果执行后续命令），Redis 的</font>**<font style="color:rgb(0, 0, 0) !important;">Lua 脚本</font>**<font style="color:rgb(0, 0, 0);">是更优选择。Redis 会</font>**<font style="color:rgb(0, 0, 0) !important;">单线程原子性执行整个 Lua 脚本</font>**<font style="color:rgb(0, 0, 0);">，执行期间不会被其他命令打断，且支持逻辑判断。</font>

#### <font style="color:rgb(0, 0, 0);">原理：</font>

<font style="color:rgb(0, 0, 0);">Lua 脚本可以包含多条 Redis 命令，Redis 执行时会将整个脚本视为一个 “原子操作”。脚本中可以用</font><code><font style="color:rgba(0, 0, 0, 0.85) !important;">redis.call()</font></code><font style="color:rgb(0, 0, 0);">调用 Redis 命令，还能通过条件判断实现复杂逻辑（这是事务无法支持的）。</font>

#### <font style="color:rgb(0, 0, 0);">示例（用 Lua 脚本实现 “扣减库存并记录日志”）：</font>

```lua
-- 脚本功能：扣减商品库存，若库存足够，记录扣减日志
-- 参数：KEYS[1] = 库存键，KEYS[2] = 日志键；ARGV[1] = 扣减数量
local stock_key = KEYS[1]
local log_key = KEYS[2]
local num = tonumber(ARGV[1])

-- 获取当前库存
local current_stock = tonumber(redis.call('get', stock_key) or "0")
if current_stock >= num then
    -- 扣减库存
    redis.call('decrby', stock_key, num)
    -- 记录日志（当前时间戳+扣减数量）
    redis.call('lpush', log_key, "["..redis.call('time')[1].."] 扣减"..num)
    return 1  -- 成功
else
    return 0  -- 库存不足，失败
end
```

#### <font style="color:rgb(0, 0, 0);">执行方式（Redis-cli）：</font>

```bash
# 先设置初始库存
127.0.0.1:6379> SET stock:1001 10
OK

# 执行Lua脚本（KEYS为2个键，ARGV为扣减数量3）
127.0.0.1:6379> EVAL "local stock_key = KEYS[1]...return 0 end" 2 stock:1001 log:1001 3
(integer) 1  # 执行成功

# 查看结果
127.0.0.1:6379> GET stock:1001
"7"
127.0.0.1:6379> LRANGE log:1001 0 0
1) "[1698765432] 扣减3"
```

#### <font style="color:rgb(0, 0, 0);">特点：</font>

* **<font style="color:rgb(0, 0, 0) !important;">优点</font>**<font style="color:rgb(0, 0, 0);">：原子性执行（比事务更彻底，支持逻辑判断）；减少网络往返（一次脚本调用完成复杂逻辑）；可复用（脚本可缓存，通过</font><code><font style="color:rgb(0, 0, 0);">EVALSHA</font></code><font style="color:rgb(0, 0, 0);">调用，节省带宽）。</font>
* **<font style="color:rgb(0, 0, 0) !important;">缺点</font>**<font style="color:rgb(0, 0, 0);">：脚本不宜过长（会阻塞 Redis 单线程，影响性能）；调试相对复杂。</font>

#### <font style="color:rgb(0, 0, 0);">适用场景：</font>

* <font style="color:rgb(0, 0, 0);">有条件判断的多命令逻辑（如 “库存足够才扣减”“余额不足则拒绝”）；</font>
* <font style="color:rgb(0, 0, 0);">替代事务处理复杂原子操作（如分布式锁的实现、秒杀逻辑）。</font>

### <font style="color:rgb(0, 0, 0);">总结：如何选择？</font>

| **<font style="color:rgb(0, 0, 0) !important;">方案</font>** | **<font style="color:rgb(0, 0, 0) !important;">支持混合命令</font>** | **<font style="color:rgb(0, 0, 0) !important;">原子性</font>** | **<font style="color:rgb(0, 0, 0) !important;">网络效率</font>** | **<font style="color:rgb(0, 0, 0) !important;">适用场景</font>** |
| :--- | :--- | :--- | :--- | :--- |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">批量命令</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">否（同类型）</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">最高</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">同类型命令批量操作（如 MSET 设置多个字符串）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">管道</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">否</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">高</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">非原子性批量操作（如批量初始化数据）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">事务</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">中</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">简单原子操作（无逻辑判断，如转账）</font> |
| <font style="color:rgba(0, 0, 0, 0.85) !important;">Lua 脚本</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">是</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">高</font> | <font style="color:rgba(0, 0, 0, 0.85) !important;">复杂原子操作（有逻辑判断，如秒杀、分布式锁）</font> |

<font style="color:rgb(0, 0, 0);">根据实际需求选择：</font>

* <font style="color:rgb(0, 0, 0);">简单批量用</font>**<font style="color:rgb(0, 0, 0) !important;">批量命令</font>**<font style="color:rgb(0, 0, 0);">；</font>
* <font style="color:rgb(0, 0, 0);">非原子批量用</font>**<font style="color:rgb(0, 0, 0) !important;">管道</font>**<font style="color:rgb(0, 0, 0);">；</font>
* <font style="color:rgb(0, 0, 0);">简单原子操作用</font>**<font style="color:rgb(0, 0, 0) !important;">事务</font>**<font style="color:rgb(0, 0, 0);">；</font>
* <font style="color:rgb(0, 0, 0);">复杂原子逻辑用</font>**<font style="color:rgb(0, 0, 0) !important;">Lua 脚本</font>**<font style="color:rgb(0, 0, 0);">。</font>


> 更新: 2025-10-27 15:35:09  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/nfk97xdtvwfi417o>