# Spring知识汇总

## 一、Spring 面试题集合

### @Component Bean 的 Name 默认是什么？

很多同学觉得 Bean 的名字就是类名首字母小写，其实并不全是这样。

在解析 @Component 注册为 BeanDefinition 时会调用 `AnnotationBeanNameGenerator.buildDefaultBeanName`。

![BeanName 生成](images/1699961891863-da50e961-d644-40c7-ae48-7d852742d4ce.png)

### 单例 Bean 与单例模式

**单例模式**：主要作用是保证在 Java 应用程序中，一个 Class 有且仅有一个实例。好处是可以避免不必要的重复操作，以及防止踩踏事件。很多操作（如建立目录、数据库连接）都需要这样的单线程操作，一些资源管理器常被设计成单例模式，例如数据库连接、外部资源（一台电脑可对应多个端口，但系统会集中管理这些端口）、内部资源（用一个对象管理存放系统配置的一个或多个属性文件）。

**单例 Bean**：在 Spring 框架中，指在整个应用程序中只存在一个实例的 Bean 对象，作用是共享和复用对象实例，以提高性能、减少资源消耗。其创建和管理由 Spring 容器负责，容器启动时创建实例，并在整个应用生命周期中共享。

**区别：**

1. **运行环境**：Java 单例设计模式的环境是 JVM，而 Bean 单例的环境是 Bean 容器。一个 Spring 程序可以有很多个 Bean，但一个 Java 程序通常有且仅有一个自己的 JVM。所以虽然 Spring 的 Bean 单例在一个容器中有且仅有一个，但如果程序有多个 Bean 容器且都有某个 Bean，那么这个 Bean 在程序中并非只有一个。若将对象生命周期完全交给 Spring 管理（不在其他地方通过 new、反射等方式创建），其实也能达到单例模式的效果。
2. **范围**：单例模式通常指在一个 JVM 中一个类只能构造出一个对象；Spring 的单例 Bean 范围更小，是 beanName —— 一个 beanName 对应同一个 Bean 对象，不同 beanName 可以对应不同的 Bean 对象（即使是同一个类）。
3. **实现方式**：单例 Bean 由 Spring 容器负责创建和管理；单例模式的实现方式有多种，常见的有饿汉式（类加载时创建）、懒汉式（第一次使用时创建）等。
4. **适用范围**：单例 Bean 适用于需要共享和复用对象实例的场景（如数据库连接池、线程池）；单例模式适用于需要确保全局唯一性、避免资源浪费的场景（如配置信息管理、日志记录器）。

**小结**：单例 Bean 是 Spring 框架中的概念，使用了单例设计模式，但实现方式和适用范围有所不同，不能简单等同于单例设计模式 —— 因为同一个 class 可以在容器中存在两个不同 name 的实例，不符合单例设计模式的原则。

```java
@Component
public class ZhouyuService {

}
```

以上定义了一个单例 Bean，beanName 为 zhouyuService，类型为 ZhouyuService。可以继续用 @Bean 进一步定义：

```java
@ComponentScan("com.zhouyu")
public class AppConfig {

    @Bean
    public ZhouyuService zhouyuService1(){
        return new ZhouyuService();
    }

    @Bean
    public ZhouyuService zhouyuService2(){
        return new ZhouyuService();
    }
}
```

以上，Spring 容器中将有三个 ZhouyuService 类型的 bean 对象，它们的名字不一样。

### @Transactional(readOnly=true) 真的是提高性能的灵丹妙药吗？

很多同学都说 @Transactional(readOnly = true) 提高了性能，那我们不得不思考：Spring 对它做了什么？真的提高了性能吗？

**它是如何工作的？Spring 对它做了什么？**

