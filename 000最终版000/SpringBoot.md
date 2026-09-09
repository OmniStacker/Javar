# SpringBoot知识汇总

## 目录

1. [SpringBoot概述](#1-springboot概述)
2. [启动原理](#2-启动原理)
3. [自动配置](#3-自动配置)
4. [Starter机制](#4-starter机制)
5. [打包与运行](#5-打包与运行)
6. [常见问题](#6-常见问题)

---

## 1. SpringBoot概述

### 1.1 谈谈你对SpringBoot的理解？

SpringBoot是Spring的快速启动框架，核心特性：
- 自动配置
- 起步依赖
- 内嵌服务器
- 生产就绪

### 1.2 Spring和SpringBoot的关系和区别？

| 特性 | Spring | SpringBoot |
|------|--------|------------|
| **配置** | XML/Java配置 | 自动配置 |
| **服务器** | 需外置 | 内嵌 |
| **依赖** | 手动管理 | 起步依赖 |
| **部署** | 部署到服务器 | 可执行jar |

---

## 2. 启动原理

### 2.1 SpringBoot的启动原理？

**启动流程**：
1. 创建SpringApplication对象
2. 运行run方法
3. 准备环境
4. 创建ApplicationContext
5. 自动配置
6. 刷新上下文
7. 启动内嵌服务器

### 2.2 SpringBoot可以同时处理多少请求？

- 默认Tomcat：200个线程
- 可通过配置调整：server.tomcat.max-threads

---

## 3. 自动配置

### 3.1 Springboot的自动配置原理？

**原理**：
1. @EnableAutoConfiguration
2. @Import(AutoConfigurationImportSelector)
3. 读取META-INF/spring.factories
4. 条件匹配（@ConditionalOnClass等）
5. 自动配置Bean

**条件注解**：
- @ConditionalOnClass
- @ConditionalOnMissingBean
- @ConditionalOnProperty

---

## 4. Starter机制

### 4.1 SpringBoot如何自定义Starter？

**步骤**：
1. 创建Starter项目
2. 定义自动配置类
3. 创建spring.factories
4. 添加依赖

**命名规范**：
- 官方：spring-boot-starter-xxx
- 自定义：xxx-spring-boot-starter

---

## 5. 打包与运行

### 5.1 为什么SpringBoot的jar可以直接运行？

**原因**：
- 使用spring-boot-maven-plugin
- 打包为fat jar
- 内嵌服务器
- 可执行入口

**jar结构**：
- BOOT-INF/classes
- BOOT-INF/lib
- META-INF

---

## 6. 常见问题

### 6.1 SpringBoot为什么要禁止循环依赖？

**原因**：
- 设计问题
- 可能导致不可预知的行为
- 增加调试难度

**解决方案**：
- 重构代码
- 使用@Lazy

### 6.2 SpringBoot为什么默认使用CGLIB？

**原因**：
- 支持无接口类代理
- 性能较好

### 6.3 如何对SpringBoot配置文件和代码加密？

**方案**：
1. 使用jasypt加密配置文件
2. 使用ProGuard混淆代码
3. 使用自定义ClassLoader

---

## 总结

本文档汇总了SpringBoot的核心知识点：

1. **概述**：SpringBoot介绍、与Spring区别
2. **启动原理**：启动流程
3. **自动配置**：自动配置原理、条件注解
4. **Starter机制**：自定义Starter
5. **打包与运行**：jar运行原理
6. **常见问题**：循环依赖、CGLIB、加密

通过本文档，可以系统性地掌握SpringBoot的核心概念。