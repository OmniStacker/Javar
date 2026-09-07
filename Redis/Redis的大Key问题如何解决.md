# Redis的大Key问题如何解决

<font style="color:rgba(0, 0, 0, 0.82);">Redis的大Key问题是指单个Key所对应的数据量过大，一般单个key超过10kb就被认为是大Key，这会导致以下问题：</font>

1. **<font style="color:rgba(0, 0, 0, 0.82);">网络延迟增大</font>**<font style="color:rgba(0, 0, 0, 0.82);">：传输大数据需要更多的时间。</font>
2. **<font style="color:rgba(0, 0, 0, 0.82);">阻塞Redis性能</font>**<font style="color:rgba(0, 0, 0, 0.82);">：大Key的操作会阻塞Redis单线程的性能。</font>
3. **<font style="color:rgba(0, 0, 0, 0.82);">内存不足和导致OOM</font>**<font style="color:rgba(0, 0, 0, 0.82);">：大Key可能会占用过多内存，影响其它部分的缓存使用。</font>

<font style="color:rgba(0, 0, 0, 0.82);"></font>

<font style="color:rgba(0, 0, 0, 0.82);"></font>

## <font style="color:rgba(0, 0, 0, 0.82);">排查</font>

## <font style="color:rgb(24, 24, 24) !important;">Big Key问题排查</font>

<font style="color:rgb(36, 41, 46);">当出现Redis性能急剧下降的情况时，很可能是由于存在大key导致的。在排除大key问题时，可以考虑采取以下几种方法：</font>

### <font style="color:rgb(24, 24, 24) !important;">BIGKEYS命令</font>

<font style="color:rgb(36, 41, 46);">Redis自带的</font><font style="color:rgb(36, 41, 46);"> </font><code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">BIGKEYS</font></code><font style="color:rgb(36, 41, 46);"> </font><font style="color:rgb(36, 41, 46);">命令可以查询当前Redis中所有key的信息，对整个数据库中的键值对大小情况进行统计分析。</font>

<font style="color:rgb(36, 41, 46);">比如说，统计每种数据类型的键值对个数以及平均大小。</font>

<font style="color:rgb(36, 41, 46);">此外，这个命令执行后，会输出每种数据类型中最大的 big key 的信息，对于 String 类型来说，会输出最大 big key 的字节长度，对于集合类型来说，会输出最大 big key 的元素个数。</font>

<code>**<font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">BIGKEYS</font>**</code>**<font style="color:rgb(36, 41, 46);">命令会扫描整个数据库，这个命令本身会阻塞Redis</font>**<font style="color:rgb(36, 41, 46);">，找出所有的大键，并将其以一个列表的形式返回给客户端。</font>

<font style="color:rgb(36, 41, 46);">命令格式如下：</font>

```plain
$ redis-cli --bigkeys
```

<font style="color:rgb(36, 41, 46);">返回示例如下：</font>

```plain
# Scanning the entire keyspace to find biggest keys as well as
# average sizes per key type.  You can use -i 0.1 to sleep 0.1 sec
# per 100 SCAN commands (not usually needed).

[00.00%] Biggest string found so far 'a' with 3 bytes
[05.14%] Biggest list   found so far 'b' with 100004 items
[35.77%] Biggest string found so far 'c' with 6 bytes
[73.91%] Biggest hash   found so far 'd' with 3 fields

-------- summary -------

Sampled 506 keys in the keyspace!
Total key length in bytes is 3452 (avg len 6.82)

Biggest string found 'c' has 6 bytes
Biggest   list found 'b' has 100004 items
Biggest   hash found 'd' has 3 fields

504 strings with 1403 bytes (99.60% of keys, avg size 2.78)
1 lists with 100004 items (00.20% of keys, avg size 100004.00)
0 sets with 0 members (00.00% of keys, avg size 0.00)
1 hashs with 3 fields (00.20% of keys, avg size 3.00)
0 zsets with 0 members (00.00% of keys, avg size 0.00)
```