```java
/**
 * Prepare the transactional {@code Connection} right after transaction begin.
 * The default implementation executes a "SET TRANSACTION READ ONLY" statement
 * if the {@link #setEnforceReadOnly "enforceReadOnly"} flag is set to {@code true}
 * and the transaction definition indicates a read-only transaction.
 * The "SET TRANSACTION READ ONLY" is understood by Oracle, MySQL and Postgres
 * and may work with other databases as well. If you'd like to adapt this treatment,
 * override this method accordingly.
 */
protected void prepareTransactionalConnection(Connection con, TransactionDefinition definition)
        throws SQLException {

    if (isEnforceReadOnly() && definition.isReadOnly()) {
        try (Statement stmt = con.createStatement()) {
            stmt.executeUpdate("SET TRANSACTION READ ONLY");
        }
    }
}
```

实际上就是利用数据库的 `SET TRANSACTION READ ONLY` 开启只读事务。只读事务对数据库意味着：

1. 通过执行 `SET TRANSACTION READ ONLY` 将当前事务设置为只读事务，事务内部任何修改数据的操作（`INSERT`、`UPDATE`、`DELETE`）都将被禁止，只能执行读取操作（`SELECT`）。
2. 只读事务依然会运用上隔离级别（MVCC），需要一定的性能开销。

**查询到底要不要设置只读，不设置是不是一样的？**

一般情况下，执行查询时不开启事务的性能可能稍微优于开启只读事务，因为不开启事务的查询不涉及事务管理和隔离级别的开销，更为轻量级和高效。

当查询不需要事务的隔离级别和一致性保证，也不需要使用事务管理的功能时，不开启事务可能更合适，查询会立即执行并返回结果。

但如果应用需要保证数据的一致性和隔离性，希望查询与其他事务的修改行为相互独立，那么开启只读事务是必要的，虽然会有一些额外性能开销，但可避免并发操作可能引起的数据不一致问题。

综上，是否开启只读事务取决于具体的应用场景和需求：需要一致性和隔离性则开启；不需要这些保证、追求查询性能则不开启。

### Spring 自动装配 Bean 有哪些方式

1. **根据名称自动装配（byName）**：Spring 容器会根据 Bean 的名称自动将相应的依赖注入到需要的地方。XML 配置中可使用 `autowire="byName"` 启用。
2. **根据类型自动装配（byType）**：Spring 容器会根据 Bean 的类型自动注入。XML 配置中可使用 `autowire="byType"` 启用。
3. **构造函数自动装配（constructor）**：Spring 容器会根据构造函数的参数类型自动注入。XML 配置中可使用 `autowire="constructor"` 启用。
4. **自动装配注解（@Autowired）**：在字段、构造函数或方法上使用 @Autowired 注解，Spring 容器会自动将相应的依赖注入到标注位置。

```java
@Component
public class Bean4 {
    @Autowired
    private Dependency dependency;

    // 构造函数自动装配
    @Autowired
    public Bean4(Dependency dependency) {
        this.dependency = dependency;
    }

    // 方法自动装配
    @Autowired
    public void setDependency(Dependency dependency) {
        this.dependency = dependency;
    }

    // Bean4的其他属性和方法
}
```

需要注意的是，自动装配需要满足一定条件，如 Bean 的定义必须在 Spring 容器中，且只能有一个匹配的依赖项。如果存在多个匹配的依赖项，可以使用 @Qualifier 注解或 @Primary 注解来指定。

### @Autowired 与 @Resource 区别

两者都是进行自动注入的，主要从以下四个维度区分：

1. 来源不同；
2. 依赖查找的顺序不同；
3. 支持的参数不同；
4. 依赖注入的用法支持不同。

**来源不同**

@Autowired 是 Spring2.5 定义的注解；@Resource 是 Java 定义的注解，来自 JSR-250（Java 250 规范提案）。

**依赖查找的顺序不同**

依赖注入通过先在 Spring IoC 容器中查找对象、再将对象注入到当前类中。查找分为按名称（byName）和按类型（byType），@Autowired 和 @Resource 都既使用名称查找又使用类型查找，但查找顺序截然相反。

*@Autowired*：首先按类型匹配，如果有多个匹配的 bean，再根据名称匹配。

如果被注入的属性或构造函数参数的类型在容器中有且只有一个对应的 bean，就直接注入该 bean：

