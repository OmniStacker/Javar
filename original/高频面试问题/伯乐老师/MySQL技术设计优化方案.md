# MySQL 技术设计优化方案

## <font style="color:rgba(0, 0, 0, 0.96);">目录</font>

1. <font style="color:rgb(9, 105, 218);">索引设计优化方案</font>
2. <font style="color:rgb(9, 105, 218);">慢查询优化方案</font>
3. <font style="color:rgb(9, 105, 218);">深分页性能优化</font>
4. <font style="color:rgb(9, 105, 218);">事务与死锁优化</font>
5. <font style="color:rgb(9, 105, 218);">主从复制高可用方案</font>
6. <font style="color:rgb(9, 105, 218);">综合优化最佳实践</font>

***

## <font style="color:rgba(0, 0, 0, 0.96);">1. 索引设计优化方案</font>

### <font style="color:rgba(0, 0, 0, 0.96);">1.1 联合索引设计规范</font>

#### <font style="color:rgba(0, 0, 0, 0.96);">问题场景</font>

```sql
-- 现有表结构
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `age` int NOT NULL,
  `city` varchar(50) NOT NULL,
  `status` tinyint NOT NULL DEFAULT '1',
  `create_time` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

-- 常见查询场景
SELECT * FROM user WHERE age = 20 AND city = '北京';
SELECT * FROM user WHERE age > 18 AND city = '北京' AND status = 1;
SELECT * FROM user WHERE city = '北京';
```

#### <font style="color:rgba(0, 0, 0, 0.96);">优化方案</font>

**<font style="color:rgba(0, 0, 0, 0.96);">方案一：传统联合索引（不推荐）</font>**

```sql
-- ❌ 问题：范围查询导致后续索引失效
ALTER TABLE user ADD INDEX idx_age_city_status(age, city, status);

-- 执行计划分析
EXPLAIN SELECT * FROM user WHERE age > 18 AND city = '北京' AND status = 1;
-- 结果：只用到了age索引，city和status失效
```

**<font style="color:rgba(0, 0, 0, 0.96);">方案二：优化后的联合索引（推荐）</font>**

```plain
-- ✅ 优化：等值查询字段放前面，范围查询放后面
ALTER TABLE user ADD INDEX idx_city_status_age(city, status, age);

-- 调整后的查询
SELECT * FROM user WHERE city = '北京' AND status = 1 AND age > 18;

-- 执行计划分析
EXPLAIN SELECT * FROM user WHERE city = '北京' AND status = 1 AND age > 18;
-- 结果：三个字段都用上了索引
```

**<font style="color:rgba(0, 0, 0, 0.96);">联合索引设计原则</font>**

| **<font style="color:rgba(0, 0, 0, 0.96);">原则</font>** | **<font style="color:rgba(0, 0, 0, 0.96);">说明</font>** | **<font style="color:rgba(0, 0, 0, 0.96);">示例</font>** |
| --- | --- | --- |
| <font style="color:rgba(0, 0, 0, 0.96);">1. 等值查询优先</font> | <font style="color:rgba(0, 0, 0, 0.96);">WHERE a=1 AND b>10 → 索引(a,b)</font> | <code><font style="color:rgba(0, 0, 0, 0.96);background-color:rgba(175, 184, 193, 0.2);">idx_city_age</font></code><br/><font style="color:rgba(0, 0, 0, 0.96);"> </font><font style="color:rgba(0, 0, 0, 0.96);">而非</font><font style="color:rgba(0, 0, 0, 0.96);"> </font><code><font style="color:rgba(0, 0, 0, 0.96);background-color:rgba(175, 184, 193, 0.2);">idx_age_city</font></code> |
| <font style="color:rgba(0, 0, 0, 0.96);">2. 选择性高的优先</font> | <font style="color:rgba(0, 0, 0, 0.96);">区分度高的字段放前面</font> | <font style="color:rgba(0, 0, 0, 0.96);">身份证号 > 性别</font> |
| <font style="color:rgba(0, 0, 0, 0.96);">3. 查询频率高的优先</font> | <font style="color:rgba(0, 0, 0, 0.96);">常用查询条件放前面</font> | <font style="color:rgba(0, 0, 0, 0.96);">根据业务统计决定顺序</font> |
| <font style="color:rgba(0, 0, 0, 0.96);">4. 尽量覆盖索引</font> | <font style="color:rgba(0, 0, 0, 0.96);">SELECT字段包含在索引中</font> | <code><font style="color:rgba(0, 0, 0, 0.96);background-color:rgba(175, 184, 193, 0.2);">idx_city_age</font></code><br/><font style="color:rgba(0, 0, 0, 0.96);"> </font><font style="color:rgba(0, 0, 0, 0.96);">能覆盖 SELECT city, age</font> |

#### <font style="color:rgba(0, 0, 0, 0.96);">实战代码示例</font>

```plain
// 业务代码优化：根据索引调整查询条件顺序
@Repository
public class UserRepository {
    
    /**
     * ❌ 不推荐：范围查询在前
     */
    public List<User> findUsersBadWay(int minAge, String city, int status) {
        String sql = "SELECT * FROM user WHERE age > ? AND city = ? AND status = ?";
        // age的范围查询会导致city和status索引失效
        return jdbcTemplate.query(sql, new Object[]{minAge, city, status}, userRowMapper);
    }
    
    /**
     * ✅ 推荐：等值查询在前，范围查询在后
     */
    public List<User> findUsersOptimized(String city, int status, int minAge) {
        // 确保索引是 idx_city_status_age
        String sql = "SELECT * FROM user WHERE city = ? AND status = ? AND age > ?";
        return jdbcTemplate.query(sql, new Object[]{city, status, minAge}, userRowMapper);
    }
    
    /**
     * ✅ 进阶：使用覆盖索引，避免回表
     */
    public List<UserDTO> findUsersWithCoveringIndex(String city, int status) {
        // 只查询索引中包含的字段，避免回表
        String sql = "SELECT id, city, status, age FROM user " +
                     "WHERE city = ? AND status = ? " +
                     "ORDER BY age DESC LIMIT 100";
        return jdbcTemplate.query(sql, new Object[]{city, status}, userDTORowMapper);
    }
}
```

