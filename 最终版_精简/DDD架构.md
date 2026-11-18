# DDD 领域驱动设计

> 本文面向 1 年以内经验的 Java 开发者。每个概念都按「是什么 → 为什么需要 → 怎么用」展开，
> 尽量用生活化的例子代替抽象定义。

## 本文导读

- [一、DDD 到底解决什么问题](#一ddd-到底解决什么问题)
- [二、领域模型：贫血模型与充血模型](#二领域模型贫血模型与充血模型)
- [三、DDD 的核心构件](#三ddd-的核心构件)
- [四、分层架构：把业务逻辑放在中间](#四分层架构把业务逻辑放在中间)
- [五、持久化：仓库与工厂](#五持久化仓库与工厂)
- [六、CQRS：读写分开建模](#六cqrs读写分开建模)
- [七、在微服务中落地 DDD](#七在微服务中落地-ddd)
- [八、速查表](#八速查表)

---

## 一、DDD 到底解决什么问题

**一句话定义**：领域驱动设计（Domain-Driven Design，DDD）是一套以**业务领域模型**为核心的
软件设计方法，由 Eric Evans 在 2003 年的著作《Domain-Driven Design》中系统提出。

**它针对的是「业务复杂」而非「技术复杂」。** 软件复杂度大致有两个来源：

| 复杂度类型 | 举例 | DDD 是否有帮助 |
| --- | --- | --- |
| 本质复杂度 | 计费规则随套餐、地区、促销叠加变化；订单状态机分支极多 | 有帮助 |
| 偶然复杂度 | 换一个 ORM、加一台缓存、调一次 JVM 参数 | 帮助不大 |

如果你的系统本质就是一张表的增删改查（后台管理、配置页面），强行套 DDD 只会增加无谓的
分层和跳转。DDD 的价值在**规则多、变化快、多人协作**的业务系统里。

> **打个比方**：DDD 像是给一家餐厅制定「岗位说明书」。它先规定谁负责接单、谁负责烹饪、
> 谁负责结账，再规定哪些话只能在哪类岗位之间说。菜谱（业务规则）写清楚、职责边界划清楚，
> 人多了才不会乱。但如果只是街边一个只卖煎饼的小摊，硬要分五个岗位，反而更慢。

**核心思想有三条**：

1. **用模型承载业务规则**——业务规则不是散落在 Service 里的 if-else，而是收敛到模型对象上。
2. **统一语言（Ubiquitous Language）**——开发、产品、业务方使用同一套词汇，代码里的类名就叫
   `订单`、`退款单`，而不是 `OrderData`、`BizBean`。
3. **划清边界（限界上下文）**——大系统拆成多个自洽的小模型，而不是一个大而全的模型。

---

## 二、领域模型：贫血模型与充血模型

先明确术语：**领域模型**就是对业务概念的抽象表达——把「订单」「账户」「库存」这些真实世界里
的东西，变成代码里的对象。按「对象里有没有业务行为」区分，有两种风格。

### 2.1 贫血模型（Anemic Domain Model）

对象里**只有数据**（字段 + getter/setter），所有业务逻辑放在 Service 层。数据与行为是分离的，
本质上仍是**面向过程**的写法。

```java
// 只有数据，没有任何业务规则
public class Account {
    private Long id;
    private BigDecimal balance;

    public BigDecimal getBalance() { return balance; }
    public void setBalance(BigDecimal balance) { this.balance = balance; }
}

// 业务规则全部堆在 Service 里
public class AccountService {
    public void withdraw(Long accountId, BigDecimal amount) {
        Account account = accountRepository.findById(accountId);
        if (account.getBalance().compareTo(amount) < 0) {
            throw new InsufficientBalanceException();
        }
        account.setBalance(account.getBalance().subtract(amount));
        accountRepository.save(account);
    }
}
```

- **优点**：简单直观、上手快；分层清晰（数据 / 逻辑各归各处）；团队水平参差时也不容易写乱。
- **缺点**：任何一处要扣款，都得记得先查余额——**规则靠调用方自觉**，漏写一次就是资损 Bug；
  业务复杂后 Service 会膨胀成几千行的「上帝类」。

> **注意**：Martin Fowler 在 2003 年将贫血模型列为**反模式（anti-pattern）**，理由是它
> 「付出了领域模型的全部成本，却没有拿到任何好处」。但要客观看待：在 CRUD 型系统里，
> 贫血模型 + 事务脚本（Transaction Script）恰恰是性价比最高的选择。是否贫血，取决于业务复杂度，
> 与「水平高低」无关。

### 2.2 充血模型（Rich Domain Model）

对象里**既有数据也有行为**，业务规则封装在对象内部，外部只能调用对象暴露的方法。

```java
public class Account {
    private Long id;
    private BigDecimal balance;

    // 行为和数据绑在一起：想扣钱，只能走这个方法
    public void withdraw(BigDecimal amount) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("取款金额必须大于 0");
        }
        if (balance.compareTo(amount) < 0) {
            throw new InsufficientBalanceException();
        }
        this.balance = balance.subtract(amount);
    }

    public BigDecimal getBalance() { return balance; }
}
```

此时 Service 只负责**编排**（取对象、调方法、存回去），不再承载规则：

```java
public class AccountService {
    public void withdraw(Long accountId, BigDecimal amount) {
        Account account = accountRepository.findById(accountId);
        account.withdraw(amount);          // 规则在对象内部
        accountRepository.save(account);
    }
}
```

- **优点**：规则只有一份，「忘记校验」不可能发生；符合面向对象封装；复杂业务更易演进。
- **缺点**：要求开发者一开始就想清楚模型边界；对象职责过载时会变成「什么都懂一点」的巨型类；
  与 ORM 的懒加载、无参构造等机制配合时需要额外注意。

### 2.3 两者对比

| 维度 | 贫血模型 | 充血模型 |
| --- | --- | --- |
| 编程范式 | 面向过程 | 面向对象 |
| 业务规则位置 | Service 层 | 领域对象内部 |
| 规则一致性 | 靠调用方自觉，易漏 | 天然收口，难绕过 |
| 上手成本 | 低 | 较高，需先设计模型 |
| 适用场景 | 简单 CRUD、报表类、后台管理 | 规则多、变化频繁的核心域 |
| 典型风险 | Service 膨胀、规则重复 | 对象臃肿、与 ORM 冲突 |

### 2.4 怎么选：三个判断标准

1. **规则会不会变**：一年要改好几次的核心域（计价、风控、库存扣减）→ 偏充血。
2. **规则会不会被多处调用**：同一规则被 3 个以上入口调用 → 必须收口到对象里。
3. **团队是否熟悉**：不熟悉时可以先从「Service 编排 + 领域对象只做校验方法」这种中间形态过渡，
   不必一步到位。

> **实践建议**：同一个系统里允许两种风格共存——核心域用充血，边缘的配置管理用贫血。
> 强行统一反而是过度设计。

---

## 三、DDD 的核心构件

DDD 用一组构件来描述模型。下面四个最常用。

### 3.1 实体与值对象

**实体（Entity）**：有唯一标识，标识不变则「还是同一个东西」，属性可以变。

```java
public class Order {
    private final OrderId id;       // 唯一标识，创建后不可变
    private OrderStatus status;     // 状态可以变：待支付 -> 已支付

    public void pay() {
        if (status != OrderStatus.PENDING_PAYMENT) {
            throw new IllegalStateException("当前状态不可支付");
        }
        this.status = OrderStatus.PAID;
    }
}
```

**值对象（Value Object）**：没有唯一标识，**靠属性值判断相等，且创建后不可变**。

```java
// 金额：100 元和另一张 100 元是等价的，不需要区分「哪一张」
public final class Money {
    private final BigDecimal amount;
    private final String currency;

    public Money(BigDecimal amount, String currency) {
        this.amount = amount;
        this.currency = currency;
    }

    public Money add(Money other) {
        if (!this.currency.equals(other.currency)) {
            throw new IllegalArgumentException("币种不同不能相加");
        }
        return new Money(this.amount.add(other.amount), currency);  // 返回新对象
    }
    // equals/hashCode 基于 amount + currency
}
```

| 维度 | 实体 | 值对象 |
| --- | --- | --- |
| 判别相等的方式 | 比较唯一标识（如订单号） | 比较全部属性值 |
| 可变性 | 状态可变，标识不变 | 不可变，需要变化时创建新对象 |
| 生命周期 | 有独立生命周期（创建→更新→删除） | 依附于实体，随用随建 |
| 典型例子 | 订单、用户、账户 | 金额、地址、坐标、时间段 |

> **常见误区**：值对象「属性相同即视为不同对象」是错误理解。两张 100 元纸币在业务上没有区别，
> 所以 `new Money(100,"CNY").equals(new Money(100,"CNY"))` 应当为 `true`。

### 3.2 聚合与聚合根

**聚合（Aggregate）**是一组**必须保持整体一致**的对象的集合；**聚合根（Aggregate Root）**是
这个集合对外唯一的入口。

> **打个比方**：一家门店（聚合）里有店长、店员、收银机（内部对象），但对外只认「店长」一个
> 联系人（聚合根）。外人要调货、要投诉，一律找店长，不能直接去翻收银机。这样门店内部怎么调整，
> 外部都不受影响。

```java
// 聚合根：订单。外部只能通过它操作订单项
public class Order {
    private final OrderId id;
    private final List<OrderItem> items = new ArrayList<>();
    private Money totalAmount;

    public void addItem(Product product, int quantity) {
        if (quantity <= 0) throw new IllegalArgumentException("数量必须大于 0");
        items.add(new OrderItem(product, quantity));
        recalculateTotal();          // 内部一致性由聚合根保证
    }

    public void removeItem(OrderItem item) {
        items.remove(item);
        recalculateTotal();
    }

    private void recalculateTotal() {
        this.totalAmount = items.stream()
                .map(OrderItem::subtotal)
                .reduce(new Money(BigDecimal.ZERO, "CNY"), Money::add);
    }
    // 不暴露 items 的 setter，避免外部破坏一致性
}
```

**设计聚合的六条规则**：

1. **识别聚合**：把业务上必须「同生共死」的对象划到一起（订单 + 订单项）。
2. **选聚合根**：选具有全局唯一标识、且能承担一致性责任的对象（订单）。
3. **内部强一致**：聚合内部要么全部成功、要么全部失败，由聚合根协调；跨聚合只保证最终一致。
4. **禁止外部直达内部**：外部只能持有聚合根的引用，不能绕过它修改内部对象。
5. **聚合要小**：一个聚合尽量只包含一个实体 + 若干值对象，聚合越大并发冲突越多。
6. **查询不必走聚合根**：只为「会改变状态」的操作设边界，纯统计类查询可以直接读库。

### 3.3 领域服务

有些业务逻辑**天生不属于某一个对象**，跨多个聚合，这时用**领域服务（Domain Service）**承载。

> **打个比方**：转账不属于「付款人」也不属于「收款人」，它是两个账户之间的协作，
> 所以需要柜台（领域服务）来协调。

```java
// 无状态：不保存业务数据，每次调用传入所需对象
public class TransferService {
    public void transfer(Account from, Account to, Money amount) {
        from.withdraw(amount);      // 规则仍在各自实体内部
        to.deposit(amount);
    }
}
```

**设计要点**：

1. **接口先行**：定义清晰的方法签名，调用方不需要知道实现。
2. **只做协调**：领域服务负责编排，具体规则仍应下沉到实体/值对象。
3. **无状态**：不要在领域服务里存业务状态，否则难以复用和测试。
4. **可测试**：不直接依赖数据库连接等基础设施，便于单元测试。
5. **控制依赖**：尽量减少对其他模块的依赖，避免变成新的「上帝类」。
6. **区分本地/远程**：若为远程服务，需要额外考虑网络失败、超时与重试。

### 3.4 限界上下文

**限界上下文（Bounded Context）**是 DDD 战略设计的核心：它划定的不是代码模块，而是
**一个模型适用的语义边界**——在边界内，每个术语只有一个确定含义。

> **为什么需要它**：同一个词在不同部门含义不同。以「商品」为例——在**销售上下文**里它是
> 「可售卖单元 + 价格」；在**仓储上下文**里它是「SKU + 库位 + 库存量」；在**售后上下文**里
> 它是「可退换的对象 + 保修期」。如果强行用一个 `Product` 类装下所有字段，最终会得到一堆
> 大多数场景用不上的空字段。

```text
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  销售上下文   │   │  仓储上下文   │   │  售后上下文   │
│ Product      │   │ StockItem    │   │ Returnable   │
│ (含价格/促销) │   │ (含库位/数量) │   │ (含保修期)    │
└──────────────┘   └──────────────┘   └──────────────┘
        └────────── 通过上下文映射（防腐层）转换 ──────────┘
```

**它带来的三个好处**：

1. **模型自洽**：每个上下文内部只有一个统一模型，不会互相污染。
2. **沟通精确**：团队内部说「商品」时含义唯一，减少歧义。
3. **切分依据**：限界上下文常被用作微服务拆分的参考边界（但不完全等价——一个上下文可以部署为
   多个服务，多个上下文也可能同库）。

---

## 四、分层架构：把业务逻辑放在中间

Eric Evans 提出四层划分，至今仍是 DDD 落地的骨架。

### 4.1 四层职责

| 层 | 职责 | 允许依赖 | 不该出现的东西 |
| --- | --- | --- | --- |
| 展现层（Presentation） | 接收请求、参数校验、返回视图/DTO | 应用层 | 业务规则、SQL |
| 应用层（Application） | 编排用例：取对象、调领域方法、存回、发事件 | 领域层、基础设施层 | 业务规则（必须保持"薄"） |
| 领域层（Domain） | 实体、值对象、聚合、领域服务、领域事件 | **不依赖任何外层** | 数据库、HTTP、框架注解 |
| 基础设施层（Infrastructure） | 持久化实现、消息、缓存、外部接口 | 被上层依赖（依赖倒置） | 业务判断 |

> **"应用层要薄"是重点**：它只做流程编排，写出来应该像一份步骤清单——校验、取数据、调用、
> 保存、发布事件。一旦应用层开始出现「如果金额大于 5000 则打 8 折」这类判断，规则就该下沉到
> 领域层了。

### 4.2 依赖规则

依赖方向永远**由外向内**：展现层 → 应用层 → 领域层。领域层处于中心，**不依赖任何外层**，
它通过接口（依赖倒置）让基础设施层来实现持久化。

```java
// 领域层只定义接口，不知道 MySQL 的存在
public interface OrderRepository {
    Optional<Order> findById(OrderId id);
    void save(Order order);
}

// 基础设施层提供实现
public class JpaOrderRepository implements OrderRepository { /* ... */ }
```

### 4.3 常见误解

- **「四层」不等于「四个 Maven 模块」**：可以是四个包，也可以拆成模块，取决于团队规模。
- **应用层不是 Controller**：Controller 属于展现层，应用层是跨请求可复用的用例编排。
- **领域层不排斥注解**：少量框架注解（如 `@Transactional` 放在应用层、`@Embeddable` 放在值对象）
  在实践中很常见，不必教条化。

---

## 五、持久化：仓库与工厂

领域对象不应该知道「自己存在哪张表里」。DDD 用两个构件隔离数据库：

- **仓库（Repository）**：负责领域对象的**存取**，对外表现为一个集合（`add`、`findById`、`remove`）。
- **工厂（Factory）**：负责**从持久化数据重建复杂对象**，把「数据库的一行行记录」拼成完整的聚合。

> **打个比方**：仓库是**仓库管理员**——你只管说「我要 3 号订单」，他去货架（数据库）取货给你，
> 你不需要知道货架怎么编号。工厂是**装配工**——把一个订单头 + 5 条订单明细拼成一个完整的订单对象。

**落地要点**：

1. **接口在领域层，实现在基础设施层**（依赖倒置），便于替换和测试。
2. **只暴露必要方法**：不要给仓库塞 `queryBySql` 之类的方法，否则等于把 SQL 泄漏到领域层。
3. **返回聚合整体**：`findById` 应返回装配完整的聚合，而不是先返回订单头再由调用方查明细。
4. **复杂重建用工厂**：当聚合需要多表组装、或需要根据历史数据推导状态时，用工厂封装这段逻辑。
5. **事务放在应用层**：一个用例一个事务，领域层不感知事务边界。
6. **异常转换**：把数据库异常（如 `SQLException`）在基础设施层转换为领域异常，避免技术细节上浮。

---

## 六、CQRS：读写分开建模

### 6.1 是什么

CQRS（Command Query Responsibility Segregation，命令查询职责分离）的核心主张是：
**更新数据用的模型，和读取数据用的模型，可以不是同一个模型。**

- **命令（Command）**：改变状态的操作（下单、退款、扣库存），通常不返回业务数据。
- **查询（Query）**：不改变状态的操作（列表、详情、统计），只读。

### 6.2 与 CQS 的关系

CQRS 源自 Bertrand Meyer 提出的 **CQS（命令查询分离）**原则——一个方法要么改变状态、要么返回
结果，不要两者都做。CQRS 把这条原则从「方法级」提升到了「模型级 / 架构级」。这个模式由
Greg Young 提出并在社区推广。

### 6.3 实现形态（比想象中灵活）

CQRS 有多种落地程度，**不是非得上微服务**：

| 形态 | 说明 | 复杂度 |
| --- | --- | --- |
| 同库同进程，不同对象模型 | 写模型是充血聚合，读模型是扁平 DTO，共用一张表/一个库 | 低 |
| 同库，读写不同接口 | 读写走不同的 Repository / Mapper，库表相同 | 低 |
| 读写分离库 | 写库主、读库从，靠主从复制同步 | 中 |
| 独立读库 + 事件同步 | 写侧发领域事件，读侧异步投影（Projection） | 高 |

### 6.4 什么时候用：先听警告

> Martin Fowler 对这个模式的评价相当谨慎：CQRS 对多数系统而言是在**引入风险较高的复杂度**，
> 只应在**系统中的特定部分**（某个限界上下文）使用，而不应作为整个系统的架构；社区里失败的
> 案例比成功的多。

**适合的信号**：

- 读写负载差异极大（读 1000 : 写 1），需要独立扩容；
- 查询需要多种维度聚合，用领域模型查会非常别扭；
- 业务规则集中在写侧，读侧纯粹是展示。

**不适合的信号**：

- 系统本质就是 CRUD，读写模型几乎一致；
- 团队规模小、没有成熟的异步与最终一致处理经验；
- 无法接受「写完立刻查可能查不到」（最终一致带来的体验问题）。

### 6.5 必须承担的代价

1. **一致性**：读写分离后不再强一致，需要处理延迟与更新失败补偿。
2. **运维复杂度**：多一套模型、可能多一套库、多一条同步链路。
3. **查询膨胀**：读模型容易碎片化，需要按业务场景归类，必要时独立为查询服务。

---

## 七、在微服务中落地 DDD

DDD 与微服务的对应关系是：**限界上下文 ≈ 服务边界**，但这是参考而非公式。

| 步骤 | 做法 | 注意点 |
| --- | --- | --- |
| 1. 划分上下文 | 按业务能力与语言边界划出限界上下文 | 不要按技术分层（用户服务/订单服务）粗暴切分 |
| 2. 上下文映射 | 明确上下文之间的关系：共享内核、防腐层、开放主机服务等 | 跨上下文必须有显式转换层，不能直接共享实体类 |
| 3. 边界内建模型 | 每个服务拥有独立的领域模型与统一语言 | 同一个词在不同服务里含义可以不同 |
| 4. 定义交互协议 | REST/HTTP、gRPC、消息（AMQP/Kafka） | 同步调用用于查询，异步事件用于状态传播 |
| 5. 数据自治 | 每个服务独占自己的库，禁止跨库 JOIN | 需要的数据通过事件或查询接口获得 |
| 6. 组织对齐 | 团队结构与服务边界对齐（康威定律） | 一个团队负责一个或多个完整上下文 |
| 7. 自动化运维 | 每个服务独立构建、部署、监控 | 服务多了以后，没有自动化和可观测性会被运维拖垮 |
| 8. 持续演进 | 模型随业务理解加深不断重构 | 一次性设计出完美边界几乎不可能 |

**两个最容易踩的坑**：

1. **分布式单体**：服务拆开了，但每次改需求要同时改 5 个服务并一起发布——说明边界划错了。
2. **共享数据库**：多个服务直连同一个库，等于没有边界，DDD 的所有隔离价值归零。

---

## 八、速查表

| 概念 | 一句话记忆 |
| --- | --- |
| 领域模型 | 业务概念在代码里的抽象 |
| 贫血模型 | 对象只有数据，逻辑在 Service（简单但规则易漏） |
| 充血模型 | 对象自带行为，规则收口（复杂业务首选） |
| 实体 | 有唯一标识，标识在则同一个 |
| 值对象 | 无标识、不可变、按值相等（如金额） |
| 聚合 | 必须保持整体一致的一组对象 |
| 聚合根 | 聚合对外唯一入口，负责内部一致性 |
| 领域服务 | 跨聚合、不属于单个对象的业务协调 |
| 限界上下文 | 一个模型适用的语义边界（同词不同义的分界） |
| 仓库 | 领域对象的存取接口，屏蔽数据库 |
| 工厂 | 从持久化数据重建复杂聚合 |
| CQRS | 读写用不同模型，慎用 |

---

## 参考资料

- Eric Evans，《Domain-Driven Design: Tackling Complexity in the Heart of Software》，2003
- Martin Fowler，[AnemicDomainModel](https://martinfowler.com/bliki/AnemicDomainModel.html)，2003
- Martin Fowler，[CQRS](https://martinfowler.com/bliki/CQRS.html)，2011
- Martin Fowler，[BoundedContext](https://martinfowler.com/bliki/BoundedContext.html)，2014