```java
@Autowired
private UserService userService;
```

如果容器中存在多个类型为 UserService 的 bean，就需要通过名称匹配。此时可在 @Autowired 上使用 @Qualifier 指定要注入的 bean 名称，如果不使用 @Qualifier 就会使用属性名：

```java
@Autowired
@Qualifier("userService2")
private UserService userService;
```

*@Resource*：可以通过名称或类型注入 bean，取决于 name 和 type 两个属性。

如果指定了 name 属性，Spring 根据该名称查找对应的 bean：

```java
@Resource(name = "myBean")
private MyBean myBean;
```

如果指定了 type 属性，Spring 根据该类型查找对应的 bean：

```java
@Resource(type = MyBean.class)
private MyBean myBean;
```

如果既没有指定 name 也没有指定 type，默认按照名称查找：

```java
@Resource
private MyBean myBean;
```

上述代码默认按名称 `myBean` 查找对应的 bean 并注入。

**支持的参数不同**

@Autowired 只支持设置一个 required 参数，而 @Resource 支持 7 个参数。

![@Resource 参数1](images/1713513602763-e139ca2f-840a-48fe-9b72-bcb23635e992.png)

![@Resource 参数2](images/1713513555699-e4f935cf-aa03-4a14-a5c5-4d8cd9e0222d.png)

**依赖注入的用法支持不同**

常见依赖注入有三种实现：属性注入、构造方法注入、Setter 注入。@Autowired 支持全部三种，而 @Resource 只支持属性注入和 Setter 注入。

```java
@RestController
public class UserController {
    // 属性注入
    @Autowired
    private UserService userService;

    @RequestMapping("/add")
    public UserInfo add(String username, String password) {
        return userService.add(username, password);
    }
}

@RestController
public class UserController {
    // 构造方法注入
    private UserService userService;

    @Autowired
    public UserController(UserService userService) {
        this.userService = userService;
    }

    @RequestMapping("/add")
    public UserInfo add(String username, String password) {
        return userService.add(username, password);
    }
}

@RestController
public class UserController {
    // Setter 注入
    private UserService userService;

    @Autowired
    public void setUserService(UserService userService) {
        this.userService = userService;
    }

    @RequestMapping("/add")
    public UserInfo add(String username, String password) {
        return userService.add(username, password);
    }
}
```

![依赖注入用法](images/1661341346342-317ea714-5825-4dc9-96a0-f0a118158380.png)

**总结**

1. 来源不同：@Autowired 来自 Spring 框架，@Resource 来自 JSR-250；
2. 依赖查找的顺序不同：@Autowired 先按类型再按名称，@Resource 先按名称再按类型；
3. 支持的参数不同：@Autowired 只支持 1 个参数，@Resource 支持 7 个参数；
4. 依赖注入的用法支持不同：@Autowired 支持构造方法注入、属性注入和 Setter 注入，@Resource 只支持属性注入和 Setter 注入。

### Bean 的实例化和 Bean 的初始化有什么区别？

Spring 创建一个 Bean 对象时，会先通过反射执行类的构造方法得到一个 Java 对象，这个过程就是 **Bean 的实例化**。

得到 Java 对象后，会进行依赖注入，之后进入初始化。**Bean 的初始化**就是调用前面创建出来的 Java 对象中特定的方法：比如 Java 对象实现了 InitializingBean 接口，初始化时会执行 `afterPropertiesSet()`，Spring 只执行这个方法，并不关心方法做了什么，我们可以在此方法中对某个属性进行验证或赋值；或者执行 init-method 指定的方法，比如：

```java
@Component
public class ZhouyuService {

    public void a(){
        System.out.println("zhouyu init");
    }

}
```

```java
@ComponentScan("com.zhouyu")
public class AppConfig {

    @Bean(initMethod = "a")
    public ZhouyuService zhouyuService1(){
        return new ZhouyuService();
    }
}
```

### Spring AOP 是如何实现的？它和 AspectJ 有什么区别？

