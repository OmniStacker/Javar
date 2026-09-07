# 说说String s = new String ("abc") 创建了几个对象？

<font style="color:rgb(38, 38, 38);">在 Java 面试中，这行看似简单的代码是衡量一位开发者对 JVM 内存模型、特别是字符串常量池（String Constant Pool）理解深度的“黄金问题”。如果你的回答仅仅是“一个”或“两个”，那么你可能已经掉入了面试官的陷阱。</font>

**<font style="color:rgb(38, 38, 38);">标准答案是：分情况、分版本讨论。</font>**

<font style="color:rgb(38, 38, 38);">这行代码的核心行为可以分解为两部分：</font>

1. **<font style="color:rgb(38, 38, 38);">字面量</font>\*\*\*\*<font style="color:rgb(38, 38, 38);"> </font>**<code>**<font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">"abc"</font>**</code><font style="color:rgb(38, 38, 38);">：这部分会检查字符串常量池。如果池中不存在等值的 "abc"，就会在池中创建一个。</font>
2. <code>**<font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">new String(...)</font>**</code><font style="color:rgb(38, 38, 38);">：</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">new</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">关键字的行为是明确的——它总会在堆内存中创建一个新的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">对象。</font>

<font style="color:rgb(38, 38, 38);">问题的复杂性来源于字符串常量池（SCP）在不同 JDK 版本中存储位置的变迁，以及 JDK 9 之后底层实现的改变。</font>

## <font style="color:rgb(38, 38, 38);">1. JDK 6 及之前：“永久代”的峥嵘岁月</font>

<font style="color:rgb(38, 38, 38);">在遥远的 JDK 6 时代，JVM 的方法区是使用“永久代”（Permanent Generation）实现的，而字符串常量池就位于其中，完全独立于 Java 堆。</font>

![1760246213547-fbbfbe64-ca61-43c0-a995-64d570ac00da.png](./img/Il5i3aJyMQYm2Tna/1760246213547-fbbfbe64-ca61-43c0-a995-64d570ac00da-952672.png)

#### **<font style="color:rgb(38, 38, 38);">场景一：常量池中【没有】"abc"</font>**

<font style="color:rgb(38, 38, 38);">当代码首次执行时，会创建 </font>**<font style="color:rgb(38, 38, 38);">2 个对象</font>**<font style="color:rgb(38, 38, 38);">。</font>

1. **<font style="color:rgb(38, 38, 38);">检查常量池</font>**<font style="color:rgb(38, 38, 38);">：发现池中没有 "abc"。</font>
2. **<font style="color:rgb(38, 38, 38);">创建池中对象</font>**<font style="color:rgb(38, 38, 38);">：在</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">永久代</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">的常量池中创建一个 "abc" 字符串对象。</font>
3. **<font style="color:rgb(38, 38, 38);">创建堆中对象</font>**<font style="color:rgb(38, 38, 38);">：通过</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">new</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">关键字，在</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Java 堆</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">中再创建一个</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">对象。这个堆中的对象会引用常量池中的 "abc" 对象（在 HotSpot VM 实现中，是共享其内部的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">char[]</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">数组）。</font>

#### **<font style="color:rgb(38, 38, 38);">场景二：常量池中【已有】"abc"</font>**

<font style="color:rgb(38, 38, 38);">如果常量池中已经存在 "abc"（例如，在执行这行代码前有其他代码 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String x = "abc";</font></code><font style="color:rgb(38, 38, 38);">），那么只会创建 </font>**<font style="color:rgb(38, 38, 38);">1 个对象</font>**<font style="color:rgb(38, 38, 38);">。</font>

1. **<font style="color:rgb(38, 38, 38);">检查常量池</font>**<font style="color:rgb(38, 38, 38);">：发现池中已有 "abc"，不做任何操作。</font>
2. **<font style="color:rgb(38, 38, 38);">创建堆中对象</font>**<font style="color:rgb(38, 38, 38);">：通过</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">new</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">关键字，只在</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">Java 堆</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">中创建一个新的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">对象。</font>

***

## <font style="color:rgb(38, 38, 38);">2. JDK 7 / 8：常量池“搬家”入堆</font>

<font style="color:rgb(38, 38, 38);">为了解决永久代内存难以管理和容易溢出的问题，从 JDK 7 开始，Oracle 将字符串常量池从永久代中迁移到了 </font>**<font style="color:rgb(38, 38, 38);">Java 堆</font>**<font style="color:rgb(38, 38, 38);"> 内部。JDK 8 则彻底移除了永久代，代之以元空间（Metaspace）。</font>