***

## <font style="color:rgba(0, 0, 0, 0.96);">2. 慢查询优化方案</font>

### <font style="color:rgba(0, 0, 0, 0.96);">2.1 索引失效问题排查</font>

#### <font style="color:rgba(0, 0, 0, 0.96);">问题场景：函数导致索引失效</font>

```plain
-- ❌ 慢查询：在索引列上使用函数
SELECT * FROM orders 
WHERE DATE_FORMAT(create_time, '%Y-%m-%d') = '2024-01-01';

-- 执行时间：3.5秒（100万条数据）
-- 扫描行数：1,000,000行（全表扫描）
```

**<font style="color:rgba(0, 0, 0, 0.96);">优化方案</font>**

```plain
-- ✅ 优化：改写查询条件，避免函数
SELECT * FROM orders 
WHERE create_time >= '2024-01-01 00:00:00' 
  AND create_time < '2024-01-02 00:00:00';

-- 执行时间：0.05秒
-- 扫描行数：2,350行（走索引）

-- 确保有索引
ALTER TABLE orders ADD INDEX idx_create_time(create_time);
```

**<font style="color:rgba(0, 0, 0, 0.96);">Java代码实现</font>**

```plain
@Service
public class OrderService {
    
    /**
     * ❌ 不推荐：使用日期函数
     */
    public List<Order> findOrdersByDateBadWay(LocalDate date) {
        String sql = "SELECT * FROM orders WHERE DATE(create_time) = ?";
        return jdbcTemplate.query(sql, new Object[]{date}, orderRowMapper);
    }
    
    /**
     * ✅ 推荐：使用范围查询
     */
    public List<Order> findOrdersByDateOptimized(LocalDate date) {
        LocalDateTime startTime = date.atStartOfDay();
        LocalDateTime endTime = date.plusDays(1).atStartOfDay();
        
        String sql = "SELECT * FROM orders " +
                     "WHERE create_time >= ? AND create_time < ?";
        return jdbcTemplate.query(sql, 
            new Object[]{startTime, endTime}, 
            orderRowMapper);
    }
    
    /**
     * ✅ 进阶：使用MyBatis动态SQL + 覆盖索引
     */
    @Select("SELECT id, order_no, create_time, amount " +
            "FROM orders " +
            "WHERE create_time >= #{startTime} AND create_time < #{endTime}")
    List<OrderDTO> findOrdersWithCoveringIndex(
        @Param("startTime") LocalDateTime startTime,
        @Param("endTime") LocalDateTime endTime
    );
}
```

### <font style="color:rgba(0, 0, 0, 0.96);">2.2 隐式类型转换优化</font>

#### <font style="color:rgba(0, 0, 0, 0.96);">问题场景</font>

```plain
-- 表结构：phone字段是varchar类型
CREATE TABLE `user_phone` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `phone` varchar(20) NOT NULL,
  `user_id` bigint NOT NULL,
  KEY `idx_phone` (`phone`)
) ENGINE=InnoDB;

-- ❌ 慢查询：传入数字类型导致索引失效
SELECT * FROM user_phone WHERE phone = 13800138000;
-- MySQL会将索引列转换：CAST(phone AS UNSIGNED) = 13800138000
-- 结果：全表扫描
```

**<font style="color:rgba(0, 0, 0, 0.96);">优化方案</font>**

```plain
-- ✅ 优化：确保类型匹配
SELECT * FROM user_phone WHERE phone = '13800138000';
```

**<font style="color:rgba(0, 0, 0, 0.96);">Java代码防御</font>**

```plain
@Service
public class UserPhoneService {
    
    /**
     * ✅ 推荐：强制类型转换，防止隐式转换
     */
    public UserPhone findByPhone(Object phoneInput) {
        // 统一转换为字符串
        String phone = String.valueOf(phoneInput);
        
        // 参数校验
        if (!phone.matches("^1[3-9]\\d{9}$")) {
            throw new IllegalArgumentException("手机号格式错误");
        }
        
        String sql = "SELECT * FROM user_phone WHERE phone = ?";
        return jdbcTemplate.queryForObject(sql, new Object[]{phone}, userPhoneRowMapper);
    }
    
    /**
     * ✅ 批量查询优化：使用IN查询 + PreparedStatement
     */
    public List<UserPhone> findByPhones(List<String> phones) {
        if (CollectionUtils.isEmpty(phones)) {
            return Collections.emptyList();
        }
        
        // 使用IN查询，而非循环单次查询
        String inClause = String.join(",", Collections.nCopies(phones.size(), "?"));
        String sql = "SELECT * FROM user_phone WHERE phone IN (" + inClause + ")";
        
        return jdbcTemplate.query(sql, phones.toArray(), userPhoneRowMapper);
    }
}
```

### <font style="color:rgba(0, 0, 0, 0.96);">2.3 LIKE查询优化</font>

#### <font style="color:rgba(0, 0, 0, 0.96);">问题场景</font>