Spring AOP 利用动态代理机制：如果 Bean 实现了接口，就采用 JDK 动态代理生成该接口的代理对象；如果 Bean 没有实现接口，就采用 CGLIB 生成当前类的代理对象。代理对象的作用是代理原本的 Bean 对象，执行某个方法时会在该方法基础上增加切面逻辑，从而用 AOP 实现登录校验、权限控制、日志记录等统一功能。

Spring AOP 和 AspectJ 之间并没有特别强的关系。AOP 表示面向切面编程，是一种思想，各个组织和个人都可以通过技术实现。AspectJ 就是其中之一，它在编译期对类进行增强，因此要用 AspectJ 得用其开发的编译器编译项目。而 Spring AOP 采用动态代理实现 AOP，只是觉得 AspectJ 中设计的 @Before、@After、@Around 等注解比较好，同时也避免给程序员造成困扰，所以对这些注解进行了支持 —— 虽然注解相同，但底层实现完全不一样。

### Spring 中的事务是如何实现的？

1. Spring 事务底层基于数据库事务和 AOP 机制。
2. 对于使用了 @Transactional 注解的 Bean，Spring 会创建一个代理对象作为 Bean。
3. 调用代理对象的方法时，会先判断该方法上是否加了 @Transactional 注解。
4. 如果加了，则利用事务管理器创建一个数据库连接。
5. 并修改数据库连接的 autocommit 属性为 false，禁止此连接的自动提交，这是实现 Spring 事务非常重要的一步。
6. 然后执行当前方法，方法中会执行 SQL。
7. 执行完当前方法后，如果没有出现异常就直接提交事务。
8. 如果出现了异常，并且这个异常是需要回滚的就会回滚事务，否则仍然提交事务。
9. Spring 事务的隔离级别对应的就是数据库的隔离级别。
10. Spring 事务的传播机制是 Spring 事务自己实现的，也是 Spring 事务中最复杂的。
11. Spring 事务的传播机制基于数据库连接来做：一个数据库连接一个事务，如果传播机制配置为需要新开一个事务，那么实际上就是先建立一个数据库连接，在此新数据库连接上执行 SQL。

![Spring 事务实现](images/1622966825505-41961ccc-19e0-4f70-8182-e6e3337eb3af.png)

### 你是如何理解 Spring 事务的传播机制的？底层是如何实现的？

一个线程在运行过程中可能会连续调用好几个方法，调用某一个方法时可能开启了一个 Spring 事务，那么调用接下来的方法时到底是共用同一个事务，还是新开一个事务？这就是传播机制，程序员可根据不同业务场景配置：

1. REQUIRED（Spring 默认的传播类型）：如果当前没有事务，则自己新建一个事务；如果当前存在事务，则加入这个事务。
2. SUPPORTS：当前存在事务，则加入当前事务；如果当前没有事务，就以非事务方法执行。
3. MANDATORY：当前存在事务，则加入当前事务；如果当前事务不存在，则抛出异常。
4. REQUIRES_NEW：创建一个新事务，如果存在当前事务，则挂起该事务。
5. NOT_SUPPORTED：以非事务方式执行，如果当前存在事务，则挂起当前事务。
6. NEVER：不使用事务，如果当前事务存在，则抛出异常。
7. NESTED：如果当前事务存在，则在嵌套事务中执行，否则和 REQUIRED 一样（开启一个事务）。

在 Spring 中，一个 Spring 事务对应一个数据库连接，新开一个 Spring 事务其实就是新开一个数据库连接。比如执行某个方法时需要开启一个 Spring 事务，就会创建一个数据库连接，然后开始执行方法；如果方法中调用了其他方法，就会看这个其他方法怎么配置：

1. 比如是 REQUIRES_NEW，那么就会新开一个数据库连接，其中方法中的 SQL 就在这个新开的数据库连接中执行。
2. 比如是 REQUIRED，那么就不会新开，而是基于之前的数据库连接来执行方法中的 SQL。