<font style="color:rgb(38, 38, 38);">这个改动意味着，此时常量池中的对象和我们普通创建的对象，都共享同一片内存区域——堆。</font>

#### **<font style="color:rgb(38, 38, 38);">场景一：常量池中【没有】"abc"</font>**

<font style="color:rgb(38, 38, 38);">此时仍然创建 </font>**<font style="color:rgb(38, 38, 38);">2 个对象</font>**<font style="color:rgb(38, 38, 38);">，但它们的位置都在 </font>**<font style="color:rgb(38, 38, 38);">Java 堆</font>**<font style="color:rgb(38, 38, 38);"> 中。</font>

1. **<font style="color:rgb(38, 38, 38);">检查常量池</font>**<font style="color:rgb(38, 38, 38);">：发现堆内的常量池区域没有 "abc"。</font>
2. **<font style="color:rgb(38, 38, 38);">创建池中对象</font>**<font style="color:rgb(38, 38, 38);">：在</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">堆的常量池区域</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">创建一个 "abc" 对象。</font>
3. **<font style="color:rgb(38, 38, 38);">创建堆中对象</font>**<font style="color:rgb(38, 38, 38);">：在</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">堆的普通对象区域</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">创建一个新的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">对象。</font>

#### **<font style="color:rgb(38, 38, 38);">场景二：常量池中【已有】"abc"</font>**

<font style="color:rgb(38, 38, 38);">同样，此场景下只会创建 </font>**<font style="color:rgb(38, 38, 38);">1 个对象</font>**<font style="color:rgb(38, 38, 38);">。</font>

1. **<font style="color:rgb(38, 38, 38);">检查常量池</font>**<font style="color:rgb(38, 38, 38);">：发现堆内的常量池区域已有 "abc"。</font>
2. **<font style="color:rgb(38, 38, 38);">创建堆中对象</font>**<font style="color:rgb(38, 38, 38);">：只在</font><font style="color:rgb(38, 38, 38);"> </font>**<font style="color:rgb(38, 38, 38);">堆的普通对象区域</font>**<font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">创建一个新的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">对象。</font>

![1760246259927-0389af2f-d257-4ea2-817b-42de3698e6eb.png](./img/Il5i3aJyMQYm2Tna/1760246259927-0389af2f-d257-4ea2-817b-42de3698e6eb-291824.png)

***

## <font style="color:rgb(38, 38, 38);">3. JDK 9+：字符串压缩与底层变革</font>

<font style="color:rgb(38, 38, 38);">从 JDK 9 开始，Java 引入了**字符串压缩（Compact Strings）**特性。为了节省内存，</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String</font></code><font style="color:rgb(38, 38, 38);"> 的底层存储从 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">char[]</font></code><font style="color:rgb(38, 38, 38);"> 变成了 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font></code><font style="color:rgb(38, 38, 38);">。更重要的是，</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">new String("...")</font></code><font style="color:rgb(38, 38, 38);"> 构造函数的行为也发生了根本性变化：</font>**<font style="color:rgb(38, 38, 38);">它不再共享字面量的底层数组，而是选择复制一份</font>**<font style="color:rgb(38, 38, 38);">。</font>

#### **<font style="color:rgb(38, 38, 38);">场景一：常量池中【没有】"abc"</font>**

<font style="color:rgb(38, 38, 38);">这个版本的答案变得更加复杂，总共涉及 </font>**<font style="color:rgb(38, 38, 38);">2 个 String 对象</font>**<font style="color:rgb(38, 38, 38);"> 和 </font>**<font style="color:rgb(38, 38, 38);">2 个 </font>**<code>**<font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font>**</code>**<font style="color:rgb(38, 38, 38);"> 数组</font>**<font style="color:rgb(38, 38, 38);">。</font>

1. **<font style="color:rgb(38, 38, 38);">常量池部分</font>**<font style="color:rgb(38, 38, 38);">：在堆的常量池区域创建 1 个</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">对象 ("abc") 和 1 个用于存储其内容的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">数组。</font>
2. **<font style="color:rgb(38, 38, 38);">堆对象部分</font>**<font style="color:rgb(38, 38, 38);">：在堆的普通对象区域创建 1 个</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">new String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">对象，并为它</font>**<font style="color:rgb(38, 38, 38);">复制一份全新的</font>\*\*\*\*<font style="color:rgb(38, 38, 38);"> </font>**<code>**<font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font>**</code>**<font style="color:rgb(38, 38, 38);"> </font>\*\*\*\*<font style="color:rgb(38, 38, 38);">数组</font>**<font style="color:rgb(38, 38, 38);">。</font>