<font style="color:rgb(36, 41, 46);">解读下返回结果，从这个结果中可以看出：</font>

* <font style="color:rgb(36, 41, 46);">Redis中样本了506个键。</font>
* <font style="color:rgb(36, 41, 46);">这506个键总共占用了3452字节，平均每个键占用6.82字节。</font>
* <font style="color:rgb(36, 41, 46);">最大的字符串键是'c'，值有6字节。</font>
* <font style="color:rgb(36, 41, 46);">最大的列表键是'b'，有100004个元素。</font>
* <font style="color:rgb(36, 41, 46);">最大的哈希键是'd'，有3个字段。</font>
* <font style="color:rgb(36, 41, 46);">有504个字符串键，总共1403字节，占所有键的99.60%，平均每个字符串键大小为2.78字节。</font>
* <font style="color:rgb(36, 41, 46);">有1个列表键，包含100004个元素，占所有键的0.20%，平均每个列表键大小为100004个元素。</font>
* <font style="color:rgb(36, 41, 46);">没有集合(set)键。</font>
* <font style="color:rgb(36, 41, 46);">有1个哈希键，包含3个字段，占所有键的0.20%，平均每个哈希键大小为3个字段。</font>
* <font style="color:rgb(36, 41, 46);">没有有序集合(zset)键。</font>

<font style="color:rgb(36, 41, 46);">这些信息可以帮助你理解Redis数据库的使用状态，以便进行相应的优化或调整。</font>

<font style="color:rgb(36, 41, 46);">需要注意的是，由于</font><code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">BIGKEYS</font></code><font style="color:rgb(36, 41, 46);">命令需要扫描整个数据库，所以它可能会对Redis实例造成一定的负担。</font>**<font style="color:rgb(36, 41, 46);">在执行这个命令之前，请确保你的Redis实例有足够的资源来处理它，建议在从节点执行</font>**<font style="color:rgb(36, 41, 46);">。</font>

#### <font style="color:rgb(24, 24, 24) !important;">Debug Object</font>

<font style="color:rgb(36, 41, 46);">如果我们找到了Big Key，就需要对其进行进一步的分析。我们可以使用命令</font><code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">debug object key</font></code><font style="color:rgb(36, 41, 46);">查看某个key的详细信息，包括该key的value大小等。这时候你就可以“窥探”Redis的内部，看看到底是哪个key太大导致的问题。</font>

<font style="color:rgb(36, 41, 46);">Debug Object 命令是一个调试命令，当 key 存在时，返回有关信息。 当 key 不存在时，返回一个错误。</font>

```plain
redis 127.0.0.1:6379> DEBUG OBJECT key
Value at:0xb6838d20 refcount:1 encoding:raw serializedlength:9 lru:283790 lru_seconds_idle:150

redis 127.0.0.1:6379> DEBUG OBJECT key
(error) ERR no such key
```

<font style="color:rgb(36, 41, 46);">第一次运行命令时，返回了 key 对应的具体信息。这些值的意思如下：</font>

* <code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">Value at:0xb6838d20</font></code><font style="color:rgb(36, 41, 46);">：key 所在的内存地址。</font>
* <code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">refcount:1</font></code><font style="color:rgb(36, 41, 46);">：引用计数，表示该对象被引用的次数。</font>
* <code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">encoding:raw</font></code><font style="color:rgb(36, 41, 46);">：编码类型，这里是 raw ，表示这个字符串对象的编码类型。</font>
* <code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">serializedlength:9</font></code><font style="color:rgb(36, 41, 46);">：序列化后的长度。</font>
* <code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">lru:283790</font></code><font style="color:rgb(36, 41, 46);">：LRU （Least Recently Used）信息，即最近最少使用算法的相关信息，在内存淘汰策略中会用到。</font>
* <code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">lru_seconds_idle:150</font></code><font style="color:rgb(36, 41, 46);">：该 key 已空闲多久（单位为秒），也就是自从最后一次访问已经过去多少秒。</font>