### 哪些情况下会导致 Spring 事务失效，对应的原因是什么？

1. **方法内的自调用**：Spring 事务基于 AOP，只要使用代理对象调用某个方法时 Spring 事务才能生效，而在一个方法中通过 `this.xxx()` 调用方法时，this 并不是代理对象，所以会导致事务失效。
   1. 解决办法1：把调用方法拆分到另外一个 Bean 中。
   2. 解决办法2：自己注入自己。
   3. 解决办法3：`AopContext.currentProxy()` + `@EnableAspectJAutoProxy(exposeProxy = true)`。
2. **方法是 private 的**：Spring 事务基于 CGLIB 进行 AOP，而 CGLIB 基于父子类实现，子类是代理类，父类是被代理类。如果父类中某个方法是 private 的，子类就无法重写它，也就无法额外增加 Spring 事务的逻辑。
3. **方法是 final 的**：原因和 private 一样，子类不能重写父类中的 final 方法。
4. **单独的线程调用方法**：MyBatis 或 JdbcTemplate 执行 SQL 时会从 ThreadLocal 中获取数据库连接对象。如果开启事务的线程和执行 SQL 的线程是同一个，就能拿到数据库连接对象；如果不是同一个线程，就拿不到，此时 MyBatis 或 JdbcTemplate 会自己新建一个数据库连接来执行 SQL，此连接的 autocommit 为 true，执行完 SQL 就会提交，后续再抛异常也无法回滚之前已提交的 SQL。
5. **没加 @Configuration 注解**：用 SpringBoot 基本没有这个问题，但如果用的 Spring 可能会有。原因也是 MyBatis 或 JdbcTemplate 从 ThreadLocal 中获取数据库连接，而 ThreadLocal 中存储的是一个 Map，key 为 DataSource 对象、value 为连接对象。如果没在 AppConfig 上添加 @Configuration 注解，会导致 Map 中存的 DataSource 对象和 MyBatis、JdbcTemplate 中的 DataSource 对象不相等，从而拿不到数据库连接，自己去创建连接了。
6. **异常被吃掉**：如果 Spring 事务没有捕获到异常，也就不会回滚，默认情况下 Spring 会捕获 RuntimeException 和 Error。
7. **类没有被 Spring 管理**。
8. **数据库不支持事务**。

### Spring 中的 Bean 创建的生命周期有哪些步骤

1. 推断构造方法。
2. 实例化。
3. 填充属性，也就是依赖注入。
4. 处理 Aware 回调。
5. 初始化前，处理 @PostConstruct 注解。
6. 初始化，处理 InitializingBean 接口。
7. 初始化后，进行 AOP。

真正的步骤更加细致，可以看下面的流程图：

![Bean 生命周期](images/1625729452241-4bc1dbb0-a827-49f1-83b8-70e61fd29a65.png)

### Spring 中 Bean 是线程安全的吗

Spring 本身并没有针对 Bean 做线程安全的处理，所以：

1. 如果 Bean 是无状态的，那么 Bean 是线程安全的。
2. 如果 Bean 是有状态的，那么 Bean 不是线程安全的。

另外，Bean 是不是线程安全，跟 Bean 的作用域没有关系。Bean 的作用域只是表示 Bean 的生命周期范围，对于任何生命周期的 Bean 都是一个对象，这个对象是不是线程安全的，还是得看这个 Bean 对象本身。

### ApplicationContext 和 BeanFactory 有什么区别

**基本概念**

- **BeanFactory**：Spring 框架中最基础的接口，提供最简单的容器功能，主要负责实例化对象和获取对象。它是 Spring 容器家族的根接口，可以理解为 IoC 容器的基础规范。
- **ApplicationContext**（应用上下文）：继承了 BeanFactory 接口，是 Spring 提供的更高级的容器实现，在 BeanFactory 基础上增加了许多企业级功能，拥有 BeanFactory 的所有功能。

**主要区别**

*1）装载 Bean 的区别*

