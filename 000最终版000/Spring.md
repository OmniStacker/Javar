# Spring知识汇总

## 目录

1. [Spring概述](#1-spring概述)
2. [IoC容器](#2-ioc容器)
3. [AOP面向切面编程](#3-aop面向切面编程)
4. [Spring事务](#4-spring事务)
5. [Spring MVC](#5-spring-mvc)
6. [Spring常用注解](#6-spring常用注解)
7. [Spring设计模式](#7-spring设计模式)
8. [Spring扩展点](#8-spring扩展点)

---

## 1. Spring概述

### 1.1 什么是Spring？

Spring是一个轻量级的Java开发框架，核心特性：
- IoC（控制反转）
- AOP（面向切面编程）
- 声明式事务
- 测试支持

---

## 2. IoC容器

### 2.1 什么是IoC？

**IoC（控制反转）**：将对象的创建、依赖注入交给Spring容器管理。

### 2.2 Bean的生命周期

1. 实例化
2. 属性赋值
3. 初始化（BeanPostProcessor、InitializingBean、init-method）
4. 使用
5. 销毁（DisposableBean、destroy-method）

### 2.3 Bean的作用域

- singleton：单例（默认）
- prototype：原型
- request：请求
- session：会话
- global-session：全局会话

### 2.4 依赖注入方式

1. 构造器注入
2. Setter注入
3. 字段注入（@Autowired）

---

## 3. AOP面向切面编程

### 3.1 什么是AOP？

**AOP（面向切面编程）**：通过预编译方式和运行期动态代理实现程序功能的统一维护。

### 3.2 AOP核心概念

- **切面（Aspect）**：横切关注点的模块化
- **连接点（Joinpoint）**：程序执行过程中的某个点
- **通知（Advice）**：切面的实现
- **切点（Pointcut）**：匹配连接点的表达式
- **引入（Introduction）**：添加方法或字段
- **目标对象（Target）**：被代理的对象
- **织入（Weaving）**：创建代理对象

### 3.3 通知类型

- **Before**：前置通知
- **After**：后置通知
- **AfterReturning**：返回通知
- **AfterThrowing**：异常通知
- **Around**：环绕通知

---

## 4. Spring事务

### 4.1 Spring事务的传播机制

1. **PROPAGATION_REQUIRED**：默认，支持当前事务，不存在则新建
2. **PROPAGATION_REQUIRES_NEW**：新建事务，挂起当前事务
3. **PROPAGATION_NESTED**：嵌套事务
4. **PROPAGATION_SUPPORTS**：支持当前事务，不存在则以非事务执行
5. **PROPAGATION_NOT_SUPPORTED**：以非事务执行，挂起当前事务
6. **PROPAGATION_NEVER**：以非事务执行，存在事务则异常
7. **PROPAGATION_MANDATORY**：必须在事务中执行，不存在则异常

### 4.2 Spring事务的隔离级别

- DEFAULT：默认
- READ_UNCOMMITTED
- READ_COMMITTED
- REPEATABLE_READ
- SERIALIZABLE

### 4.3 事务失效场景

1. 方法不是public
2. 自调用
3. 异常被捕获
4. 抛出checked异常
5. 数据库不支持事务

---

## 5. Spring MVC

### 5.1 Spring MVC工作流程

1. 用户请求到DispatcherServlet
2. HandlerMapping查找Handler
3. HandlerAdapter执行Handler
4. Handler返回ModelAndView
5. ViewResolver解析View
6. 渲染View返回

### 5.2 核心组件

- DispatcherServlet：前端控制器
- HandlerMapping：处理器映射
- HandlerAdapter：处理器适配器
- ViewResolver：视图解析器

---

## 6. Spring常用注解

### 6.1 核心注解

- @Component：组件
- @Service：服务层
- @Repository：DAO层
- @Controller：控制器
- @Autowired：自动注入
- @Qualifier：指定注入
- @Resource：JSR-250注解
- @Configuration：配置类
- @Bean：定义Bean

### 6.2 Web相关注解

- @RequestMapping：映射请求
- @GetMapping：GET请求
- @PostMapping：POST请求
- @PutMapping：PUT请求
- @DeleteMapping：DELETE请求
- @ResponseBody：返回JSON
- @RequestBody：接收JSON
- @RestController：Controller+ResponseBody

---

## 7. Spring设计模式

### 7.1 Spring中使用的设计模式

1. **工厂模式**：BeanFactory、ApplicationContext
2. **单例模式**：Bean默认单例
3. **代理模式**：AOP动态代理
4. **模板方法**：JdbcTemplate、RestTemplate
5. **观察者模式**：事件监听
6. **策略模式**：ResourceLoader
7. **装饰器模式**：BeanWrapper

---

## 8. Spring扩展点

### 8.1 常用扩展点

1. BeanPostProcessor
2. BeanFactoryPostProcessor
3. InitializingBean
4. DisposableBean
5. ApplicationContextAware
6. BeanNameAware
7. ApplicationListener

---

## 总结

本文档汇总了Spring的核心知识点：

1. **概述**：Spring框架介绍
2. **IoC容器**：控制反转、Bean生命周期、作用域、依赖注入
3. **AOP**：面向切面编程、核心概念、通知类型
4. **Spring事务**：传播机制、隔离级别、失效场景
5. **Spring MVC**：工作流程、核心组件
6. **常用注解**：核心注解、Web注解
7. **设计模式**：Spring中使用的设计模式
8. **扩展点**：常用Spring扩展点

通过本文档，可以系统性地掌握Spring的核心概念。