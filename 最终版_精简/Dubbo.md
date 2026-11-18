# Dubbo 知识汇总

Dubbo 是 Java 微服务体系中常见的远程调用框架。本文按"是什么 → 为什么需要 → 怎么用"的顺序，梳理它的主要能力、集群容错与负载均衡策略、服务消费者配置，以及异步调用、注册中心、线程模型、SPI、泛化调用等常用特性。

阅读前提：能写 Java 的增删改查代码、了解 Spring 的基本用法（Bean、注解）即可，不要求读过框架源码。文中概念首次出现时会先给一句话解释；示例配置以 Dubbo 3.x 的写法为主，涉及 2.x 差异的地方会单独标注。

## 本文导读

- [1. Dubbo 概述](#1-dubbo-概述)：它是什么、解决什么问题、一次调用涉及哪些角色
- [2. 集群容错策略](#2-集群容错策略)：调用失败后是重试、报错还是忽略
- [3. 负载均衡策略](#3-负载均衡策略)：多个提供者时，这次请求发给谁
- [4. 服务配置](#4-服务配置)：消费者端常用参数、默认值与配置示例
- [5. 高级特性](#5-高级特性)：异步、治理、降级、注册中心、版本兼容、线程模型、SPI、泛化调用
- [6. 总结](#6-总结)：一页速查

## 1. Dubbo 概述

这一章先回答"它是什么、为什么要有它"，再补上一次远程调用会涉及哪些角色。后面的容错和负载均衡，都是围绕这些角色展开的。

### 1.1 什么是 Dubbo

Dubbo 是一个高性能、轻量级的 Java RPC 框架，用于构建可扩展的分布式应用，并提供服务治理能力。它最初由阿里巴巴开源，后捐献给 Apache 软件基金会，现为 Apache 顶级项目（Apache Dubbo）。

先解释两个术语：

- **RPC（Remote Procedure Call，远程过程调用）**：让程序像调用本地方法一样调用另一台机器上的方法。网络连接、序列化（把 Java 对象转成可传输的字节流）、异常传递等细节都由框架完成。
- **分布式应用**：一个系统被拆成多个进程、部署在多台机器上，彼此通过网络协作。

一条生活化的比喻：调用远程服务就像给隔壁工位的同事发消息——你只管把消息发出去、等回复，不需要知道他坐在哪一层楼、消息又是怎么传过去的。

版本上需要区分两类：Dubbo 2.x 以接口级服务发现为主；Dubbo 3.x 引入应用级服务发现与新的 Triple 协议（面向云原生场景的新通信协议），同时保持对 2.x 用法的兼容。具体版本的差异以所用版本的官方发布说明为准。

### 1.2 Dubbo 的主要作用

当系统从单体拆成多个服务后，"怎么调用、调用谁、调用失败怎么办"如果每个团队各写一套，成本高、故障率也高。Dubbo 把这些通用能力收进框架，业务代码只需要关注接口本身。

1. **远程调用**：以远程调用的方式访问部署在不同机器、甚至不同数据中心的服务。
2. **负载均衡**：内置多种算法，把客户端的请求分摊给多个提供者，避免个别实例被打满。
3. **服务注册与发现**：通过注册中心维护服务地址等元数据，消费者据此拿到可用提供者列表，提供者上下线时清单自动更新。
4. **服务治理**：支持服务降级、容错、流量控制等，保障系统稳定。
5. **跨语言调用**：为不同语言实现的服务提供一致的调用方式与通信协议。
6. **配置管理**：通过配置中心动态下发参数，改配置不必重新部署。
7. **性能监控**：查看调用量、响应时间等指标，为容量评估和优化提供依据。
8. **分层架构**：把通信层、服务层、注册层等分离，各模块可以独立演进与替换（这也是它能把协议、序列化、注册中心做成可插拔扩展的基础）。

### 1.3 一次调用涉及的角色

- **Provider（服务提供者）**：把接口实现暴露为远程服务的一方。
- **Consumer（服务消费者）**：调用远程服务的一方。
- **Registry（注册中心）**：保存服务地址清单的"电话簿"，提供者上线时写入，消费者订阅变更。
- **Monitor（监控中心）**：统计调用次数、耗时等指标，属于可选组件。
- **Container（容器）**：负责启动和运行服务的进程环境，例如 Spring 容器。

一次典型调用的流程：

1. 提供者启动后，把自身地址注册到注册中心。
2. 消费者启动时订阅对应接口，从注册中心获取可用提供者列表并缓存在本地。
3. 消费者发起调用时，先经路由筛选、再由负载均衡选出一个提供者，然后通过网络发送请求。
4. 提供者执行业务逻辑并返回结果；若本次失败，则交给集群容错策略处理。
5. 调用数据按需上报监控中心。

## 2. 集群容错策略

"集群"在这里指同一个服务有多个提供者实例。当某次调用超时或报错时，框架是换一台机器再试、还是直接报错，这就是容错策略回答的问题。比喻：给同事打电话没人接，是换个人再打一遍，还是直接放弃并上报。

### 2.1 六种内置策略

| 策略（cluster 取值） | 失败后的行为 | 适用场景 |
| --- | --- | --- |
| failover（缺省） | 自动切换其他提供者重试，直到成功或重试次数用完 | 读操作、提供者较多且偶发短暂故障 |
| failfast | 只发起一次调用，失败立即报错，不重试 | 非幂等的写操作（如新增记录）、响应时间要求高 |
| failsafe | 失败只记录异常、不抛出，返回空结果 | 写审计日志等允许失败的旁路操作 |
| failback | 后台记录失败请求，定时重发 | 消息通知、提供者状态时好时坏 |
| forking | 并行调用多个提供者，只要一个成功就返回 | 实时性要求高的读操作，但更消耗资源 |
| broadcast | 逐个调用所有提供者，任意一台报错就报错 | 通知所有节点刷新本地缓存、日志等资源 |

几个容易记错的点：

- **failover 的重试次数由 `retries` 控制，缺省为 2，且不包含第一次调用**，也就是最多总共调用 3 次。`retries` 只在 failover、failback 下生效。
- **broadcast 是"任意一台报错则报错"**，不是"任一成功即返回"；它的目的是通知所有提供者，而不是挑一个返回。
- **forking 的最大并行数由 `forks` 控制，缺省为 2**。
- 重试会带来更长延迟，也可能让写操作重复执行，因此写接口通常把 `retries` 设为 0。

### 2.2 配置方式

`cluster` 属性在提供者端和消费者端都能配置，实践中更常配在消费者端，因为它决定"我调用失败后怎么办"。

```xml
<dubbo:reference id="demoService" interface="com.example.DemoService"
                 cluster="failfast" retries="0" timeout="2000" />
```

```yaml
dubbo:
  consumer:
    cluster: failover
    retries: 2
```

```java
@DubboReference(cluster = "failover", retries = 2, timeout = 2000)
private DemoService demoService;
```

配置优先级：方法级高于接口级，接口级高于全局（`dubbo:consumer` / `dubbo:provider` 的缺省值）。

### 2.3 进阶了解（可跳过）

初学可略过本节。

- broadcast 支持 `broadcast.fail.percent`（Dubbo 2.7.10 及以上版本）：取值 0～100，失败节点比例达到该值时就停止调用其余节点并抛异常；缺省情况下要等所有节点都失败才抛异常。它只影响"是否继续调用其他节点"，不改变"任意一台报错则报错"的结果。
- 除上述六种外，Dubbo 还提供 available（只调一个当前可用实例）、mergeable（与 group 配合，把多个分组的结果合并返回）、zone-aware（多注册中心场景下的选址）等集群模式，需要时查阅官方文档。

## 3. 负载均衡策略

一个接口有 3 个提供者实例时，每次调用该发给谁？负载均衡（Load Balance）负责在候选实例中挑一个，目标是把请求分摊开、避免某些实例被打满。比喻：超市开多个收银台，顾客去哪个队由引导员分配——分得好，各队长度接近。

Dubbo 采用的是**客户端负载均衡**：由消费端根据地址列表和算法算出目标实例，而不是靠一个中间代理转发。

### 3.1 五种内置策略

| 策略（loadbalance 取值） | 选择规则 | 特点与适用场景 |
| --- | --- | --- |
| random（缺省） | 按权重随机挑选 | 调用量大时分布均匀，便于动态调整权重；缺点是慢实例可能持续积压请求 |
| roundrobin | 按权重轮询，借鉴 Nginx 的平滑加权轮询算法 | 适合实例性能相近、希望请求均匀的场景，也能避免"大权重节点被集中调用" |
| leastactive | 优先选活跃调用数最少的实例，活跃数 = 已发出请求数 − 已返回响应数 | 可理解为选"堆积量最小"的实例，让慢节点少收请求；相同活跃数之间按权重随机 |
| shortestresponse | 在最近一个滑动窗口（缺省 30 秒）内，优先选平均响应时间最短的实例 | 更关注响应速度，但可能让流量过度集中到少数强节点 |
| consistenthash | 按调用参数做哈希选实例，相同参数的请求落到同一提供者 | 适合有状态请求（如需命中本地缓存）；提供者下线时靠虚拟节点把受影响的请求平摊给其他实例 |

需要注意：**权重（weight）是各算法共用的参数，不是独立的策略名**。把"加权随机 / 加权轮询 / 加权最小活跃数"当作三个单独的策略去配置是不成立的——它们仍然分别通过 `random`、`roundrobin`、`leastactive` 配置，再配合 `weight` 调整比例。

### 3.2 配置方式

```xml
<!-- 消费者端：接口级 -->
<dubbo:reference interface="com.example.DemoService" loadbalance="roundrobin" />
```

```yaml
dubbo:
  consumer:
    loadbalance: random
```

```java
@DubboReference(loadbalance = "leastactive")
private DemoService demoService;
```

提供者可以设置权重，权重越高被选中的比例越大：

```xml
<dubbo:service interface="com.example.DemoService" ref="demoServiceImpl" weight="200" />
```

### 3.3 进阶了解（可跳过）

初学可略过本节。

- **平滑加权轮询**：若有 A、B、C 三节点、权重为 3:2:1，最朴素的轮询会形成 A A A B B C 的集中调用。Dubbo 借鉴 Nginx 的算法，在每轮把"当前权重"累加、选中后减去总权重，最终调用序列被摊平为 A、B、A、C、B、A 这样的分布，既均匀又平滑。
- **一致性哈希的两个参数**：缺省只对第一个参数做哈希，需要改时配置 `hash.arguments`（如 `0,1` 表示用前两个参数）；缺省使用 160 份虚拟节点，可用 `hash.nodes` 调整（如 320）。

## 4. 服务配置

这一节列出消费者端最常用的配置项与缺省值，照着填就能跑起来；同时说明超时、重试、容错三者如何配合，避免上线后才发现"请求被重复执行"。

### 4.1 服务消费者常用参数

| 参数 | 作用 | 缺省值 |
| --- | --- | --- |
| `id` | 服务引用在容器中的 Bean 名称 | 未配置时按接口名生成 |
| `interface` | 服务接口全限定名（包名 + 类名），必填 | 无 |
| `version` | 服务版本，需与提供者一致 | 无 |
| `group` | 服务分组，同一接口有多套实现时用于区分 | 无 |
| `timeout` | 调用超时时间，单位毫秒 | 1000 |
| `retries` | 重试次数，**不含第一次调用**，不需要重试设为 0 | 2 |
| `cluster` | 集群容错策略 | failover |
| `loadbalance` | 负载均衡策略 | random |
| `check` | 启动时检查提供者是否存在，true 表示不存在直接报错 | true |

### 4.2 配置示例

```xml
<dubbo:application name="demo-consumer" />
<dubbo:registry address="zookeeper://127.0.0.1:2181" />

<dubbo:consumer timeout="3000" retries="1" />

<dubbo:reference id="demoService" interface="com.example.DemoService"
                 version="1.0.0" cluster="failover" loadbalance="random" />
```

```yaml
dubbo:
  application:
    name: demo-consumer
  registry:
    address: zookeeper://127.0.0.1:2181
  protocol:
    name: dubbo
    port: 20880
  consumer:
    timeout: 3000
    retries: 1
```

```java
@DubboReference(version = "1.0.0", timeout = 3000, retries = 1)
private DemoService demoService;
```

### 4.3 超时、重试与容错怎么配合

- 对响应时间敏感、不能等：用 failfast，失败立即报错，不再排队等重试。
- 允许失败、不希望影响主流程：用 failsafe，失败只记日志。
- 希望故障恢复后自动补发：用 failback。
- 写操作（新增、扣减等）：把 `retries` 设为 0，配合合理的 `timeout`，避免超时后重试造成重复数据。
- 缺省 1000 毫秒的超时对多数线上接口偏短，实践中常按接口实际耗时分布调到 2～3 秒（经验值，需结合压测结果确定）。

## 5. 高级特性

这一节把日常开发最常打交道的几项能力放在一起：异步调用、服务治理与降级、注册中心选择、版本兼容、线程模型、SPI 扩展和泛化调用。每项按"是什么、为什么、怎么用"展开。

### 5.1 异步调用

**是什么**：消费者发出请求后不阻塞等待结果，先返回一个"凭证"（Future），结果回来后再通过回调或取值获取。

**为什么需要**：并行调用多个下游服务时，总耗时可从"相加"降为"取最大"；也能避免业务线程长时间占着不放。

**怎么用**：Dubbo 从 2.7.0 起以 `CompletableFuture` 为基础提供异步编程接口。更早期的版本使用 `AsyncContext`，现已不推荐，新项目不必使用。

```java
// 方式一：服务接口直接返回 CompletableFuture
CompletableFuture<String> future = asyncService.sayHello("world");

future.whenComplete((retValue, exception) -> {
    if (exception != null) {
        exception.printStackTrace();
    } else {
        System.out.println("Response: " + retValue);
    }
});
```

若接口仍是同步签名，可以在方法级打开异步：

```xml
<dubbo:reference id="asyncService" interface="com.example.AsyncService">
    <dubbo:method name="sayHello" async="true" />
</dubbo:reference>
```

```java
asyncService.sayHello("world");                  // 此调用立即返回 null
CompletableFuture<String> helloFuture =
        RpcContext.getContext().getCompletableFuture();
helloFuture.whenComplete((v, t) -> System.out.println(v));
```

**注意事项**：

- 异步结果与调用线程绑定。`RpcContext` 是线程上下文，切到别的线程后再取可能拿到空值，需要显式把 Future 或上下文传过去。
- 超时要照常设置，否则异步只是把"等待"挪到了另一个地方。
- 若只想发出请求、完全忽略返回值，可配置 `return="false"`（异步总是不等待返回），减少 Future 对象的创建与管理开销。

### 5.2 服务治理

**解决的问题**：流量控制（限流、并发控制）、服务降级、服务熔断、服务路由（按标签、区域、灰度分流）。

**常用手段**：动态配置（配置中心下发、不重启生效）、权重调整、黑白名单、路由规则、服务分组。

### 5.3 服务降级

**触发条件**：提供者不可用、调用超时、熔断打开、流量超过阈值。

**降级策略**：返回默认值、返回缓存数据、返回兜底数据。

**在 Dubbo 中的入口是 `mock`**：在消费者端为引用配置 mock 后，出现非业务异常（如超时、网络异常）时执行 Mock 逻辑；业务异常（提供者正常返回的错误）不走 Mock。常见做法是让 Mock 直接返回空值或兜底对象，例如在 mock 表达式中写 `return null`（不同版本的语法细节略有差异，以所用版本文档为准）。

### 5.4 服务注册中心

| 注册中心 | 特点 | 适用场景 |
| --- | --- | --- |
| Nacos | 同时提供服务发现与配置管理；可通过不同实现支持 AP（可用性优先）与 CP（一致性优先）两种一致性模型，与 Spring Cloud Alibaba 集成良好 | 目前生产中较常见的选择，尤其已使用阿里系技术栈时 |
| Zookeeper | 成熟的分布式协调服务，基于 ZAB 协议，偏强一致（CP） | 对一致性要求高、已有 ZK 运维能力的场景 |
| Redis | 用 Key/Map 存地址、用发布订阅推送变更，自 Dubbo 2.1.0 起支持；依赖心跳检测脏数据，需要各节点时间同步 | 轻量场景或已有 Redis 的团队；官方文档对其长期可靠性有保留说明 |
| Multicast | 不需要中心节点，广播地址相同即可互相发现 | 受网络结构限制，只适合小规模应用或开发测试 |

```yaml
dubbo:
  registry:
    # 按环境换成 nacos://、zookeeper://、multicast:// 等
    address: zookeeper://127.0.0.1:2181
```

### 5.5 版本兼容性

**问题**：接口增删参数后，旧消费者与新提供者可能不兼容；同一接口还可能同时存在多套实现（如灰度版本、不同租户的定制）。

**解决方案**：

- **版本号隔离**：提供者以 `version="1.0.0"`、`version="2.0.0"` 暴露不同实现，消费者只调用匹配的版本。
- **分组隔离**：用 `group` 区分同一接口的不同实现，实现灰度或环境隔离。
- **参数兼容性设计**：新增字段用可选类型、不改已有字段语义；需要改签名时新增方法而不是修改原方法。
- **泛化调用**：没有接口 jar 时也能发起调用（见 5.8）。

```java
@DubboReference(version = "2.0.0", group = "gray")
private DemoService demoService;
```

### 5.6 线程模型

**是什么**：Dubbo 提供者一侧有两类线程——**IO 线程**负责网络读写和事件处理（缺省数量为 CPU 核数 + 1），**业务线程池**负责执行服务实现（缺省为 fixed 类型、200 个线程）。请求缺省会派发到业务线程池执行。

**为什么需要**：IO 线程必须尽快回到"接收下一个请求"的状态。如果在 IO 线程里查数据库，它会一直阻塞，后续请求都进不来，吞吐量会明显下降。

**怎么配**（协议级别）：

```xml
<dubbo:protocol name="dubbo" port="20880"
                dispatcher="all" threadpool="fixed" threads="200" />
```

派发策略 `dispatcher`：

| 取值 | 含义 |
| --- | --- |
| all（dubbo 协议缺省） | 请求、响应、连接事件、心跳等全部派发到线程池 |
| direct | 全部在 IO 线程上直接执行，不进线程池 |
| message | 只有请求/响应进线程池，连接事件、心跳在 IO 线程执行 |
| execution | 只有请求进线程池，响应、连接事件、心跳在 IO 线程执行 |
| connection | 连接事件在 IO 线程排队执行，其他消息派发到线程池 |

线程池类型 `threadpool`：fixed（缺省，固定大小、启动即建）、cached（空闲一分钟回收）、limited（只增不减，避免缩容后突发流量导致性能问题）、eager（任务数超过核心线程数时优先扩容到最大线程数，满了才入队）。

补充两个相关缺省值：Dubbo 协议缺省端口为 20880；请求与响应数据包大小上限缺省为 8 MB（超出会报错，大报文场景需要调整 `payload`）。

### 5.7 SPI 机制

**是什么**：SPI（Service Provider Interface，服务提供者接口）是一种"接口 + 配置文件"的扩展机制——接口只定义能力，实现类写在配置文件里，运行时可替换、可按名字挑选。

**为什么需要**：Dubbo 的协议、序列化、负载均衡、注册中心等组件都是可替换的。框架自己不写死实现，第三方按同一套约定接入即可，这也是第 1.2 节"分层架构"能落地的前提。

**和 JDK 自带 SPI 的区别**（Dubbo 做了增强）：按需加载（用到才实例化，JDK 原生 SPI 会一次性加载全部实现）、支持依赖注入（IOC）与包装类增强（AOP）、可按名字动态选择实现，且扩展实例是单例。

**怎么用**：

1. 在接口上用 `@SPI` 标注这是一个扩展点，可顺带指定缺省实现名。

```java
@SPI("demo")
public interface DemoExtension {
    void doSomething();
}
```

2. 在实现所在 jar 的 `META-INF/dubbo/` 目录下，以"接口全限定名"作为文件名，内容写成 `名字=实现类全限定名`，一行一个。

```text
demo=com.example.DemoExtensionImpl
```

3. 通过 `ExtensionLoader` 按名字取实现。

```java
DemoExtension ext = ExtensionLoader
        .getExtensionLoader(DemoExtension.class)
        .getExtension("demo");
ext.doSomething();
```

### 5.8 泛化调用

**是什么**：消费者没有服务接口的 jar 包（不知道参数、返回值对应的 Java 类型），改用 `GenericService`，按"方法名 + 参数类型名 + 参数值"的方式调用；参数中的 POJO 用 Map 表示，返回值里的 POJO 也会自动转成 Map。

**为什么需要**：通用服务测试平台、网关、跨语言或跨系统集成等场景，无法引入每个业务方的接口 jar。

**怎么用**：

```xml
<dubbo:reference id="demoService" interface="com.example.DemoService" generic="true" />
```

```java
GenericService demoService = (GenericService) context.getBean("demoService");

Map<String, Object> person = new HashMap<>();
person.put("name", "user_a");
person.put("password", "pwd_a");

// 参数类型按全限定名传字符串，POJO 参数直接传 Map
Object result = demoService.$invoke(
        "findPerson",
        new String[]{"com.example.Person"},
        new Object[]{person});
```

注意：转 Map 时如果字段类型是接口、或者泛型信息丢失，需要额外放一个 `class` 键指定具体的实现类，否则提供者无法还原参数类型。

## 6. 总结

| 主题 | 要点 |
| --- | --- |
| Dubbo 概述 | 高性能 Java RPC 框架，提供远程调用、负载均衡、注册发现、治理等能力；核心角色是提供者、消费者、注册中心、监控中心 |
| 集群容错 | failover（缺省，`retries` 缺省 2 且不含首次调用）、failfast、failsafe、failback、forking（`forks` 缺省 2）、broadcast（任一报错即报错） |
| 负载均衡 | random（缺省）、roundrobin、leastactive、shortestresponse、consistenthash；权重是参数而非独立策略 |
| 服务配置 | 消费者常用 `id`、`interface`、`version`、`group`、`timeout`（1000ms）、`retries`（2）、`cluster`（failover）、`loadbalance`（random）、`check`（true） |
| 高级特性 | 异步调用（`CompletableFuture`）、服务治理、服务降级（`mock`）、注册中心（Nacos / Zookeeper / Redis / Multicast）、版本兼容、线程模型（dispatcher、threadpool、threads）、SPI 扩展、泛化调用 |

## 参考资料

- Apache Dubbo 官方文档：用户指南（集群容错、负载均衡、线程模型、异步调用、泛化调用）
- Apache Dubbo 官方文档：配置参考手册（dubbo:reference、dubbo:consumer、dubbo:protocol 的缺省值）
- Apache Dubbo 官方文档：注册中心参考手册（Redis、Multicast）、扩展点开发指南
- Apache Dubbo 项目主页（Apache 软件基金会顶级项目）