- **BeanFactory**：采用延迟加载策略，容器启动较快。只有当客户端请求获取 Bean 时才进行实例化，第一次调用 `getBean()` 时才初始化相应的 Bean。
- **ApplicationContext**：容器启动时就完成所有单例 Bean 的实例化（除非配置了 `lazy-init="true"`）。这样系统运行期不需要等待对象实例化，提高响应速度，并且能在启动阶段就发现系统中的配置问题。

*2）功能差异*

![功能差异](images/1744198548153-6b552ad8-1c14-4869-b5eb-41d8b8f043ec.png)

ApplicationContext 比 BeanFactory 提供了更多的企业级功能：

- **国际化支持（MessageSource）**：实现 MessageSource 接口，支持信息国际化和参数化。

  ```java
  // 获取不同语言的消息
  String message = context.getMessage("message.welcome", new Object[]{"John"}, Locale.US);
  ```

- **资源访问（ResourceLoader）**：实现 ResourceLoader 接口，统一加载各种资源文件。

  ```java
  // 从类路径加载资源
  Resource resource = context.getResource("classpath:config.xml");

  // 从文件系统加载资源
  Resource fileResource = context.getResource("file:///path/to/file.txt");
  ```

- **事件机制（ApplicationEventPublisher）**：实现事件发布功能，允许 Bean 通过事件交互。

  ```java
  // 自定义事件
  public class UserCreatedEvent extends ApplicationEvent {
      private String username;

      public UserCreatedEvent(Object source, String username) {
          super(source);
          this.username = username;
      }
      // getter...
  }

  // 发布事件
  context.publishEvent(new UserCreatedEvent(this, "张三"));

  // 事件监听器
  @Component
  public class EmailService implements ApplicationListener {
      @Override
      public void onApplicationEvent(UserCreatedEvent event) {
          System.out.println("发送邮件给: " + event.getUsername());
      }
  }
  ```

- **标准 Context 事件**：内置支持多种容器事件：
  - ContextRefreshedEvent：容器刷新完成时触发。
  - ContextStartedEvent：容器启动时触发。
  - ContextStoppedEvent：容器停止时触发。
  - ContextClosedEvent：容器关闭时触发。

- **获取其他组件引用**：可以获取 Bean 工厂本身。

  ```java
  // 获取到bean工厂
  ConfigurableListableBeanFactory factory = ((ConfigurableApplicationContext)context).getBeanFactory();
  ```

*3）使用选择*

- **何时使用 BeanFactory**：
  - 在资源受限的环境中（如移动设备）：延迟加载策略可减少启动时的资源消耗。
  - 当应用程序的依赖关系较少且简单时。
  - 对启动性能有极高要求，且可以接受首次请求延迟的场景。
- **何时使用 ApplicationContext（推荐）**：
  - 开发企业级应用时（几乎所有场景）。
  - 需要处理国际化消息时。
  - 需要发布和监听事件时。
  - 在 Web 应用中（使用 WebApplicationContext，针对 Web 环境做了优化）。
  - 需要使用 AOP 特性时。

### Spring 容器启动流程是怎样的

1. 创建 Spring 容器，也就是启动 Spring 时，首先进行扫描，扫描得到所有的 BeanDefinition 对象，并存在一个 Map 中。
2. 然后筛选出非懒加载的单例 BeanDefinition 进行创建 Bean；对于多例 Bean，不需要在启动过程中创建，会在每次获取 Bean 时利用 BeanDefinition 去创建。
3. 利用 BeanDefinition 创建 Bean 就是 Bean 的创建生命周期，包括合并 BeanDefinition、推断构造方法、实例化、属性填充、初始化前、初始化、初始化后等步骤，其中 AOP 发生在初始化后这一步。
4. 单例 Bean 创建完之后，Spring 会发布一个容器启动事件。
5. Spring 启动结束。
6. 源码中会更复杂，比如会提供一些模板方法让子类实现，还涉及 BeanFactoryPostProcessor 和 BeanPostProcessor 的注册：Spring 的扫描就是通过 BeanFactoryPostProcessor 实现的，依赖注入就是通过 BeanPostProcessor 实现的。
7. 启动过程中还会处理 @Import 等注解。