```plain
-- ❌ 索引失效：前缀模糊查询
SELECT * FROM product WHERE name LIKE '%手机%';

-- ❌ 索引失效：后缀模糊查询
SELECT * FROM product WHERE name LIKE '%手机';

-- ✅ 走索引：前缀匹配
SELECT * FROM product WHERE name LIKE '手机%';
```

**<font style="color:rgba(0, 0, 0, 0.96);">优化方案</font>**

**<font style="color:rgba(0, 0, 0, 0.96);">方案一：前缀匹配（简单场景）</font>**

```plain
@Service
public class ProductService {
    
    /**
     * ✅ 前缀匹配查询
     */
    public List<Product> searchByNamePrefix(String keyword) {
        String sql = "SELECT * FROM product WHERE name LIKE ?";
        return jdbcTemplate.query(sql, new Object[]{keyword + "%"}, productRowMapper);
    }
}
```

**<font style="color:rgba(0, 0, 0, 0.96);">方案二：全文索引（复杂场景）</font>**

```plain
-- 创建全文索引（MySQL 5.7+支持InnoDB全文索引）
ALTER TABLE product ADD FULLTEXT INDEX ft_idx_name(name) WITH PARSER ngram;

-- 使用全文搜索
SELECT * FROM product WHERE MATCH(name) AGAINST('手机' IN NATURAL LANGUAGE MODE);
```

```plain
@Service
public class ProductSearchService {
    
    /**
     * ✅ 使用全文索引搜索
     */
    public List<Product> fullTextSearch(String keyword) {
        String sql = "SELECT *, MATCH(name) AGAINST(? IN NATURAL LANGUAGE MODE) as score " +
                     "FROM product " +
                     "WHERE MATCH(name) AGAINST(? IN NATURAL LANGUAGE MODE) " +
                     "ORDER BY score DESC " +
                     "LIMIT 100";
        return jdbcTemplate.query(sql, new Object[]{keyword, keyword}, productRowMapper);
    }
}
```

**<font style="color:rgba(0, 0, 0, 0.96);">方案三：Elasticsearch（推荐生产环境）</font>**

```plain
@Service
public class ProductSearchServiceES {
    
    @Autowired
    private ElasticsearchRestTemplate elasticsearchTemplate;
    
    /**
     * ✅ 使用ES进行复杂搜索（推荐）
     */
    public List<Product> searchProducts(String keyword) {
        NativeSearchQuery query = new NativeSearchQueryBuilder()
            .withQuery(QueryBuilders.multiMatchQuery(keyword, "name", "description")
                .type(MultiMatchQueryBuilder.Type.BEST_FIELDS)
                .fuzziness(Fuzziness.AUTO))
            .withPageable(PageRequest.of(0, 100))
            .build();
        
        SearchHits<Product> searchHits = elasticsearchTemplate.search(query, Product.class);
        return searchHits.stream()
            .map(SearchHit::getContent)
            .collect(Collectors.toList());
    }
}
```

***

## <font style="color:rgba(0, 0, 0, 0.96);">3. 深分页性能优化</font>

### <font style="color:rgba(0, 0, 0, 0.96);">3.1 问题分析</font>

```plain
-- ❌ 深分页慢查询
SELECT * FROM orders 
WHERE status = 1 
ORDER BY create_time DESC 
LIMIT 1000000, 20;

-- 问题：MySQL需要扫描前1000020条记录，然后丢弃前1000000条
-- 执行时间：5.8秒
-- 扫描行数：1,000,020行
```

### <font style="color:rgba(0, 0, 0, 0.96);">3.2 优化方案</font>

**<font style="color:rgba(0, 0, 0, 0.96);">方案一：子查询 + 延迟关联（推荐）</font>**

```plain
-- ✅ 优化：先查ID（走覆盖索引），再关联查询
SELECT o.* FROM orders o
INNER JOIN (
    SELECT id FROM orders 
    WHERE status = 1 
    ORDER BY create_time DESC 
    LIMIT 1000000, 20
) tmp ON o.id = tmp.id;

-- 执行时间：0.3秒
-- 子查询扫描行数：1,000,020行（但走覆盖索引，不回表）
-- 关联查询只需回表20次
```

**<font style="color:rgba(0, 0, 0, 0.96);">Java实现</font>**

```plain
@Service
public class OrderPaginationService {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    /**
     * ❌ 传统分页（慢）
     */
    public PageResult<Order> findOrdersTraditional(int page, int size) {
        int offset = (page - 1) * size;
        
        String sql = "SELECT * FROM orders WHERE status = 1 " +
                     "ORDER BY create_time DESC LIMIT ?, ?";
        
        List<Order> orders = jdbcTemplate.query(sql, 
            new Object[]{offset, size}, 
            orderRowMapper);
        
        return new PageResult<>(orders, page, size);
    }
    
    /**
     * ✅ 子查询优化分页（快）
     */
    public PageResult<Order> findOrdersOptimized(int page, int size) {
        int offset = (page - 1) * size;
        
        String sql = "SELECT o.* FROM orders o " +
                     "INNER JOIN (" +
                     "  SELECT id FROM orders " +
                     "  WHERE status = 1 " +
                     "  ORDER BY create_time DESC " +
                     "  LIMIT ?, ?" +
                     ") tmp ON o.id = tmp.id";
        
        List<Order> orders = jdbcTemplate.query(sql, 
            new Object[]{offset, size}, 
            orderRowMapper);
        
        return new PageResult<>(orders, page, size);
    }
}
```

**<font style="color:rgba(0, 0, 0, 0.96);">方案二：游标分页（最佳方案）</font>**

