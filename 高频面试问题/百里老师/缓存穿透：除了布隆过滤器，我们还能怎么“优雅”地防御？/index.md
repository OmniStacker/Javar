# 缓存穿透：除了布隆过滤器，我们还能怎么“优雅”地防御？

![1764759660617-08aa1a04-713e-4ee4-892d-68c8dd930469.png](./img/0Zi0xBfzH2bNaDst/1764759660617-08aa1a04-713e-4ee4-892d-68c8dd930469-987706.png)

<font style="color:rgb(38, 38, 38);">在分布式系统的缓存防御战中，“缓存穿透”是最经典也是最棘手的场景之一。当海量请求查询一个</font>**<font style="color:rgb(38, 38, 38);">根本不存在的数据</font>**<font style="color:rgb(38, 38, 38);">时，流量会瞬间击穿 Redis，直达脆弱的数据库。</font>

<font style="color:rgb(38, 38, 38);">提到防御，大家第一反应往往是“布隆过滤器（Bloom Filter）”。它固然经典，但并非万能银弹（误判率、不可删除等硬伤）。今天我们来探讨几种更符合现代架构的优雅方案。</font>

***

### <font style="color:rgb(38, 38, 38);">一、 危机现场：当流量绕过防线</font>

![1764759682236-8e3813c4-7884-4758-8eb8-e3e58b1936bb.png](./img/0Zi0xBfzH2bNaDst/1764759682236-8e3813c4-7884-4758-8eb8-e3e58b1936bb-129023.png)

<font style="color:rgb(38, 38, 38);">如上图所示，缓存穿透的可怕之处不在于“流量大”，而在于</font>**<font style="color:rgb(38, 38, 38);">“流量无效”。</font>**<font style="color:rgb(38, 38, 38);"> </font>

<font style="color:rgb(38, 38, 38);">攻击者（或代码 Bug）往往利用随机生成的 Key（如 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">UUID</font></code><font style="color:rgb(38, 38, 38);"> 或负数 ID）发起攻击。由于这些 Key 在缓存中必然 Miss，在数据库中也查不到（返回 Null），导致</font>**<font style="color:rgb(38, 38, 38);">“回写缓存”机制失效</font>**<font style="color:rgb(38, 38, 38);">。 </font>

<font style="color:rgb(38, 38, 38);">结果就是：Redis 成了摆设，数据库独自承担了所有 IO 压力，直至连接池耗尽。</font>

***

### <font style="color:rgb(38, 38, 38);">二、 方案 A：缓存空对象 (Cache Null Object)</font>

![1764759873714-39bff498-807b-4d04-ac42-af6b5832b052.png](./img/0Zi0xBfzH2bNaDst/1764759873714-39bff498-807b-4d04-ac42-af6b5832b052-411294.png)

**<font style="color:rgb(38, 38, 38);">为什么这是最“实惠”的方案？</font>**<font style="color:rgb(38, 38, 38);"> </font>

<font style="color:rgb(38, 38, 38);">这是一种</font>**<font style="color:rgb(38, 38, 38);">“以毒攻毒”</font>**<font style="color:rgb(38, 38, 38);">的策略。既然数据库返回了 Null，那我们就把这个 Null 当作一个“值”存起来。</font>

* **<font style="color:rgb(38, 38, 38);">核心权衡</font>**<font style="color:rgb(38, 38, 38);">：虽然这会浪费 Redis 的内存来存一堆垃圾 Key，但它换来的是</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">100% 的数据准确性</font>**<font style="color:rgb(38, 38, 38);">（相比布隆过滤器没有误判）。</font>
* **<font style="color:rgb(38, 38, 38);">工程细节</font>**<font style="color:rgb(38, 38, 38);">：注意图中强调的</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">TTL (过期时间)</font>**<font style="color:rgb(38, 38, 38);">。这是防止内存爆炸的关键。我们通常设置一个较短的过期时间（如 300秒），既能挡住短时间内的攻击潮，又能让系统在数据真正产生后能及时更新。</font>

***

### <font style="color:rgb(38, 38, 38);">三、 方案 B：Roaring Bitmap (咆哮位图)</font>

![1764759887932-98a5827b-a82c-4087-9319-ab8fea14679b.png](./img/0Zi0xBfzH2bNaDst/1764759887932-98a5827b-a82c-4087-9319-ab8fea14679b-288244.png)

**<font style="color:rgb(38, 38, 38);">从“位图”到“咆哮位图”的进化：</font>**<font style="color:rgb(38, 38, 38);"> 如果你的 ID 是连续的整数（比如用户 ID），普通的 BitMap 虽然省空间，但在数据稀疏时（比如只有 ID=1 和 ID=100000000）会浪费大量连续的 0。 Roaring Bitmap 的精髓在于</font>**<font style="color:rgb(38, 38, 38);">“分段与自适应”</font>**<font style="color:rgb(38, 38, 38);">：</font>

1. **<font style="color:rgb(38, 38, 38);">分段</font>**<font style="color:rgb(38, 38, 38);">：将 32 位整数切两半，高 16 位作为“桶索引”，低 16 位作为“桶内数据”。</font>
2. **<font style="color:rgb(38, 38, 38);">自适应</font>**<font style="color:rgb(38, 38, 38);">：</font>
   * <font style="color:rgb(38, 38, 38);">如果桶内数据少（稀疏），就用</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Array Container</font>**<font style="color:rgb(38, 38, 38);">（存</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">short</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">数组），省空间。</font>
   * <font style="color:rgb(38, 38, 38);">如果桶内数据多（密集），就自动升级为</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Bitmap Container</font>**<font style="color:rgb(38, 38, 38);">，利用位操作加速查询。 这使得它在保持</font>**<font style="color:rgb(38, 38, 38);">零误判</font>**<font style="color:rgb(38, 38, 38);">的同时，做到了极致的空间压缩。</font>