![Spring 容器启动流程](images/1622965863563-ce71fb30-d01f-4829-93a8-a94d784ccc2c.png)

### @SpringBootApplication 注解有什么用？为什么一定要写它？

@SpringBootApplication 是一个复合注解：

```java
@SpringBootConfiguration
@EnableAutoConfiguration
@ComponentScan
public @interface SpringBootApplication {

}
```

它整合了以上三个注解，在一个类上只要加了 @SpringBootApplication，就相当于同时加了这三个注解。当 Spring 容器启动时解析到一个类上有 @SpringBootApplication，就相当于这个类上有：

1. @ComponentScan：Spring 容器会进行扫描，扫描路径为当前解析的这个类所在的包路径。
2. @EnableAutoConfiguration：负责自动配置类的导入，也就是将项目中的自动配置类导入到 Spring 容器中并解析。
3. @SpringBootConfiguration：相当于 @Configuration，表示当前类是一个配置类。

所以使用 SpringBoot 时一般会加上 @SpringBootApplication，因为只要加上了它，SpringBoot 就会进行扫描、导入自动配置类并解析。

### SpringBoot 中的 spring.factories 文件有什么作用？

spring.factories 是 SpringBoot SPI 机制实现的核心，SPI 机制表示扩展机制，所以该文件的作用就是用来对 SpringBoot 进行扩展。比如可以通过在该文件中添加 ApplicationListener、ApplicationContextInitializer、配置类等，只需在文件中添加即可，而不用额外写代码。

SpringBoot 启动过程中会找出项目中所有的 spring.factories 文件（包括 jar 中的），从而向 Spring 容器中添加各个文件中指定的 ApplicationListener、ApplicationContextInitializer、配置类等组件，使得对 SpringBoot 做扩展非常容易 —— 只要引入一个含有 spring.factories 文件的 jar，就可以把 ApplicationListener 等添加到 Spring 容器中。

### 你是如何理解 SpringBoot 中的自动配置的？

在 Spring 中，我们通常需要配置很多 Bean：

- 用 MyBatis，要配置 SqlSessionFactory 的 Bean 对象。
- 用 AOP，需要配置 @EnableAspectJAutoProxy 注解。
- 用 Spring 事务，需要配置 DataSourceTransactionManager 的 Bean 对象。
- 用 RabbitMQ，要配置 RabbitTemplate 的 Bean 对象。
- 等等。

而用 SpringBoot 时基本不用再配这些，因为 SpringBoot 帮我们配置好了。它内置了很多配置类，也叫自动配置类，比如 RabbitAutoConfiguration、AopAutoConfiguration、ElasticsearchDataAutoConfiguration、DataSourceTransactionManagerAutoConfiguration 等。我们在依赖了 spring-boot-starter-web 后，会间接依赖到 spring-boot-autoconfigure 这个 jar，其中包含了很多自动配置类：

![自动配置类](images/1673876857703-8dd2abe1-6432-4585-b439-9e0233c101ac.png)

这其实就是 SpringBoot 的自动配置，帮程序员提前配置了很多东西（Bean 或注解）。

### Spring Boot 启动过程中做了哪些事情？

1. 首先判断当前的应用类型，比如是不是 web 应用，如果是，那是 servlet 应用还是 webflux 应用，不同类型后续会创建不同的 Spring 容器。
2. 根据应用类型**创建 Spring 容器**。
3. 解析启动类，从而进行扫描、导入自动配置类并解析。
4. 启动 Tomcat 或者 Jetty、Undertow。
5. 调用 ApplicationRunner 或 CommandLineRunner。

以上是一些核心步骤，整个启动过程还包含 SpringApplicationRunListeners 的调用、banner 的打印、ApplicationContextInitializer 的执行等，具体可参照源码。

### SpringMVC 处理请求的流程是什么？