```plain
-- ✅ 使用上次查询的最后一条记录ID作为起点
SELECT * FROM orders 
WHERE status = 1 
  AND id < 999999  -- 上次查询的最后一个ID
ORDER BY id DESC 
LIMIT 20;

-- 执行时间：0.01秒
-- 扫描行数：20行
```

```plain
@Service
public class OrderCursorPaginationService {
    
    /**
     * ✅ 游标分页（推荐用于移动端滚动加载）
     */
    public CursorPageResult<Order> findOrdersByCursor(Long lastId, int size) {
        String sql;
        Object[] params;
        
        if (lastId == null) {
            // 第一页
            sql = "SELECT * FROM orders WHERE status = 1 " +
                  "ORDER BY id DESC LIMIT ?";
            params = new Object[]{size + 1};  // 多查一条判断是否有下一页
        } else {
            // 后续页
            sql = "SELECT * FROM orders WHERE status = 1 AND id < ? " +
                  "ORDER BY id DESC LIMIT ?";
            params = new Object[]{lastId, size + 1};
        }
        
        List<Order> orders = jdbcTemplate.query(sql, params, orderRowMapper);
        
        boolean hasNext = orders.size() > size;
        if (hasNext) {
            orders = orders.subList(0, size);
        }
        
        Long nextCursor = hasNext && !orders.isEmpty() 
            ? orders.get(orders.size() - 1).getId() 
            : null;
        
        return new CursorPageResult<>(orders, nextCursor, hasNext);
    }
}

// 返回对象
@Data
public class CursorPageResult<T> {
    private List<T> data;
    private Long nextCursor;  // 下次查询的起点
    private boolean hasNext;
    
    public CursorPageResult(List<T> data, Long nextCursor, boolean hasNext) {
        this.data = data;
        this.nextCursor = nextCursor;
        this.hasNext = hasNext;
    }
}
```

**<font style="color:rgba(0, 0, 0, 0.96);">方案三：分表 + 搜索引擎（海量数据）</font>**

```plain
/**
 * ✅ 千万级/亿级数据方案
 */
@Service
public class OrderBigDataService {
    
    @Autowired
    private ElasticsearchRestTemplate esTemplate;
    
    /**
     * ES做搜索和分页，MySQL存储完整数据
     */
    public PageResult<Order> searchOrders(OrderSearchDTO searchDTO) {
        // 1. ES查询，返回ID列表
        NativeSearchQuery query = buildSearchQuery(searchDTO);
        SearchHits<OrderES> searchHits = esTemplate.search(query, OrderES.class);
        
        List<Long> orderIds = searchHits.stream()
            .map(hit -> hit.getContent().getId())
            .collect(Collectors.toList());
        
        if (orderIds.isEmpty()) {
            return PageResult.empty();
        }
        
        // 2. 根据ID批量查询MySQL（保证数据一致性）
        List<Order> orders = orderRepository.findByIdIn(orderIds);
        
        // 3. 按ES的排序结果重新排列
        Map<Long, Order> orderMap = orders.stream()
            .collect(Collectors.toMap(Order::getId, o -> o));
        List<Order> sortedOrders = orderIds.stream()
            .map(orderMap::get)
            .filter(Objects::nonNull)
            .collect(Collectors.toList());
        
        return new PageResult<>(sortedOrders, 
            searchDTO.getPage(), 
            searchDTO.getSize(), 
            searchHits.getTotalHits());
    }
}
```

***

## <font style="color:rgba(0, 0, 0, 0.96);">4. 事务与死锁优化</font>

### <font style="color:rgba(0, 0, 0, 0.96);">4.1 死锁场景分析</font>

#### <font style="color:rgba(0, 0, 0, 0.96);">典型死锁场景</font>

```plain
-- 会话1
BEGIN;
UPDATE account SET balance = balance - 100 WHERE id = 1;  -- 锁住id=1
-- 等待...
UPDATE account SET balance = balance + 100 WHERE id = 2;  -- 等待id=2的锁

-- 会话2
BEGIN;
UPDATE account SET balance = balance - 50 WHERE id = 2;   -- 锁住id=2
-- 等待...
UPDATE account SET balance = balance + 50 WHERE id = 1;   -- 等待id=1的锁（死锁！）
```

### <font style="color:rgba(0, 0, 0, 0.96);">4.2 死锁解决方案</font>

**<font style="color:rgba(0, 0, 0, 0.96);">方案一：统一加锁顺序</font>**

```plain
@Service
public class AccountTransferService {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    /**
     * ❌ 可能导致死锁：加锁顺序不一致
     */
    @Transactional
    public void transferBadWay(Long fromId, Long toId, BigDecimal amount) {
        // 先锁fromId，再锁toId
        updateBalance(fromId, amount.negate());
        updateBalance(toId, amount);
    }
    
    /**
     * ✅ 避免死锁：统一按ID大小顺序加锁
     */
    @Transactional
    public void transferOptimized(Long fromId, Long toId, BigDecimal amount) {
        // 确保总是先锁ID小的，再锁ID大的
        Long firstId = Math.min(fromId, toId);
        Long secondId = Math.max(fromId, toId);
        
        // 先锁定两个账户
        Account firstAccount = lockAccount(firstId);
        Account secondAccount = lockAccount(secondId);
        
        // 再执行业务逻辑
        if (fromId.equals(firstId)) {
            firstAccount.setBalance(firstAccount.getBalance().subtract(amount));
            secondAccount.setBalance(secondAccount.getBalance().add(amount));
        } else {
            firstAccount.setBalance(firstAccount.getBalance().add(amount));
            secondAccount.setBalance(secondAccount.getBalance().subtract(amount));
        }
        
        updateAccount(firstAccount);
        updateAccount(secondAccount);
    }
    
    /**
     * 使用SELECT ... FOR UPDATE显式加锁
     */
    private Account lockAccount(Long accountId) {
        String sql = "SELECT * FROM account WHERE id = ? FOR UPDATE";
        return jdbcTemplate.queryForObject(sql, new Object[]{accountId}, accountRowMapper);
    }
}
```