#### **<font style="color:rgb(38, 38, 38);">场景二：常量池中【已有】"abc"</font>**

<font style="color:rgb(38, 38, 38);">此时创建 </font>**<font style="color:rgb(38, 38, 38);">1 个 String 对象</font>**<font style="color:rgb(38, 38, 38);"> 和 </font>**<font style="color:rgb(38, 38, 38);">1 个 </font>**<code>**<font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font>**</code>**<font style="color:rgb(38, 38, 38);"> 数组</font>**<font style="color:rgb(38, 38, 38);">。</font>

1. **<font style="color:rgb(38, 38, 38);">常量池部分</font>**<font style="color:rgb(38, 38, 38);">：常量池中已有 "abc"，无需操作。</font>
2. **<font style="color:rgb(38, 38, 38);">堆对象部分</font>**<font style="color:rgb(38, 38, 38);">：在堆的普通对象区域创建 1 个</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">new String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">对象，并为其</font>**<font style="color:rgb(38, 38, 38);">复制一份全新的</font>\*\*\*\*<font style="color:rgb(38, 38, 38);"> </font>**<code>**<font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font>**</code>**<font style="color:rgb(38, 38, 38);"> </font>\*\*\*\*<font style="color:rgb(38, 38, 38);">数组</font>**<font style="color:rgb(38, 38, 38);">。</font>

![1760246288602-ea7315d6-c23e-46a1-9a88-73f3457a10e9.png](./img/Il5i3aJyMQYm2Tna/1760246288602-ea7315d6-c23e-46a1-9a88-73f3457a10e9-926558.png)

***

## <font style="color:rgb(38, 38, 38);">终极总结：面试中的完美回答</font>

<font style="color:rgb(38, 38, 38);">当面试官抛出这个问题时，一个能覆盖所有情况的完美回答应该是结构化的，能充分展现你知识的广度和深度。</font>

![1760246400346-330cb363-7c1c-424d-aaaf-9cdcbcd3ea06.png](./img/Il5i3aJyMQYm2Tna/1760246400346-330cb363-7c1c-424d-aaaf-9cdcbcd3ea06-778778.png)

<font style="color:rgb(38, 38, 38);">你可以这样组织你的回答：</font>

<font style="color:rgb(38, 38, 38);">"关于 </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">String s = new String("abc");</font></code><font style="color:rgb(38, 38, 38);"> 创建了几个对象，这个问题的答案并不是固定的，它取决于代码执行的上下文以及所处的 JDK 版本。</font>

1. **<font style="color:rgb(38, 38, 38);">在 JDK 6 及以前</font>**<font style="color:rgb(38, 38, 38);">，由于字符串常量池在永久代，如果常量池中没有 "abc"，会创建 2 个对象（一个在永久代，一个在堆）；如果已有，则只在堆上创建 1 个。</font>
2. **<font style="color:rgb(38, 38, 38);">在 JDK 7 和 8 中</font>**<font style="color:rgb(38, 38, 38);">，常量池被移到了堆内。此时如果池中没有 "abc"，同样是创建 2 个对象，但它们都在堆内；如果已有，则还是只创建 1 个堆对象。</font>
3. **<font style="color:rgb(38, 38, 38);">从 JDK 9 开始</font>**<font style="color:rgb(38, 38, 38);">，由于字符串压缩和底层实现的改变，</font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">new String</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">会复制一个新的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">数组。因此，如果池中没有 "abc"，会创建 2 个 String 对象和 2 个</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">数组；如果已有，则会创建 1 个 String 对象和 1 个新的</font><font style="color:rgb(38, 38, 38);"> </font><code><font style="color:rgb(38, 38, 38);background-color:rgba(175, 184, 193, 0.2);">byte[]</font></code><font style="color:rgb(38, 38, 38);"> </font><font style="color:rgb(38, 38, 38);">数组。"</font>

<font style="color:rgb(38, 38, 38);">这样的回答，不仅准确，更能体现出你对 JVM 技术演进的深刻理解，无疑会给面试官留下深刻的印象。</font>


> 更新: 2025-10-12 13:20:16  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/bq3om0knf4g7w02o>