1. 在启动 Tomcat 过程中，会创建 DispatcherServlet 对象，并执行它的初始化逻辑。
2. DispatcherServlet 初始化过程中会创建 Spring 容器（根据用户的 Spring 配置）。
3. 初始化过程中还会初始化 HandlerMapping、HandlerAdapter 等。
4. SpringMVC 默认提供了好几个 HandlerMapping，其中有一个为 RequestMappingHandlerMapping。
5. RequestMappingHandlerMapping 的作用是去寻找 Spring 容器中有哪些加了 @RequestMapping 的方法。
6. 找到这些方法后，解析该注解上的信息（包含指定的 path），然后把 path 作为 key、Method 作为 value 存到一个 map 中。
7. DispatcherServlet 接收到请求后，RequestMappingHandlerMapping 负责根据请求路径从 map 中找到对应的 Method。
8. 然后准备执行 Method，只是在执行之前会解析该方法的各个参数。
9. 比如参数前面加了 @RequestParam 注解，SpringMVC 就会解析该注解，并从请求中取出对应 request param 中的数据传给该参数。
10. 解析完各个参数并从请求中拿到对应的值后，就会执行方法。
11. 执行完方法得到返回值后，SpringMVC 会进一步解析。
12. 比如方法上如果加了 @ResponseBody，就直接把返回值返回给浏览器。
13. 如果方法上没有加 @ResponseBody，就要根据返回值找到对应的页面并进行服务端渲染，再把渲染结果返回给浏览器。

### SpringMVC 中的重定向和转发分别是如何实现的？

1. 可以使用 `forward:` 对当前请求进行转发。
2. 可以用 `redirect:` 对当前请求进行重定向。
3. SpringMVC 接收到一个请求后，会先处理请求。如果后续方法要进行转发，就会利用 RequestDispatcher 将当前请求转发到指定地址。这种情况下一直是同一个请求，只不过两次请求的路径不一样，并且转发对浏览器而言是透明的。
4. 如果处理完发现要进行重定向，SpringMVC 会向浏览器响应 303，同时告诉浏览器要重定向的路径，由浏览器自己来访问，所以重定向需要浏览器参与，是不同的两个请求。

### BeanDefinitionReader 与 MetadataReader 的区别

**BeanDefinitionReader**

Spring 框架中用于读取 bean 定义信息的接口。它负责从各种来源（如 XML 文件、注解、Java 配置类等）读取并解析 bean 的定义，然后转换为 BeanDefinition 对象，最终注册到 BeanDefinitionRegistry 中。

主要实现包括：

- XmlBeanDefinitionReader：读取 XML 配置文件。
- AnnotatedBeanDefinitionReader：读取带有注解的类。
- ClassPathBeanDefinitionScanner：扫描指定路径下的类。

**MetadataReader**

Spring 的核心组件，主要用于读取和访问类的元数据信息，而不仅限于 bean 定义。它提供对类、方法、字段等元数据的访问能力，包括类的注解信息、类的结构信息等。

MetadataReader 通常与 ASM 库结合使用，可以不需要加载整个类就能获取类的元数据信息，这对提高性能非常重要。

**主要区别**

1. **功能范围**：BeanDefinitionReader 专注于读取和解析 bean 定义；MetadataReader 范围更广，用于读取类的各种元数据信息。
2. **使用场景**：BeanDefinitionReader 主要用于 Spring IoC 容器的初始化阶段；MetadataReader 可用于各种需要获取类元数据的场景，如注解扫描、条件化配置等。
3. **抽象层次**：BeanDefinitionReader 工作在较高的抽象层次，直接与 Spring bean 相关；MetadataReader 工作在较低的抽象层次，关注类的元数据信息。
4. **输出结果**：BeanDefinitionReader 的输出是 BeanDefinition 对象；MetadataReader 提供的是类的元数据信息，如 ClassMetadata 和 AnnotationMetadata。

两者在 Spring 框架中扮演不同但相互补充的角色，共同支持 Spring 的依赖注入和控制反转功能。