**<font style="color:rgba(0, 0, 0, 0.96);">方案二：减小事务粒度</font>**

```plain
@Service
public class OrderService {
    
    /**
     * ❌ 大事务：锁持有时间长，容易死锁
     */
    @Transactional
    public void processOrderBadWay(Long orderId) {
        Order order = orderRepository.findById(orderId);
        
        // 复杂业务逻辑（耗时操作）
        calculateDiscount(order);
        checkInventory(order);
        
        // 外部调用（网络IO，非常耗时！）
        PaymentResult paymentResult = paymentService.pay(order);
        
        // 更新订单状态
        order.setStatus(OrderStatus.PAID);
        orderRepository.save(order);
    }
    
    /**
     * ✅ 小事务：只在必要时加锁
     */
    public void processOrderOptimized(Long orderId) {
        Order order = orderRepository.findById(orderId);
        
        // 1. 非事务操作：计算和检查
        calculateDiscount(order);
        checkInventory(order);
        
        // 2. 非事务操作：支付（外部调用）
        PaymentResult paymentResult = paymentService.pay(order);
        
        // 3. 事务操作：只在更新数据时开启事务
        updateOrderStatus(orderId, OrderStatus.PAID, paymentResult);
    }
    
    @Transactional
    private void updateOrderStatus(Long orderId, OrderStatus status, PaymentResult result) {
        // 事务内只做数据库更新，快速释放锁
        orderRepository.updateStatus(orderId, status);
        paymentRepository.save(result);
    }
}
```

**<font style="color:rgba(0, 0, 0, 0.96);">方案三：乐观锁替代悲观锁</font>**

```plain
-- 表结构：添加版本号字段
CREATE TABLE `inventory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `product_id` bigint NOT NULL,
  `stock` int NOT NULL,
  `version` int NOT NULL DEFAULT '0',  -- 版本号
  PRIMARY KEY (`id`),
  KEY `idx_product_id` (`product_id`)
) ENGINE=InnoDB;
```

```plain
@Service
public class InventoryService {
    
    /**
     * ❌ 悲观锁：SELECT FOR UPDATE（可能死锁）
     */
    @Transactional
    public boolean deductStockPessimistic(Long productId, int quantity) {
        String lockSql = "SELECT * FROM inventory WHERE product_id = ? FOR UPDATE";
        Inventory inventory = jdbcTemplate.queryForObject(lockSql, 
            new Object[]{productId}, inventoryRowMapper);
        
        if (inventory.getStock() < quantity) {
            return false;
        }
        
        String updateSql = "UPDATE inventory SET stock = stock - ? WHERE product_id = ?";
        jdbcTemplate.update(updateSql, quantity, productId);
        return true;
    }
    
    /**
     * ✅ 乐观锁：使用版本号（避免死锁）
     */
    @Transactional
    public boolean deductStockOptimistic(Long productId, int quantity) {
        // 1. 查询当前库存和版本号（无锁）
        String selectSql = "SELECT * FROM inventory WHERE product_id = ?";
        Inventory inventory = jdbcTemplate.queryForObject(selectSql, 
            new Object[]{productId}, inventoryRowMapper);
        
        if (inventory.getStock() < quantity) {
            return false;
        }
        
        // 2. 更新时校验版本号
        String updateSql = "UPDATE inventory " +
                           "SET stock = stock - ?, version = version + 1 " +
                           "WHERE product_id = ? AND version = ?";
        
        int affected = jdbcTemplate.update(updateSql, 
            quantity, productId, inventory.getVersion());
        
        // 3. 如果affected=0，说明版本号已变化，需要重试
        return affected > 0;
    }
    
