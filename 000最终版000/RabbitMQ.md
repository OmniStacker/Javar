# RabbitMQ知识汇总

## 目录

1. [RabbitMQ概述](#1-rabbitmq概述)
2. [核心组件](#2-核心组件)
3. [交换机类型](#3-交换机类型)
4. [消息模式](#4-消息模式)
5. [消息持久化](#5-消息持久化)
6. [死信队列](#6-死信队列)
7. [集群构建](#7-集群构建)
8. [事务处理](#8-事务处理)
9. [常用插件](#9-常用插件)

---

## 1. RabbitMQ概述

### 1.1 什么是RabbitMQ？

RabbitMQ是基于AMQP协议的开源消息代理软件，实现了高级消息队列协议（AMQP）。

### 1.2 显著特点

- 可靠性：支持持久化、确认机制
- 灵活的路由：多种交换机类型
- 集群：支持分布式部署
- 插件：丰富的插件生态
- 多语言客户端

---

## 2. 核心组件

### 2.1 RabbitMQ的核心组件

1. **Broker**：消息代理服务器
2. **Exchange**：交换机，接收消息并路由到队列
3. **Queue**：消息队列，存储消息
4. **Binding**：绑定，交换机与队列的路由规则
5. **Channel**：信道，连接中的虚拟连接
6. **Connection**：连接，TCP连接
7. **Producer**：消息生产者
8. **Consumer**：消息消费者

---

## 3. 交换机类型

### 3.1 RabbitMQ中有哪几种交换机类型？

1. **Direct Exchange**：直连交换机，精确匹配路由键
2. **Topic Exchange**：主题交换机，通配符匹配
3. **Fanout Exchange**：扇形交换机，广播所有绑定队列
4. **Headers Exchange**：头交换机，匹配消息头

---

## 4. 消息模式

### 4.1 RabbitMQ支持哪些消息模式？

1. **简单模式**：一个生产者，一个消费者
2. **工作队列模式**：一个生产者，多个消费者
3. **发布订阅模式**：一个生产者，多个消费者
4. **路由模式**：根据路由键选择队列
5. **主题模式**：根据通配符路由

---

## 5. 消息持久化

### 5.1 RabbitMQ如何实现消息的持久化？

**持久化配置**：
1. 交换机持久化
2. 队列持久化
3. 消息持久化

**代码示例**：
```java
// 声明持久化队列
channel.queueDeclare("queue_name", true, false, false, null);

// 发布持久化消息
channel.basicPublish("exchange", "routingKey", 
    MessageProperties.PERSISTENT_TEXT_PLAIN, message.getBytes());
```

---

## 6. 死信队列

### 6.1 RabbitMQ是如何实现死信队列的？

**死信原因**：
- 消息被拒绝（basic.reject/basic.nack）
- 消息过期
- 队列达到最大长度

**配置**：
```java
Map<String, Object> args = new HashMap<>();
args.put("x-dead-letter-exchange", "dlx.exchange");
args.put("x-dead-letter-routing-key", "dlx.routing.key");
channel.queueDeclare("queue_name", true, false, false, args);
```

---

## 7. 集群构建

### 7.1 RabbitMQ如何构建集群？

**集群方式**：
1. **磁盘节点**：存储元数据
2. **内存节点**：仅存储数据
3. **镜像队列**：数据冗余

**配置步骤**：
1. 配置hosts
2. 同步cookie
3. 加入集群
4. 设置镜像策略

---

## 8. 事务处理

### 8.1 RabbitMQ中如何进行事务处理？

**事务方式**：
```java
channel.txSelect();  // 开启事务
channel.txCommit();  // 提交事务
channel.txRollback(); // 回滚事务
```

**确认机制**：
```java
channel.confirmSelect();  // 开启确认模式
channel.waitForConfirms(); // 等待确认
```

---

## 9. 常用插件

### 9.1 聊一聊常用的RabbitMQ插件

1. **rabbitmq_management**：Web管理界面
2. **rabbitmq_delayed_message_exchange**：延迟消息
3. **rabbitmq_shovel**：跨集群消息复制
4. **rabbitmq_federation**：联邦队列
5. **rabbitmq_consistent_hash_exchange**：一致性哈希交换机

---

## 总结

本文档汇总了RabbitMQ的核心知识点：

1. **概述**：定义、特点
2. **核心组件**：Broker、Exchange、Queue、Binding等
3. **交换机类型**：Direct、Topic、Fanout、Headers
4. **消息模式**：简单、工作队列、发布订阅、路由、主题
5. **消息持久化**：交换机、队列、消息持久化
6. **死信队列**：死信原因、配置方法
7. **集群构建**：磁盘节点、内存节点、镜像队列
8. **事务处理**：事务方式、确认机制
9. **常用插件**：管理界面、延迟消息等

通过本文档，可以系统性地掌握RabbitMQ的核心概念。