<font style="color:rgb(36, 41, 46);">第二次运行命令时，返回了</font><font style="color:rgb(36, 41, 46);"> </font><code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">(error) ERR no such key</font></code><font style="color:rgb(36, 41, 46);">，说明在 Redis 中没有找到名为 'key' 的键。</font>

#### <font style="color:rgb(24, 24, 24) !important;">memory usage</font>

<font style="color:rgb(36, 41, 46);">在Redis4.0之前，只能通过</font><code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">DEBUG OBJECT</font></code><font style="color:rgb(36, 41, 46);">命令估算key的内存使用(字段serializedlength)，但DEBUG OBJECT命令是存在误差的。</font>

<font style="color:rgb(36, 41, 46);">4.0版本及以上，更推荐使用</font><code><font style="color:rgb(36, 41, 46);background-color:rgba(27, 31, 35, 0.05);">memory usag</font></code><font style="color:rgb(36, 41, 46);">命令。</font>

<font style="color:rgb(36, 41, 46);">memory usage命令使用非常简单，格式为：</font>**<font style="color:rgb(36, 41, 46);">memory usage key</font>**<font style="color:rgb(36, 41, 46);">。</font>

<font style="color:rgb(36, 41, 46);">如果当前key存在，则返回key的value实际使用内存估算值，如果key不存在，则返回nil。</font>

```plain
127.0.0.1:6379> set k1 value1
OK
127.0.0.1:6379> memory usage k1    //这里k1 value占用57字节内存
(integer) 57
127.0.0.1:6379> memory usage aaa  // aaa键不存在，返回nil.
(nil)
```

<font style="color:rgb(36, 41, 46);">对于除String类型之外的类型，memory usage命令采用抽样的方式，默认抽样5个元素，所以计算是近似值，我们也可以手动指定抽样的个数。</font>

<font style="color:rgb(36, 41, 46);">示例说明：生成一个100w个字段的hash键：hkey，每字段的value长度是从1~1024字节的随机值。</font>

```plain
127.0.0.1:6379> hlen hkey    // hkey有100w个字段，每个字段的value长度介于1~1024个字节
(integer) 1000000
127.0.0.1:6379> MEMORY usage hkey   //默认SAMPLES为5，分析hkey键内存占用521588753字节
(integer) 521588753
127.0.0.1:6379> MEMORY usage hkey SAMPLES  1000 //指定SAMPLES为1000，分析hkey键内存占用617977753字节
(integer) 617977753
127.0.0.1:6379> MEMORY usage hkey SAMPLES  10000 //指定SAMPLES为10000，分析hkey键内存占用624950853字节
(integer) 624950853
```

<font style="color:rgb(36, 41, 46);">要想获取key较精确的内存值，就指定更大抽样个数。但是抽样个数越大，占用cpu时间分片就越大。</font>

<font style="color:rgba(0, 0, 0, 0.82);"></font>

<font style="color:rgba(0, 0, 0, 0.82);">为了解决这些问题，可以采取以下解决方案：</font>

### <font style="color:rgba(0, 0, 0, 0.82);">解决方案</font>

#### <font style="color:rgba(0, 0, 0, 0.82);">1. </font>**<font style="color:rgba(0, 0, 0, 0.82);">分拆大Key</font>**

<font style="color:rgba(0, 0, 0, 0.82);">big list： list1、list2、...listN</font>

<font style="color:rgb(74, 74, 74);">big hash：可以将数据分段存储，比如一个大的key，假设存了1百万的用户数据，可以拆分成200个key，每个key下面存放5000个用户数据</font>

<font style="color:rgb(74, 74, 74);"></font>

