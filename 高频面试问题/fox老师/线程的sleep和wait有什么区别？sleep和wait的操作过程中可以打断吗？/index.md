# 线程的sleep和wait有什么区别？sleep和wait的操作过程中可以打断吗？

## <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">1. 面试官为什么爱问这个？</font>

<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">这题看似基础，其实暗藏杀机。很多人只会背 API 区别表，但面试官更想听到：</font>

* <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">你对</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">线程调度</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">和</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">锁机制</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">的理解</font>
* <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">你在</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">真实业务场景</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">下的选型思路</font>
* <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">你对</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">异常与中断</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">的处理经验</font>

***

## <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">2. 从语义上看本质区别</font>

* <code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">Thread.sleep()</font>**</code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：让当前线程 “暂停执行” 一段时间，</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">不释放锁</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">。相当于你在会议室占着座位玩手机，不去开会，但座位还是你的。</font>
* <code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">Object.wait()</font>**</code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：让当前线程释放对象锁并进入等待状态，直到被唤醒或超时。相当于你把会议室钥匙交给前台，自己去休息室等，别人可以用会议室。</font>

***

## <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">3. 标准对比表（背下来是基本功）</font>

| **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">对比维度</font>** | <code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">sleep(long)</font>**</code> | <code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">wait()</font>**</code><br/>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>****<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">/</font>****<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>**<code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">wait(long)</font>**</code> |
| :--- | :--- | :--- |
| <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">所属类</font> | <code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">java.lang.Thread</font></code><br/><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">（静态方法）</font> | <code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">java.lang.Object</font></code><br/><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">（实例方法）</font> |
| <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">调用位置</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">任意位置</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">必须在</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">synchronized</font></code><br/><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">代码块 / 方法中</font> |
| <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">是否释放锁</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">❌</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> 不释放</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">✅</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> 释放对象监视器锁</font> |
| <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">唤醒方式</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">时间到自动唤醒 / 被打断</font> | <code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">notify()</font></code><br/><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">/</font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">notifyAll()</font></code><br/><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">/ 被打断 / 超时</font> |
| <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">用途</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">延时执行、降低 CPU 占用</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">线程间通信、条件等待</font> |
| <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">是否可中断</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">✅</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> 可被</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">interrupt()</font></code><br/><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">打断</font> | <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">✅</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> 可被</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">interrupt()</font></code><br/><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">打断</font> |

***

## <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">4. 中断机制的细节</font>

<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">很多人只知道 “可以打断”，但细节才是面试官的陷阱：</font>

### <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">4.1</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">sleep()</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">被打断</font>

* <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">在睡眠中调用</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">interrupt()</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">会抛出</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">InterruptedException</font></code>
* **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">抛出异常后，中断状态会被清除</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">（</font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">Thread.interrupted()</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> 返回 false）</font>

```java
Thread t = new Thread(() -> {
    try {
        Thread.sleep(10000);
    } catch (InterruptedException e) {
        System.out.println("sleep被打断");
        System.out.println("中断状态: " + Thread.currentThread().isInterrupted()); // false
    }
});
t.start();
t.interrupt();
```

### <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">4.2</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">wait()</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">被打断</font>

* <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">同样会抛出</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">InterruptedException</font></code>
* <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">同样会清除中断状态</font>
* <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">但 </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">wait()</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> 还可能遭遇 </font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">虚假唤醒</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">（spurious wakeup），必须在循环中检查条件</font>

```java
synchronized (lock) {
    while (!condition) {
        lock.wait();
    }
}
```

***

## <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">5. 底层实现差异（进阶）</font>

* <code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">sleep()</font>**</code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：是</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">Thread</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">的静态 native 方法，由 JVM 调度器直接挂起线程，不涉及锁释放。</font>
* <code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">wait()</font>**</code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：是</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">Object</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">的方法，必须持有对象监视器（monitor），调用后释放 monitor 并进入条件队列，被唤醒后重新竞争锁。</font>

***

## <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">6. 真实业务场景</font>

### <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">6.1 使用</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">sleep()</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">的场景</font>

* **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">模拟重试机制</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：比如调用第三方 API 失败后，等待 1 秒再重试</font>
* **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">限流</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：在循环中</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">sleep</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">控制 QPS</font>
* **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">测试延迟</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：单元测试中模拟网络延迟</font>

**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">示例</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：</font>

```java
for (int i = 0; i < 3; i++) {
    try {
        if (callThirdPartyAPI()) break;
        Thread.sleep(1000); // 等一秒再重试
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt(); // 重新设置中断状态
        break;
    }
}
```

### <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">6.2 使用</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">wait()</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">的场景</font>

* **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">生产者 - 消费者模型</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：队列空时消费者等待，有数据时被唤醒</font>
* **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">条件等待</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：订单支付成功后，唤醒等待发货的线程</font>
* **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">连接池</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：获取连接时，如果池为空则等待</font>

**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">示例</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">：</font>

```java
synchronized (queue) {
    while (queue.isEmpty()) {
        queue.wait(); // 队列空，等待
    }
    return queue.poll();
}
```

***

## <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">7. 面试官可能追问的点</font>

1. **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">为什么</font>\*\*\*\*<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>**<code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">wait()</font>**</code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>\*\*\*\*<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">必须在同步块中调用？</font>**
   * <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">因为需要先获取对象锁，才能释放锁进入等待状态。</font>
2. <code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">sleep(0)</font>**</code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>\*\*\*\*<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">有什么用？</font>**
   * <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">触发线程重新调度，让同等优先级的线程有机会运行。</font>
3. <code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">interrupt()</font>**</code>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font>\*\*\*\*<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">后，线程状态如何变化？</font>**
   * <code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">sleep</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">/</font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">wait</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">状态 → 抛出异常 → 变为</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">Runnable</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">。</font>
4. **<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">虚假唤醒如何处理？</font>**
   * <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">永远在</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">while</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">循环中检查条件，而不是</font><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> </font><code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">if</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">。</font>

***

## <font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">8. 总结口诀</font>

<code>**<font style="color:rgba(0, 0, 0, 0.5) !important;background-color:rgb(252, 252, 252);">sleep</font>**</code>**<font style="color:rgba(0, 0, 0, 0.5) !important;background-color:rgb(252, 252, 252);"> 占着茅坑睡觉，</font>**<code>**<font style="color:rgba(0, 0, 0, 0.5) !important;background-color:rgb(252, 252, 252);">wait</font>**</code>**<font style="color:rgba(0, 0, 0, 0.5) !important;background-color:rgb(252, 252, 252);"> 把茅坑让出来等人叫。</font>**<font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);">两者都能被打断，但 </font><code><font style="color:rgba(0, 0, 0, 0.5) !important;background-color:rgb(252, 252, 252);">wait</font></code><font style="color:rgb(0, 0, 0);background-color:rgb(252, 252, 252);"> 必须在同步块中，且要防虚假唤醒。</font>


> 更新: 2025-10-12 15:23:17  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/nknsp7gyo5fwtpy4>