***

### <font style="color:rgb(38, 38, 38);">四、 方案 C：布谷鸟过滤器 (Cuckoo Filter)</font>

![1764759903709-48271d88-f110-482d-9c50-2a85424316c2.png](./img/0Zi0xBfzH2bNaDst/1764759903709-48271d88-f110-482d-9c50-2a85424316c2-867782.png)

**<font style="color:rgb(38, 38, 38);">它解决了布隆过滤器的什么痛点？</font>**<font style="color:rgb(38, 38, 38);"> 布隆过滤器最大的痛点是</font>**<font style="color:rgb(38, 38, 38);">“不支持删除”。</font>**

<font style="color:rgb(38, 38, 38);">因为多个元素可能共享同一个 Hash 位，删一个可能会误删其他的。 布谷鸟过滤器引入了</font>**<font style="color:rgb(38, 38, 38);">“指纹 (Fingerprint)”</font>**<font style="color:rgb(38, 38, 38);">和</font>**<font style="color:rgb(38, 38, 38);">“双位置机制”</font>**<font style="color:rgb(38, 38, 38);">：</font>

* **<font style="color:rgb(38, 38, 38);">鸠占鹊巢</font>**<font style="color:rgb(38, 38, 38);">：每个元素有两个候选位置。如果两个位置都满了，新来的元素会暴力“踢走”旧元素，旧元素再去它的备用位置。</font>
* **<font style="color:rgb(38, 38, 38);">支持删除</font>**<font style="color:rgb(38, 38, 38);">：因为存储的是指纹而非简单的位标记，我们可以安全地从桶中移除一个指纹，而不会影响其他数据。</font>
* **<font style="color:rgb(38, 38, 38);">空间利用率</font>**<font style="color:rgb(38, 38, 38);">：它可以达到 95% 的空间利用率才开始出现性能下降，这在寸土寸金的内存中非常宝贵。</font>

***

### <font style="color:rgb(38, 38, 38);">五、 终极防线：立体防御架构</font>

![1764759916830-b2ae7612-d3c5-4090-83c4-abafdbef85e8.png](./img/0Zi0xBfzH2bNaDst/1764759916830-b2ae7612-d3c5-4090-83c4-abafdbef85e8-965988.png)

**<font style="color:rgb(38, 38, 38);">不要把鸡蛋放在一个篮子里：</font>**<font style="color:rgb(38, 38, 38);"> 单一的技术手段总有被攻破的可能。成熟的架构应当是</font>**<font style="color:rgb(38, 38, 38);">漏斗型</font>**<font style="color:rgb(38, 38, 38);">的：</font>

1. **<font style="color:rgb(38, 38, 38);">Layer 01 网关层</font>**<font style="color:rgb(38, 38, 38);">：在请求还没进 Java/Go 进程之前，Nginx 或网关就应该拦截掉明显的恶意 IP 和非法的 User-Agent。</font>
2. **<font style="color:rgb(38, 38, 38);">Layer 02 应用层</font>**<font style="color:rgb(38, 38, 38);">：这是成本最低的拦截。例如，如果你的 ID 是 10 位数字，那么所有非数字、长度不对的请求，直接在 Controller 层</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">return</font></code><font style="color:rgb(38, 38, 38);">，根本不需要去烦扰 Redis。</font>
3. **<font style="color:rgb(38, 38, 38);">Layer 03 数据层</font>**<font style="color:rgb(38, 38, 38);">：最后才是我们上面讨论的缓存空对象或过滤器，作为保护数据库的最后一道防波堤。</font>

***

### <font style="color:rgb(38, 38, 38);">六、 决策指南</font>

![1764759928778-5143d2af-9c99-4d1e-bcea-6902c4b48f17.png](./img/0Zi0xBfzH2bNaDst/1764759928778-5143d2af-9c99-4d1e-bcea-6902c4b48f17-676140.png)

**<font style="color:rgb(38, 38, 38);">总结一下选型策略：</font>**

* **<font style="color:rgb(38, 38, 38);">代码最简单，不想引入复杂依赖？</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">-> 选</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">缓存空对象</font>**<font style="color:rgb(38, 38, 38);">（记得加 TTL）。</font>
* **<font style="color:rgb(38, 38, 38);">ID 是整数，且数据量极大（亿级）？</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">-> 选</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Roaring Bitmap</font>**<font style="color:rgb(38, 38, 38);">。</font>
* **<font style="color:rgb(38, 38, 38);">数据需要频繁增删，且对空间敏感？</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">-> 选</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">布谷鸟过滤器</font>**<font style="color:rgb(38, 38, 38);">。</font>
* **<font style="color:rgb(38, 38, 38);">传统业务，读多写少，能容忍少量误判？</font>**<font style="color:rgb(38, 38, 38);"> -> 老牌的 </font>**<font style="color:rgb(38, 38, 38);">布隆过滤器</font>**<font style="color:rgb(38, 38, 38);"> 依然能打。</font>


> 更新: 2025-12-03 19:24:49  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/kp66sgg43r2vap3n>