<font style="color:rgba(0, 0, 0, 0.82);">2. </font>**<font style="color:rgba(0, 0, 0, 0.82);">压缩数据</font>**

<font style="color:rgba(0, 0, 0, 0.82);">在存储之前对较大的数据进行压缩，从而减少存储占用空间。</font>

```java
import java.util.zip.GZIPOutputStream;  
import java.io.ByteArrayOutputStream;  
import java.io.IOException;  
import java.nio.charset.StandardCharsets;  

// Example of compressing data before storing  
public class DataCompressor {  
    public byte[] compress(String data) throws IOException {  
        ByteArrayOutputStream bos = new ByteArrayOutputStream(data.length());  
        GZIPOutputStream gzip = new GZIPOutputStream(bos);  
        gzip.write(data.getBytes(StandardCharsets.UTF_8));  
        gzip.close();  
        return bos.toByteArray();  
    }  

    public void storeCompressedKey(String key, String data) {  
        try {  
            byte[] compressedData = compress(data);  
            RedisClient.set(key.getBytes(StandardCharsets.UTF_8), compressedData);  
        } catch (IOException e) {  
            e.printStackTrace();  
        }  
    }  
}
```

#### <font style="color:rgba(0, 0, 0, 0.82);">3.</font><font style="color:rgba(0, 0, 0, 0.82);"> </font>**<font style="color:rgba(0, 0, 0, 0.82);">惰性删除</font>**

<font style="color:rgba(0, 0, 0, 0.82);">当更新或删除大Key时使用惰性删除(</font>**<font style="color:rgb(74, 74, 74);">lazyfree-lazy-expire yes</font>**<font style="color:rgb(74, 74, 74);"></font><font style="color:rgba(0, 0, 0, 0.82);">)来避免阻塞整个Redis。</font>

<font style="color:rgba(0, 0, 0, 0.82);">4. </font>**<font style="color:rgba(0, 0, 0, 0.82);">使用SCAN替代KEYS</font>**

<font style="color:rgba(0, 0, 0, 0.82);">在处理集合时，使用</font><code><font style="color:rgba(0, 0, 0, 0.82);">SCAN</font></code><font style="color:rgba(0, 0, 0, 0.82);">命令遍历大Key而不是</font><code><font style="color:rgba(0, 0, 0, 0.82);">KEYS</font></code><font style="color:rgba(0, 0, 0, 0.82);">，避免一次性加载所有数据。</font>

```java
import redis.clients.jedis.Jedis;  
import redis.clients.jedis.ScanParams;  
import redis.clients.jedis.ScanResult;  

import java.util.List;  

// Example: Iterating through large set with SCAN  
public class RedisScanner {  
    private Jedis jedis;  

    public RedisScanner(Jedis jedis) {  
        this.jedis = jedis;  
    }  

    public void scanLargeKey(String largeSetKey) {  
        String cursor = ScanParams.SCAN_POINTER_START;  
        ScanParams scanParams = new ScanParams().count(100); // 分批次取100个  
        do {  
            ScanResult<String> scanResult = jedis.sscan(largeSetKey, cursor, scanParams);  
            List<String> results = scanResult.getResult();  
            processResults(results);  
            cursor = scanResult.getCursor();  
        } while (!cursor.equals(ScanParams.SCAN_POINTER_START));  
    }  

    private void processResults(List<String> results) {  
        // 处理结果集  
    }  
}
```

### <font style="color:rgba(0, 0, 0, 0.82);">结论</font>

<font style="color:rgba(0, 0, 0, 0.82);">分片、压缩、异步删除和合理的遍历方式可以有效解决Redis大Key问题。在实际应用中，根据具体的使用场景和系统架构选择和组合这些方案。此外，要定期监控Redis节点的内存和数据使用情况，优化大Key的管理。注意，解决大Key问题往往需要架构上的设计调整。</font>


> 更新: 2025-10-10 12:37:28  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/fg51mlsueyfivzrh>