    /**
     * ✅ 带重试机制的乐观锁
     */
    public boolean deductStockWithRetry(Long productId, int quantity) {
        int maxRetries = 3;
        for (int i = 0; i < maxRetries; i++) {
            try {
                if (deductStockOptimistic(productId, quantity)) {
                    return true;
                }
                // 版本冲突，等待后重试
                Thread.sleep(50 * (i + 1));  // 指数退避
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        return false;  // 重试失败
    }
}
```

### <font style="color:rgba(0, 0, 0, 0.96);">4.3 死锁监控与告警</font>

```plain
@Component
public class DeadlockMonitor {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    @Autowired
    private AlertService alertService;
    
    /**
     * 定时检测死锁
     */
    @Scheduled(fixedRate = 60000)  // 每分钟执行一次
    public void monitorDeadlocks() {
        try {
            String sql = "SHOW ENGINE INNODB STATUS";
            String status = jdbcTemplate.queryForObject(sql, String.class);
            
            // 检查是否包含死锁信息
            if (status.contains("LATEST DETECTED DEADLOCK")) {
                // 解析死锁信息
                String deadlockInfo = extractDeadlockInfo(status);
                
                // 发送告警
                alertService.sendAlert("MySQL死锁告警", deadlockInfo);
                
                // 记录日志
                log.error("检测到MySQL死锁: {}", deadlockInfo);
            }
        } catch (Exception e) {
            log.error("死锁监控异常", e);
        }
    }
    
    private String extractDeadlockInfo(String status) {
        // 解析SHOW ENGINE INNODB STATUS的输出
        // 提取死锁相关的SQL和表信息
        // ...
        return "死锁详细信息";
    }
}
```

***

## <font style="color:rgba(0, 0, 0, 0.96);">5. 主从复制高可用方案</font>

### <font style="color:rgba(0, 0, 0, 0.96);">5.1 半同步复制配置</font>

```plain
-- 主库配置
-- my.cnf
[mysqld]
server-id=1
log-bin=mysql-bin
binlog_format=ROW

# 开启半同步复制插件
plugin-load="rpl_semi_sync_master=semisync_master.so"
rpl_semi_sync_master_enabled=1
rpl_semi_sync_master_timeout=1000  # 超时时间1秒

-- 从库配置
-- my.cnf
[mysqld]
server-id=2
relay-log=mysql-relay-bin
read_only=1

# 开启半同步复制插件
plugin-load="rpl_semi_sync_slave=semisync_slave.so"
rpl_semi_sync_slave_enabled=1
```

### <font style="color:rgba(0, 0, 0, 0.96);">5.2 读写分离实现</font>

**<font style="color:rgba(0, 0, 0, 0.96);">方案一：Spring Boot + MyBatis多数据源</font>**

```plain
/**
 * 数据源配置
 */
@Configuration
public class DataSourceConfig {
    
    @Bean
    @ConfigurationProperties("spring.datasource.master")
    public DataSource masterDataSource() {
        return DataSourceBuilder.create().build();
    }
    
    @Bean
    @ConfigurationProperties("spring.datasource.slave")
    public DataSource slaveDataSource() {
        return DataSourceBuilder.create().build();
    }
    
    @Bean
    @Primary
    public DataSource dynamicDataSource() {
        DynamicRoutingDataSource dataSource = new DynamicRoutingDataSource();
        
        Map<Object, Object> targetDataSources = new HashMap<>();
        targetDataSources.put(DataSourceType.MASTER, masterDataSource());
        targetDataSources.put(DataSourceType.SLAVE, slaveDataSource());
        
        dataSource.setTargetDataSources(targetDataSources);
        dataSource.setDefaultTargetDataSource(masterDataSource());
        
        return dataSource;
    }
}

/**
 * 动态数据源路由
 */
public class DynamicRoutingDataSource extends AbstractRoutingDataSource {
    
    @Override
    protected Object determineCurrentLookupKey() {
        return DataSourceContextHolder.getDataSourceType();
    }
}

/**
 * 数据源上下文（ThreadLocal）
 */
public class DataSourceContextHolder {
    
    private static final ThreadLocal<DataSourceType> CONTEXT = new ThreadLocal<>();
    
    public static void setDataSourceType(DataSourceType type) {
        CONTEXT.set(type);
    }
    
    public static DataSourceType getDataSourceType() {
        return CONTEXT.get();
    }
    
    public static void clear() {
        CONTEXT.remove();
    }
}

/**
 * 自定义注解
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
public @interface DataSource {
    DataSourceType value() default DataSourceType.MASTER;
}

/**
 * AOP切面：自动切换数据源
 */
@Aspect
@Component
@Order(1)  // 确保在@Transactional之前执行
public class DataSourceAspect {
    
    @Around("@annotation(dataSource)")
    public Object around(ProceedingJoinPoint point, DataSource dataSource) throws Throwable {
        try {
            DataSourceContextHolder.setDataSourceType(dataSource.value());
            return point.proceed();
        } finally {
            DataSourceContextHolder.clear();
        }
    }
}

/**
 * 业务代码使用
 */
@Service
public class UserService {
    
    @Autowired
    private UserMapper userMapper;
    
    /**
     * 写操作：走主库
     */
    @DataSource(DataSourceType.MASTER)
    @Transactional
    public void createUser(User user) {
        userMapper.insert(user);
    }
    
    /**
     * 读操作：走从库
     */
    @DataSource(DataSourceType.SLAVE)
    public User getUserById(Long id) {
        return userMapper.selectById(id);
    }
    
    /**
     * 读操作：要求强一致性，走主库
     */
    @DataSource(DataSourceType.MASTER)
    public User getUserByIdFromMaster(Long id) {
        return userMapper.selectById(id);
    }
}
```

**<font style="color:rgba(0, 0, 0, 0.96);">方案二：ShardingSphere读写分离</font>**

```plain
# application.yml
spring:
  shardingsphere:
    datasource:
      names: master,slave0,slave1
      master:
        type: com.zaxxer.hikari.HikariDataSource
        driver-class-name: com.mysql.cj.jdbc.Driver
        jdbc-url: jdbc:mysql://master:3306/db
        username: root
        password: password
      slave0:
        type: com.zaxxer.hikari.HikariDataSource
        driver-class-name: com.mysql.cj.jdbc.Driver
        jdbc-url: jdbc:mysql://slave0:3306/db
        username: root
        password: password
      slave1:
        type: com.zaxxer.hikari.HikariDataSource
        driver-class-name: com.mysql.cj.jdbc.Driver
        jdbc-url: jdbc:mysql://slave1:3306/db
        username: root
        password: password
    
    rules:
      readwrite-splitting:
        data-sources:
          ds:
            type: Static
            props:
              write-data-source-name: master
              read-data-source-names: slave0,slave1
            load-balancer-name: round-robin
        load-balancers:
          round-robin:
            type: ROUND_ROBIN
    
    props:
      sql-show: true
```

```plain
/**
 * 使用ShardingSphere，业务代码无需修改
 */
@Service
public class UserServiceWithShardingSphere {
    
    @Autowired
    private UserMapper userMapper;
    
    /**
     * 写操作：自动路由到主库
     */
    @Transactional
    public void createUser(User user) {
        userMapper.insert(user);
    }
    
    /**
     * 读操作：自动路由到从库（轮询）
     */
    public User getUserById(Long id) {
        return userMapper.selectById(id);
    }
    
    /**
     * 强制走主库：使用HintManager
     */
    public User getUserByIdFromMaster(Long id) {
        try (HintManager hintManager = HintManager.getInstance()) {
            hintManager.setWriteRouteOnly();  // 强制走主库
            return userMapper.selectById(id);
        }
    }
}
```

### <font style="color:rgba(0, 0, 0, 0.96);">5.3 主从延迟处理</font>

```plain
/**
 * 主从延迟解决方案
 */
@Service
public class UserServiceWithDelayHandle {
    
    @Autowired
    private UserMapper userMapper;
    
    @Autowired
    private RedisTemplate<String, Object> redisTemplate;
    
    private static final String USER_CACHE_KEY = "user:";
    
    /**
     * 方案一：写入后短时间内强制读主库
     */
    @Transactional
    public void createUserWithMasterRead(User user) {
        // 1. 写入主库
        userMapper.insert(user);
        
        // 2. 标记该用户需要从主库读取（5秒内）
        String key = "master_read:user:" + user.getId();
        redisTemplate.opsForValue().set(key, "1", 5, TimeUnit.SECONDS);
    }
    
    public User getUserById(Long id) {
        // 检查是否需要强制读主库
        String key = "master_read:user:" + id;
        if (Boolean.TRUE.equals(redisTemplate.hasKey(key))) {
            return getUserByIdFromMaster(id);
        }
        
        // 正常读从库
        return userMapper.selectById(id);
    }
    
    /**
     * 方案二：写入后同步缓存，读取时优先读缓存
     */
    @Transactional
    public void createUserWithCache(User user) {
        // 1. 写入主库
        userMapper.insert(user);
        
        // 2. 同步写入缓存
        String cacheKey = USER_CACHE_KEY + user.getId();
        redisTemplate.opsForValue().set(cacheKey, user, 10, TimeUnit.MINUTES);
    }
    
    public User getUserByIdWithCache(Long id) {
        // 1. 先查缓存
        String cacheKey = USER_CACHE_KEY + id;
        User user = (User) redisTemplate.opsForValue().get(cacheKey);
        if (user != null) {
            return user;
        }
        
        // 2. 缓存没有，查从库
        user = userMapper.selectById(id);
        if (user != null) {
            redisTemplate.opsForValue().set(cacheKey, user, 10, TimeUnit.MINUTES);
        }
        
        return user;
    }
    
    @DataSource(DataSourceType.MASTER)
    private User getUserByIdFromMaster(Long id) {
        return userMapper.selectById(id);
    }
}
```

***

## <font style="color:rgba(0, 0, 0, 0.96);">6. 综合优化最佳实践</font>

### <font style="color:rgba(0, 0, 0, 0.96);">6.1 慢查询日志分析</font>

```plain
-- 开启慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  -- 超过1秒的查询记录为慢查询
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
```

```plain
/**
 * 慢查询监控与分析
 */
@Component
public class SlowQueryMonitor {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    /**
     * 定时分析慢查询日志
     */
    @Scheduled(cron = "0 0 2 * * ?")  // 每天凌晨2点执行
    public void analyzeSlowQueries() {
        // 使用pt-query-digest分析慢查询日志
        String command = "pt-query-digest /var/log/mysql/slow.log > /tmp/slow_query_report.txt";
        // 执行命令...
        
        // 发送报告
        sendSlowQueryReport();
    }
    
    /**
     * 获取当前慢查询统计
     */
    public List<SlowQueryInfo> getSlowQueryStats() {
        String sql = "SELECT " +
                     "  sql_text, " +
                     "  count_star as exec_count, " +
                     "  avg_timer_wait / 1000000000000 as avg_time_sec, " +
                     "  sum_rows_examined as total_rows_scanned " +
                     "FROM performance_schema.events_statements_summary_by_digest " +
                     "WHERE avg_timer_wait > 1000000000000 " +  // 超过1秒
                     "ORDER BY avg_timer_wait DESC " +
                     "LIMIT 20";
        
        return jdbcTemplate.query(sql, slowQueryRowMapper);
    }
}
```

### <font style="color:rgba(0, 0, 0, 0.96);">6.2 连接池优化</font>

```plain
# application.yml
spring:
  datasource:
    type: com.zaxxer.hikari.HikariDataSource
    hikari:
      # 连接池配置
      minimum-idle: 10              # 最小空闲连接数
      maximum-pool-size: 50         # 最大连接数
      connection-timeout: 30000     # 连接超时时间（毫秒）
      idle-timeout: 600000          # 空闲连接超时时间（10分钟）
      max-lifetime: 1800000         # 连接最大生命周期（30分钟）
      
      # 连接测试
      connection-test-query: SELECT 1
      validation-timeout: 5000
      
      # 性能优化
      auto-commit: true
      read-only: false
      
      # 连接池名称
      pool-name: HikariCP-MySQL
```

```plain
/**
 * 连接池监控
 */
@Component
public class DataSourceMonitor {
    
    @Autowired
    private DataSource dataSource;
    
    @Scheduled(fixedRate = 60000)  // 每分钟
    public void monitorConnectionPool() {
        if (dataSource instanceof HikariDataSource) {
            HikariDataSource hikariDS = (HikariDataSource) dataSource;
            HikariPoolMXBean poolMXBean = hikariDS.getHikariPoolMXBean();
            
            log.info("连接池状态 - 活跃连接: {}, 空闲连接: {}, 等待线程: {}, 总连接: {}",
                poolMXBean.getActiveConnections(),
                poolMXBean.getIdleConnections(),
                poolMXBean.getThreadsAwaitingConnection(),
                poolMXBean.getTotalConnections());
            
            // 告警：连接池使用率超过80%
            if (poolMXBean.getActiveConnections() > hikariDS.getMaximumPoolSize() * 0.8) {
                log.warn("连接池使用率过高！");
                // 发送告警...
            }
        }
    }
}
```

### <font style="color:rgba(0, 0, 0, 0.96);">6.3 SQL审核与规范</font>

```plain
/**
 * SQL拦截器：审核SQL规范
 */
@Component
@Intercepts({
    @Signature(
        type = StatementHandler.class,
        method = "prepare",
        args = {Connection.class, Integer.class}
    )
})
public class SqlAuditInterceptor implements Interceptor {
    
    private static final int MAX_LIMIT = 1000;
    
    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        StatementHandler statementHandler = (StatementHandler) invocation.getTarget();
        BoundSql boundSql = statementHandler.getBoundSql();
        String sql = boundSql.getSql().toLowerCase();
        
        // 1. 检查是否有LIMIT
        if (sql.contains("select") && !sql.contains("limit")) {
            log.warn("SQL未添加LIMIT: {}", sql);
        }
        
        // 2. 检查LIMIT是否过大
        Pattern pattern = Pattern.compile("limit\\s+(\\d+)");
        Matcher matcher = pattern.matcher(sql);
        if (matcher.find()) {
            int limit = Integer.parseInt(matcher.group(1));
            if (limit > MAX_LIMIT) {
                throw new IllegalArgumentException(
                    "LIMIT不能超过" + MAX_LIMIT + ", 当前: " + limit);
            }
        }
        
        // 3. 检查是否使用SELECT *
        if (sql.contains("select *")) {
            log.warn("不建议使用SELECT *, 应该明确指定字段: {}", sql);
        }
        
        // 4. 检查是否有WHERE条件（UPDATE/DELETE）
        if ((sql.contains("update") || sql.contains("delete")) 
            && !sql.contains("where")) {
            throw new IllegalArgumentException(
                "UPDATE/DELETE必须包含WHERE条件: " + sql);
        }
        
        return invocation.proceed();
    }
}
```

***

## <font style="color:rgba(0, 0, 0, 0.96);">总结</font>

### <font style="color:rgba(0, 0, 0, 0.96);">优化决策树</font>

```plain
遇到MySQL性能问题
    ↓
是否开启了慢查询日志？
    ↓ 是
查看EXPLAIN执行计划
    ↓
是否走索引？
    ↓ 否
检查索引失效原因：
    - 函数/类型转换？
    - LIKE前缀模糊？
    - OR条件？
    - 优化器选择？
    ↓ 已走索引但仍慢
检查是否回表？
    ↓ 是
    - 考虑覆盖索引
    - 考虑索引下推
    ↓
是否深分页？
    ↓ 是
    - 子查询优化
    - 游标分页
    ↓
是否高并发死锁？
    ↓ 是
    - 统一加锁顺序
    - 减小事务粒度
    - 乐观锁替代悲观锁
    ↓
是否主从延迟？
    ↓ 是
    - 半同步复制
    - 写后短时读主库
    - 缓存方案
```

### <font style="color:rgba(0, 0, 0, 0.96);">关键指标</font>

| **<font style="color:rgba(0, 0, 0, 0.96);">指标</font>** | **<font style="color:rgba(0, 0, 0, 0.96);">阈值</font>** | **<font style="color:rgba(0, 0, 0, 0.96);">说明</font>** |
| --- | --- | --- |
| <font style="color:rgba(0, 0, 0, 0.96);">查询响应时间</font> | <font style="color:rgba(0, 0, 0, 0.96);">< 100ms</font> | <font style="color:rgba(0, 0, 0, 0.96);">超过需优化</font> |
| <font style="color:rgba(0, 0, 0, 0.96);">慢查询比例</font> | <font style="color:rgba(0, 0, 0, 0.96);">< 1%</font> | <font style="color:rgba(0, 0, 0, 0.96);">慢查询/总查询</font> |
| <font style="color:rgba(0, 0, 0, 0.96);">连接池使用率</font> | <font style="color:rgba(0, 0, 0, 0.96);">< 80%</font> | <font style="color:rgba(0, 0, 0, 0.96);">超过需扩容</font> |
| <font style="color:rgba(0, 0, 0, 0.96);">主从延迟</font> | <font style="color:rgba(0, 0, 0, 0.96);">< 1s</font> | <font style="color:rgba(0, 0, 0, 0.96);">超过影响业务</font> |
| <font style="color:rgba(0, 0, 0, 0.96);">索引命中率</font> | <font style="color:rgba(0, 0, 0, 0.96);">> 95%</font> | <font style="color:rgba(0, 0, 0, 0.96);">InnoDB Buffer Pool</font> |
| <font style="color:rgba(0, 0, 0, 0.96);">死锁频率</font> | <font style="color:rgba(0, 0, 0, 0.96);">0</font> | <font style="color:rgba(0, 0, 0, 0.96);">每小时死锁次数</font> |

**<font style="color:rgba(0, 0, 0, 0.96);">Look at me! 这才是真正的MySQL优化方案，不是简单说一句"加个索引"就完事了！</font>**
