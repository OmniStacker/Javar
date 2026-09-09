# Nginx知识汇总

## 目录

1. [Nginx概述](#1-nginx概述)
2. [事件驱动模型](#2-事件驱动模型)
3. [负载均衡](#3-负载均衡)
4. [反向代理与正向代理](#4-反向代理与正向代理)
5. [缓存与压缩](#5-缓存与压缩)
6. [安全与访问控制](#6-安全与访问控制)
7. [性能优化](#7-性能优化)
8. [常见问题](#8-常见问题)

---

## 1. Nginx概述

### 1.1 什么是Nginx？

Nginx（发音为"engine-x"）是一个开源的高性能、轻量级的Web服务器软件和反向代理服务器。

**主要用途**：
1. **Web服务器**：提供静态资源服务
2. **反向代理**：转发客户端请求到后端服务器
3. **负载均衡**：在多个后端服务器间分配请求
4. **SSL终端**：终止SSL/TLS连接
5. **缓存**：缓存经常请求的内容
6. **安全性和访问控制**：限制IP访问、安全防护

### 1.2 Nginx的特点

- 高性能、轻量级
- 解决C10k问题
- 高并发处理能力
- 低内存占用
- 高可靠性

---

## 2. 事件驱动模型

### 2.1 Nginx的事件驱动模型是什么？

**事件驱动模型**：
- 基于事件驱动的非阻塞I/O
- 使用epoll（Linux）/kqueue（BSD）等系统调用
- 一个工作进程可以处理数千个连接

**为什么这种模型对性能有益**：
- 不需要为每个连接创建线程
- 减少上下文切换开销
- 内存占用低
- 高并发性能优秀

### 2.2 Nginx如何处理并发请求？

**处理方式**：
1. 主进程（Master Process）管理工作进程
2. 工作进程（Worker Process）处理请求
3. 每个工作进程独立处理多个连接
4. 使用事件驱动模型，非阻塞I/O

**配置优化**：
```nginx
worker_processes auto;  # 自动设置为CPU核心数
events {
    worker_connections 10240;  # 每个worker最大连接数
    use epoll;  # 使用epoll事件驱动
}
```

### 2.3 Nginx的工作进程和线程池

**工作进程配置**：
```nginx
worker_processes auto;  # 自动设置为CPU核心数
worker_cpu_affinity auto;  # CPU亲和性
```

**线程池配置**：
```nginx
thread_pool default threads=32 max_queue=65536;
```

---

## 3. 负载均衡

### 3.1 什么是负载均衡？Nginx是如何实现负载均衡的？

**负载均衡**：将请求分配到多个后端服务器，避免单一服务器过载。

**负载均衡策略**：
1. **轮询（Round Robin）**：默认策略
2. **加权轮询（Weighted Round Robin）**：按权重分配
3. **IP哈希（IP Hash）**：同一IP分配到同一服务器
4. **最少连接（Least Connections）**：分配到连接数最少的服务器
5. **通用哈希（Generic Hash）**：自定义哈希键

**配置示例**：
```nginx
upstream backend {
    server 192.168.1.10:8080 weight=3;
    server 192.168.1.11:8080 weight=2;
    server 192.168.1.12:8080 backup;
}
```

---

## 4. 反向代理与正向代理

### 4.1 反向代理和正向代理的区别

| 特性 | 反向代理 | 正向代理 |
|------|----------|----------|
| **代理对象** | 服务器 | 客户端 |
| **可见性** | 对客户端透明 | 服务器可见代理 |
| **用途** | 负载均衡、缓存 | 访问控制、加速 |
| **配置位置** | 服务器端 | 客户端 |

**反向代理配置**：
```nginx
location / {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 5. 缓存与压缩

### 5.1 如何在Nginx中配置缓存？

**缓存配置**：
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=10g inactive=60m;

location / {
    proxy_cache my_cache;
    proxy_cache_valid 200 301 302 10m;
    proxy_cache_valid any 5m;
    proxy_pass http://backend;
}
```

### 5.2 如何设置HTTP压缩？

**Gzip压缩配置**：
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1024;
gzip_comp_level 6;
```

### 5.3 Nginx如何处理静态文件？如何优化？

**静态文件处理**：
```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

**优化方法**：
1. 开启sendfile
2. 开启tcp_nopush
3. 设置expires缓存头
4. 使用CDN

---

## 6. 安全与访问控制

### 6.1 如何在Nginx中实现基于IP的访问控制？

**IP黑白名单**：
```nginx
location /admin {
    allow 192.168.1.0/24;
    deny all;
}
```

### 6.2 如何防止恶意请求和爬虫？

**防护措施**：
1. 限制请求频率
2. 限制User-Agent
3. 限制Referer
4. 使用WAF模块

**配置示例**：
```nginx
location / {
    limit_req zone=one burst=10 nodelay;
    if ($http_user_agent ~* (bot|crawler|spider)) {
        return 403;
    }
}
```

### 6.3 什么是DDoS攻击？Nginx如何帮助缓解？

**DDoS攻击**：分布式拒绝服务攻击

**缓解措施**：
1. 限制连接数
2. 限制请求频率
3. 使用CDN
4. 配置防火墙规则

### 6.4 什么是缓冲区溢出？Nginx如何防止？

**缓冲区溢出**：向缓冲区写入超过其容量的数据

**防护措施**：
1. 限制请求体大小
2. 限制头部大小
3. 使用安全配置

---

## 7. 性能优化

### 7.1 如何调整Nginx配置以优化性能？

**系统层面**：
1. 增加文件描述符限制
2. 调整TCP参数
3. 开启TCP_NODELAY

**Nginx配置**：
```nginx
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 10240;
    use epoll;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
}
```

### 7.2 什么是HTTP/2协议？Nginx如何支持？

**HTTP/2优势**：
- 多路复用
- 头部压缩
- 服务器推送
- 二进制分帧

**配置**：
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
}
```

### 7.3 什么是WebSocket？Nginx如何支持？

**WebSocket**：全双工通信协议

**配置**：
```nginx
location /ws {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### 7.4 什么是HTTP长连接和短连接？

**长连接**：
- 一个TCP连接处理多个请求
- 减少连接建立开销
- 通过Keep-Alive实现

**短连接**：
- 一个请求一个连接
- 简单但效率低

**配置**：
```nginx
keepalive_timeout 65;
keepalive_requests 100;
```

---

## 8. 常见问题

### 8.1 Lua模块有什么用？

**Lua模块**：
- 在Nginx中嵌入Lua脚本
- 定制请求处理流程
- 实现复杂业务逻辑

**应用场景**：
- 动态路由
- 请求鉴权
- 数据转换

### 8.2 如何配置Nginx作为反向代理服务器缓存后端响应？

**配置**：
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=backend_cache:10m;

location / {
    proxy_cache backend_cache;
    proxy_cache_valid 200 301 302 10m;
    proxy_pass http://backend;
}
```

---

## 总结

本文档系统性地汇总了Nginx的核心知识点，包括：

1. **Nginx概述**：定义、特点、主要用途
2. **事件驱动模型**：事件驱动、并发处理、工作进程配置
3. **负载均衡**：负载均衡策略、配置方法
4. **反向代理与正向代理**：区别、配置方法
5. **缓存与压缩**：缓存配置、Gzip压缩、静态文件优化
6. **安全与访问控制**：IP访问控制、DDoS防护、缓冲区溢出防护
7. **性能优化**：系统配置、HTTP/2、WebSocket、长连接
8. **常见问题**：Lua模块、缓存配置

通过本文档，可以系统性地掌握Nginx的核心概念和实践方法。