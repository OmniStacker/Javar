# Nginx 知识梳理：从并发模型到反向代理配置

Nginx（读作 "engine-x"）是 Java 后端开发者绕不开的一层基础设施：它通常部署在 Tomcat / Spring Boot 应用前面，负责接收客户端请求、决定请求怎么被处理。本文按"是什么 → 为什么需要 → 怎么用/怎么配"的顺序，把并发模型、静态文件、缓存、反向代理、负载均衡、location 与 rewrite、gzip、HTTP/2、WebSocket、限流与安全控制等主题串起来，并给出可直接参考的配置片段。文中涉及的指令默认值与版本信息，均以官方文档为准；会随版本变化的数字，请以实际环境的 `nginx -V` 与对应版本文档复核。

## 本文导读

- 一、Nginx 是什么：定位与核心用途
- 二、事件驱动模型：为什么它能扛住高并发
- 三、工作进程、线程池与多核配置
- 四、连接管理：长连接、短连接与 keep-alive
- 五、静态文件：怎么发文件，怎么优化
- 六、缓存：代理缓存与浏览器缓存
- 七、反向代理与正向代理的区别
- 八、负载均衡：算法与 upstream 参数
- 九、location 匹配与 rewrite 规则
- 十、HTTP 压缩：gzip 的正确配置
- 十一、HTTP/2 与 HTTP/3
- 十二、WebSocket 代理
- 十三、IP 访问控制：allow / deny
- 十四、限流、防爬虫与 DDoS 缓解
- 十五、超时与缓冲区参数速查（含缓冲区溢出辨析）
- 十六、用 Lua 扩展请求处理（OpenResty）
- 十七、常用运维命令与排错
- 参考资料

## 一、Nginx 是什么：定位与核心用途

Nginx 是一个用 C 语言编写的高性能 Web 服务器，同时也是反向代理、内容缓存与负载均衡器。它站在客户端和你的 Java 应用之间，决定请求"能不能进、由谁处理、能不能直接给结果"。

可以把它想成一栋写字楼的前台：访客（客户端请求）不直接闯进办公室（后端应用），而是先到前台登记；前台可以核验证件（访问控制、TLS 终止），可以回答常见问题（静态文件与缓存），也可以把访客按当前忙闲分派给不同部门（负载均衡）。这个比喻能覆盖 Nginx 的绝大多数角色。

它最初由 Igor Sysoev 编写，以 2-clause BSD 许可开源，诞生于 2000 年代中期，公认的设计目标之一是应对 C10k 问题——即"单机同时保持上万条连接"。在 Java 项目里，你最常见到的位置是：浏览器 → Nginx（80/443）→ Spring Boot（8080）。

| 角色 | 做什么 | 典型场景 |
| --- | --- | --- |
| Web 服务器 | 直接返回 HTML、CSS、JS、图片等静态资源 | 前端打包产物托管 |
| 反向代理 | 把请求转发给后端应用，隐藏真实服务地址 | 前后端分离、灰度发布 |
| 负载均衡 | 把请求分给多台后端实例 | 多副本部署 |
| TLS 终止 | 在 Nginx 上解密 HTTPS，再以明文转发给内网应用 | 证书统一管理 |
| 内容缓存 | 缓存后端响应，减少回源 | 商品详情、首页 |
| 访问控制 | 按 IP、请求速率、来源页限制访问 | 后台管理口、防刷 |

最小可用的配置骨架如下。Nginx 配置是分层的：`http` 块管 HTTP 全局，`server` 块代表一个虚拟主机，`location` 块决定某个 URL 前缀怎么处理；内层没有写的指令会从外层继承。

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    server {
        listen      80;
        server_name example.com;

        location / {
            root  /usr/share/nginx/html;
            index index.html;
        }
    }
}
```

改完配置后，先用 `nginx -t` 校验语法，再用 `nginx -s reload` 平滑重载：主进程读取新配置并启动新的工作进程，旧工作进程把存量请求处理完后退出，因此通常不会中断线上流量。

## 二、事件驱动模型：为什么它能扛住高并发

本节解释 Nginx 处理连接的基本方式，以及这种方式为什么在高并发下比"一个连接一个线程"更省资源。理解它之后，后面所有性能相关的参数（工作进程数、连接数、线程池）才有落脚点。

关键在于一个比喻：餐厅里 20 桌客人，如果每桌配一名服务员，大部分时间服务员都在等客人点菜（等数据到达），人力浪费；如果一名服务员来回巡场，只在客人举手时才过去（事件通知），人力就能被充分利用。Nginx 的工作进程就是那名巡场的服务员。

事件驱动模型由四个要素组成：

1. **事件循环**：工作进程不断询问操作系统"哪些连接有新动静"（新连接到达、数据可读、可写），拿到事件后调用对应的处理逻辑。
2. **非阻塞 I/O**：读写不会原地等待，没有数据就立刻返回，工作进程转去处理别的连接。
3. **多路复用**：一次系统调用就能同时监听成千上万个连接。Linux 上常用 `epoll`，FreeBSD/macOS 上是 `kqueue`，Solaris 上是 event ports。
4. **事件处理器**：每种事件绑定一段处理代码，事件就绪即触发，例如读取请求、写回响应、关闭连接。

这种模型对性能的收益：

| 收益点 | 原因 |
| --- | --- |
| 资源占用低 | 不为每条连接创建线程或进程，连接状态只占少量内存 |
| 上下文切换少 | 线程数少，CPU 不用频繁保存/恢复线程现场 |
| 并发能力高 | 单线程即可管理大量连接，不会因线程数耗尽而拒绝服务 |
| 响应延迟低 | 非阻塞 I/O 让工作进程总在处理"有进展"的连接 |

需要同时知道它的代价：工作进程是单线程的，任何一次阻塞调用（例如读大文件、同步 DNS 解析）都会卡住该进程上的所有连接。这也正是下一节要引入线程池的原因。

## 三、工作进程、线程池与多核配置

本节讲 Nginx 的进程/线程结构，以及如何让它吃满多核 CPU。这是"配置 Nginx 优化性能"时最先要动的几个参数。

**工作进程（worker process）**：真正处理请求的进程。每个工作进程是单线程的，靠事件循环并发处理多条连接。主进程（master）只负责读配置、管理 worker、平滑重载，不处理请求。

**线程池（thread pool）**：一组可选的后台线程，主要用来把"读文件、发文件"这类可能阻塞的磁盘操作从工作进程上挪走，避免拖慢事件循环。它由 `thread_pool` 指令定义（1.7.11 起），再通过 `aio threads;` 启用。

关于两个常见误解，这里需要按官方文档更正：

- 不存在 `worker_threads` 指令。定义线程池用的是 `thread_pool 名字 threads=N max_queue=M;`，默认已有一个名为 `default` 的池，参数为 `threads=32 max_queue=65536`。
- 线程池并非用来"解析 DNS、做 SSL 加解密"，它的设计目的是非阻塞地读写文件（`sendfile` 之外的路径）。DNS 解析、SSL 握手属于其它机制。

配置多核的几个要点：

1. **`worker_processes`**：默认值为 `1`。官方建议以 CPU 核心数为起点（`auto` 会自动探测，1.3.8 / 1.2.5 起支持）。流传较广的说法"设为 CPU 核心数的 1.5 倍左右"并无官方依据，这里按官方建议取"等于核心数"，再按压测结果微调。
2. **`worker_connections`**：单个工作进程允许同时打开的最大连接数，默认 `512`。注意它统计的是**所有**连接，包含与上游服务器的连接，不只是客户端连接。理论上限约为 `worker_processes × worker_connections`，但实际还受系统"最大打开文件数"限制，可用 `worker_rlimit_nofile` 提高。
3. **CPU 亲和性**：`worker_cpu_affinity auto;`（1.9.10 起，仅 Linux / FreeBSD）把工作进程绑定到不同 CPU，减少核间迁移。
4. **事件模型**：一般不需要显式指定 `use`，Nginx 会自动选最有效的方法；确需固定时再写 `use epoll;`。

```nginx
worker_processes auto;          # 通常等于 CPU 核心数
worker_rlimit_nofile 65535;     # 提高单进程可打开文件数上限

events {
    worker_connections 10240;   # 单 worker 连接上限，含与上游的连接
    multi_accept on;
}

thread_pool my_pool threads=16 max_queue=65536;

http {
    # 在需要的 location 中启用：aio threads=my_pool;
    server {
        listen 80;
        location /video/ {
            root /data;
            sendfile on;
            aio threads=my_pool;
        }
    }
}
```

调整顺序建议：先确认 `worker_processes` 与核心数匹配，再看 `worker_connections × worker_processes` 是否覆盖预期并发，最后用 `worker_rlimit_nofile` 与系统 `ulimit -n` 打通文件句柄上限。压测数据比任何"经验倍数"都可靠。

## 四、连接管理：长连接、短连接与 keep-alive

本节讲 HTTP 连接的生命周期管理。它直接影响延迟和服务器可承载的连接数，也是排查"连接数打满"类问题的前置知识。

**长连接（持久连接）**：一条 TCP 连接上连续发送多个 HTTP 请求/响应，用完先不关，等超时或显式关闭。省掉了反复三次握手与慢启动的开销。

**短连接**：每个请求都新建一条 TCP 连接，响应后立即关闭。实现简单、彼此隔离，但开销大。

| 维度 | 长连接 | 短连接 |
| --- | --- | --- |
| 建连次数 | 一次连接多次复用 | 每请求一次 |
| 延迟 | 低（省握手） | 高 |
| 服务器连接数 | 空闲连接也占资源 | 峰值过后立即释放 |
| 适用 | 页面加载、API 调用、代理转发 | 低频、需强隔离的调用 |

Nginx 侧的管理参数：

| 指令 | 默认值 | 说明 |
| --- | --- | --- |
| `keepalive_timeout` | `75s` | 客户端长连接在服务端保持空闲的时间；设为 `0` 关闭长连接。可写第二个参数，用于生成 `Keep-Alive: timeout=` 响应头 |
| `keepalive_requests` | `1000` | 单条长连接最多处理多少个请求（1.19.10 之前默认 `100`） |
| `keepalive_time` | `1h` | 单条长连接的最长存活时间（1.19.10 起） |

与上游（后端 Java 服务）之间也可以复用连接，配置在 `upstream` 块里，需要配合 `proxy_http_version 1.1` 并清空 `Connection` 头：

```nginx
upstream backend {
    server 127.0.0.1:8080;
    keepalive 64;              # 每个 worker 缓存的空闲长连接数
    keepalive_requests 1000;   # 单条连接最多服务多少请求（1.15.3 起）
    keepalive_timeout 60s;     # 空闲长连接保持时间（1.15.3 起）
}

server {
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

版本提示：`upstream` 中的 `keepalive` 在 1.29.7 起默认开启（每 worker 32 条），此前的版本必须显式写出；`proxy_http_version` 同样在 1.29.7 起默认为 `1.1`，更早版本默认是 `1.0`，所以老版本务必手写这两行。

若要主动使用短连接，可以在响应中返回 `Connection: close`，让客户端在本次响应后关闭连接。

## 五、静态文件：怎么发文件，怎么优化

静态资源（HTML、CSS、JS、图片、视频）通常占网站流量的绝大部分，而 Java 应用并不擅长直接吐文件。本节讲 Nginx 发文件的机制，以及常见的优化手段。

**处理机制：**

1. **零拷贝**：开启 `sendfile on;` 后，文件数据由内核直接从页缓存送入 socket，避免"内核 → 用户态 → 内核"的两次多余拷贝。默认 `sendfile` 是关闭的，静态站点一般建议打开。
2. **事件驱动**：一个工作进程可同时服务大量静态请求，不会被慢客户端拖住。
3. **内存缓存**：`open_file_cache` 可缓存文件描述符、大小、修改时间与查找结果（默认关闭），减少重复的 `open`/`stat` 系统调用。
4. **异步文件 I/O**：大文件场景可用 `aio threads;` 把读盘交给线程池，避免阻塞事件循环。

**优化手段：**

| 手段 | 作用 | 备注 |
| --- | --- | --- |
| `gzip on` | 压缩文本类资源 | 图片、视频本身已压缩，压缩无收益 |
| `expires` / `add_header` | 让浏览器长期缓存，减少重复下载 | 静态资源常配 `1y` + 文件名带哈希 |
| CDN | 就近分发，减轻源站压力 | 跨地域访问收益明显 |
| 合并文件 / 雪碧图 | 减少请求数 | HTTP/2 多路复用后收益下降，是否合并需实测 |
| 现代格式 | 同画质下体积更小（如 WebP、AVIF） | 注意浏览器兼容与降级 |
| 对象存储 | 静态资源放分布式存储/CDN 源 | 便于扩容与异地容灾 |

```nginx
server {
    listen 80;
    server_name static.example.com;

    root /data/www;
    sendfile on;
    tcp_nopush on;          # 与 sendfile 配合，减少小包
    open_file_cache max=10000 inactive=60s;
    open_file_cache_valid 30s;

    location ~* \.(?:css|js|png|jpg|jpeg|gif|webp|svg|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
        access_log off;
    }

    location ~* \.(?:html|json)$ {
        expires 5m;         # 入口文件短缓存，便于发版
    }
}
```

## 六、缓存：代理缓存与浏览器缓存

缓存是把"算过的结果"存起来，下次直接给。对 Java 应用而言，Nginx 缓存能挡掉大量重复回源请求，是最省成本的性能优化之一。

冰箱里备好常做的菜：客人点单时直接加热上桌，不必每次现买菜现做——Nginx 的代理缓存就是这个冰箱，`proxy_cache_path` 是冰箱的容积与位置，`proxy_cache_valid` 是保质期。

**服务端代理缓存（`ngx_http_proxy_module`）：**

| 指令 | 作用 | 关键点 |
| --- | --- | --- |
| `proxy_cache_path` | 定义缓存目录与共享内存区 | 只能在 `http` 块使用；`keys_zone` 为必填参数 |
| `proxy_cache` | 在 `location` 中启用某个缓存区 | 值要与 `keys_zone` 的名字一致 |
| `proxy_cache_valid` | 按响应码设置缓存时长 | 只写时长（如 `5m`）时仅缓存 200/301/302 |
| `proxy_cache_key` | 缓存键 | 默认 `$scheme$proxy_host$request_uri` |
| `proxy_cache_min_uses` | 请求多少次后才缓存 | 默认 `1` |
| `proxy_cache_use_stale` | 回源出错时是否用过期缓存兜底 | 默认 `off` |
| `proxy_cache_revalidate` | 过期后是否用条件请求回源校验 | 默认 `off`（1.5.7 起） |
| `proxy_cache_bypass` | 满足条件时绕过缓存 | 常用于后台强制刷新 |
| `proxy_cache_lock` | 同一缓存键只允许一个请求回源 | 默认 `off`，可防缓存击穿 |

`proxy_cache_path` 中 `inactive`（默认 10 分钟）指"多久没被访问就清理"，即使内容还没过期；`max_size` 限制磁盘占用，超出后按最近最少使用淘汰。

```nginx
http {
    proxy_cache_path /data/nginx/cache
                     levels=1:2
                     keys_zone=api_cache:10m
                     max_size=10g
                     inactive=30m;

    server {
        location /api/ {
            proxy_pass http://backend;
            proxy_cache api_cache;
            proxy_cache_key "$scheme$host$request_uri";
            proxy_cache_valid 200 302 10m;
            proxy_cache_valid 404 1m;
            proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
            proxy_cache_lock on;
            add_header X-Cache-Status $upstream_cache_status;
        }
    }
}
```

`$upstream_cache_status` 能直接告诉你缓存是否命中，取值有 `MISS`、`HIT`、`BYPASS`、`EXPIRED`、`STALE`、`UPDATING`、`REVALIDATED`。排查"缓存为什么没生效"时先看这个头。

**其它缓存形态：**

- **FastCGI 缓存**：`fastcgi_cache` + `fastcgi_cache_path`，用于 PHP 一类 FastCGI 后端。
- **静态资源缓存**：`expires`、`add_header` 设置 `Cache-Control` / `Expires`，让浏览器端缓存，减轻服务端压力。注意 `add_header` 默认只在部分响应码（200、201、204、206、301、302、303、304、307、308）上生效，需要覆盖全部响应时加 `always`。
- **内存缓存区**：`keys_zone` 指定的共享内存只存键与元数据，不存响应体；给足 `keys_zone` 能提升命中判断速度。

缓存策略要按业务来：登录态相关、强一致要求的接口不适合长时间缓存；而列表页、详情页、静态接口通常是缓存收益最高的地方。

## 七、反向代理与正向代理的区别

两者都是"代理"，区别在于**代理的是谁**、以及**谁不知道谁的存在**。理解这一点，才能说清 Nginx 在架构里的位置。

**正向代理**：代理客户端。客户端明确配置了代理地址，请求先发给代理，由代理代客户端去访问目标站点。目标服务器只看到代理的 IP，不知道真实客户端。

**反向代理**：代理服务器。客户端以为自己在访问网站本身，实际上请求先到 Nginx，再由 Nginx 按规则转发给后端的一台或多台服务器。客户端不知道后端的存在。

| 维度 | 正向代理 | 反向代理 |
| --- | --- | --- |
| 服务对象 | 客户端 | 服务端 |
| 部署位置 | 靠近客户端（公司出口、代理软件） | 靠近服务端（机房入口） |
| 客户端是否知情 | 知情，需显式配置 | 通常不知情 |
| 主要用途 | 突破访问限制、隐藏客户端 IP、上网行为审计 | 负载均衡、缓存、TLS 终止、安全控制 |
| 典型例子 | 公司统一出口代理 | Nginx → 多台 Spring Boot |

反向代理转发时，后端默认只能看到 Nginx 的地址，因此通常要显式传几个头，让 Java 应用能拿到真实客户端信息：

```nginx
location /api/ {
    proxy_pass http://backend;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

如果应用里用 `request.getRemoteAddr()` 取客户端 IP，需要框架侧配合解析 `X-Forwarded-For`（例如 Spring Boot 的 `server.forward-headers-strategy`），否则拿到的永远是 Nginx 的地址。

## 八、负载均衡：算法与 upstream 参数

当后端从一台变成多台，就需要一个"分派规则"。本节讲 Nginx 支持的负载均衡算法、`upstream` 里 `server` 的常用参数，以及怎么组合使用。

`upstream` 块定义一组后端服务器，默认使用**加权轮询**（weighted round-robin）：按权重比例依次分发。权重为 5、1、1 的三台服务器，每 7 个请求中第一台拿 5 个。

| 算法 | 指令 | 行为 | 适用 |
| --- | --- | --- | --- |
| 加权轮询 | 默认，无需指令 | 按权重轮流分发 | 后端性能相近的无状态服务 |
| 最少连接 | `least_conn;` | 优先给当前活跃连接最少的服务器（计入权重） | 请求耗时差异大 |
| IP 哈希 | `ip_hash;` | 按客户端 IP 计算哈希（IPv4 取前三段），同一客户端固定到同一台 | 简易会话保持 |
| 自定义哈希 | `hash $key [consistent];` | 按指定键哈希，加 `consistent` 用一致性哈希 | 缓存服务器分片 |
| 随机 | `random [two [least_conn]];` | 随机选，`two` 表示随机取两台再择优（1.15.1 起） | 大规模集群 |
| 最少时间 | `least_time ...;` | 按平均响应时间与活跃连接数选择 | 长期属于商业版能力，官方文档标注 1.31.0 起开源版可用，使用前请核对版本 |

`upstream` 中 `server` 的常用参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `weight=N` | `1` | 权重，越大分到的请求越多 |
| `max_conns=N` | `0`（不限） | 到该后端的最大并发连接数（1.11.5 起） |
| `max_fails=N` | `1` | 在 `fail_timeout` 时间内失败多少次即判定不可用 |
| `fail_timeout=T` | `10s` | 失败统计窗口，同时是判定不可用后的摘除时长 |
| `backup` | — | 备用机，主服务器全部不可用时才接流量 |
| `down` | — | 手动标记下线，配合 `ip_hash` 可保持哈希稳定 |
| `resolve` | — | 动态解析域名并自动更新地址，需配合 `resolver` |
| `slow_start=T` | — | 商业版参数，恢复时权重渐进上升 |

注意：开源版默认是**被动健康检查**——靠真实请求的失败次数（`max_fails`/`fail_timeout`）判断后端好坏；主动健康检查（`health_check`）属于商业版模块。若组内只有一台服务器，`max_fails`、`fail_timeout` 会被忽略，它永远不会被判为不可用。

```nginx
upstream backend {
    least_conn;
    server 10.0.0.11:8080 weight=3 max_fails=2 fail_timeout=10s;
    server 10.0.0.12:8080 weight=1 max_fails=2 fail_timeout=10s;
    server 10.0.0.13:8080 backup;
    keepalive 64;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://backend;
        proxy_next_upstream error timeout http_502 http_503;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

`proxy_next_upstream` 决定"什么情况下换下一台重试"，默认已包含 `error` 与 `timeout`；把它配得过于激进（例如把 `http_500` 也算失败）可能导致非幂等请求被重复提交，需要结合业务判断。

## 九、location 匹配与 rewrite 规则

`location` 决定"这个 URL 交给哪段配置处理"，`rewrite` 决定"URL 要不要改写、要不要跳转"。两者是 Nginx 配置里最容易写错、也最常被追问的部分。

### 9.1 location 的匹配优先级

匹配流程可以记成四步：

1. 先在所有**前缀** location 中找最长匹配，并记下来；
2. 如果这个最长前缀带 `^~` 修饰符，直接用它的配置，不再检查正则；
3. 否则按**配置文件中的出现顺序**逐个尝试正则 location，第一个匹配上的立即生效；
4. 正则都没匹配上，就用第 1 步记下的最长前缀 location。

`=` 是精确匹配，一旦命中立即结束查找，所以高频路径（如 `location = /`）用它可以省掉后续比较。

| 修饰符 | 含义 | 是否继续检查正则 |
| --- | --- | --- |
| `=` | URI 完全相等 | 否，命中即结束 |
| `^~` | 前缀匹配，且命中后跳过正则 | 否 |
| 无 | 普通前缀匹配，取最长 | 是 |
| `~` | 区分大小写的正则 | 按顺序 |
| `~*` | 不区分大小写的正则 | 按顺序 |
| `@name` | 命名 location，只用于内部跳转（如 `try_files`、`error_page`） | 不参与普通匹配 |

```nginx
server {
    location = / {                 # 1. 只匹配 "/"
        return 200 "home\n";
    }

    location / {                   # 2. 兜底前缀
        proxy_pass http://backend;
    }

    location ^~ /images/ {         # 3. 命中后不再看正则
        root /data;
    }

    location ~* \.(gif|jpg|jpeg|png)$ {   # 4. 正则按出现顺序
        expires 30d;
    }

    location @fallback {           # 5. 命名 location
        proxy_pass http://backend;
    }
}
```

实践提示：把正则 location 写在前面并不会"优先"，优先级由类型决定，只有同类正则之间才比较出现顺序。这条规则与很多人的直觉相反，是排查"配置没生效"的高频原因。

### 9.2 rewrite 与 return

`rewrite 正则 替换串 [flag];` 的语义是：请求 URI 匹配正则时，按替换串改写。指令按配置中出现的顺序依次执行，直到被 flag 打断。

| flag | 效果 |
| --- | --- |
| 无 | 继续执行后续 rewrite，然后按改写后的 URI 继续处理 |
| `last` | 停止当前这组 rewrite，用新 URI 重新做一次 location 查找 |
| `break` | 停止当前这组 rewrite，留在当前 location 继续处理 |
| `redirect` | 返回 302 临时重定向（替换串不是以协议或 `$scheme` 开头的绝对地址时，默认使用该标志） |
| `permanent` | 返回 301 永久重定向 |

补充两点官方语义：如果替换串本身以协议开头，处理会直接停止并返回重定向；`rewrite` 只能写在 `server`、`location`、`if` 中。

```nginx
server {
    # 老接口迁移到新路径，内部跳转，不改变浏览器地址
    rewrite ^/old-api/(.*)$ /api/v2/$1 last;

    # 强制 https（注意返回的是重定向）
    if ($scheme = http) {
        return 301 https://$host$request_uri;
    }

    # 更简单的做法：直接 return，避免不必要的正则开销
    location = /health {
        return 200 "ok\n";
    }

    # 单页应用的前端路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

`if` 在 `location` 中的行为有诸多限制（官方文档也提示其语义容易出错），能用 `map`、`try_files`、`return` 表达的，尽量不要用 `if`。

## 十、HTTP 压缩：gzip 的正确配置

压缩能直接减少传输字节数，对文本类响应（HTML、CSS、JS、JSON）收益明显。Gzip 是最通用的压缩方式，浏览器普遍支持。

| 指令 | 默认值 | 说明 |
| --- | --- | --- |
| `gzip` | `off` | 总开关，默认关闭 |
| `gzip_types` | `text/html` | 除 `text/html` 外还需要压缩的 MIME 类型；`text/html` 始终会被压缩 |
| `gzip_comp_level` | `1` | 压缩级别 1~9，越高越费 CPU |
| `gzip_min_length` | `20` | 小于该字节数的响应不压缩（依据 `Content-Length` 判断） |
| `gzip_buffers` | `32 4k\|16 8k` | 压缩使用的缓冲块数量与大小 |
| `gzip_http_version` | `1.1` | 允许压缩的最低 HTTP 版本 |
| `gzip_proxied` | `off` | 对代理请求是否压缩（依据请求中的 `Via` 头判断） |
| `gzip_vary` | `off` | 是否添加 `Vary: Accept-Encoding` 响应头 |
| `gzip_disable` | — | 按 User-Agent 正则跳过压缩，如 `msie6` |
| `gzip_static` | `off` | 独立模块：优先发送预压缩的 `.gz` 文件，需编译时开启 |

```nginx
http {
    gzip on;
    gzip_types text/plain text/css application/javascript application/json
               application/xml application/xhtml+xml image/svg+xml;
    gzip_comp_level 5;          # 1 最快，9 最小；5 左右是常见折中
    gzip_min_length 1024;       # 太小压缩反而得不偿失
    gzip_buffers 32 4k;
    gzip_http_version 1.1;
    gzip_proxied any;
    gzip_disable "msie6";
    gzip_vary on;               # 让缓存/CDN 区分压缩与非压缩版本
    gzip_static on;             # 需模块支持：直接发送预生成的 .gz
}
```

启用后，Nginx 会对符合条件的响应加上 `Content-Encoding: gzip`，由客户端负责解压。三个常见坑：

- **`gzip_static` 不是"是否添加 Content-Encoding 头"的开关**，它表示"存在同名 `.gz` 文件时优先发送该文件"，属于 `ngx_http_gzip_static_module`，默认未编译进 Nginx，需要 `--with-http_gzip_static_module`。
- **`gzip_http_version` 不是"压缩窗口大小"**，它只是"允许压缩的最低 HTTP 版本"。
- **HTTPS 下的压缩要谨慎**：官方文档明确指出，TLS 上压缩后的响应可能受到 BREACH 类攻击影响，涉及敏感信息（如 CSRF token、会话标识）的响应不宜压缩。

## 十一、HTTP/2 与 HTTP/3

HTTP/2 是 HTTP/1.1 的继任者，目标是降低延迟、提升并发效率。Nginx 从 1.9.5 起提供支持，但需要模块被编译进来。

主要特性：

| 特性 | 说明 | 解决的问题 |
| --- | --- | --- |
| 多路复用 | 一条 TCP 连接上并发多个请求/响应流 | HTTP/1.1 的队头阻塞 |
| 头部压缩 | HPACK 算法压缩请求/响应头 | 重复头部带来的带宽浪费 |
| 二进制分帧 | 传输层改为二进制帧 | 文本解析的低效与歧义 |
| 流优先级 | 客户端可标注流的优先级 | 关键资源优先加载 |
| 服务器推送 | 服务端主动推送资源 | 减少一轮请求，但实际收益视场景而定，需测试评估 |

Nginx 侧的配置要点：

1. **版本与模块**：`ngx_http_v2_module` 自 1.9.5 起存在，默认不编译，需要 `--with-http_v2_module`。可用 `nginx -V` 确认编译参数。
2. **写法的变化**：1.25.1 起推荐使用独立的 `http2 on;` 指令；`listen 443 ssl http2;` 中的 `http2` 参数已被官方标记为**弃用**（deprecated）。一些较老的示例仍写作 `listen 443 ssl http2;`，这里按新版写法更正。
3. **TLS 要求**：通过 TLS 承载 HTTP/2 需要 ALPN 扩展，OpenSSL 需 1.0.2 及以上。HTTP/2 也可以跑在明文上，但浏览器普遍只在 HTTPS 下启用。
4. **HTTP/3**：基于 QUIC（UDP），Nginx 1.25.0 起在 `listen` 中提供 `quic` 参数。

```nginx
server {
    listen 443 ssl;
    http2 on;                    # 1.25.1+ 推荐写法
    server_name example.com;

    ssl_certificate     /etc/nginx/ssl/example.com.crt;
    ssl_certificate_key /etc/nginx/ssl/example.com.key;

    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_session_cache   shared:SSL:10m;

    location / {
        proxy_pass http://backend;
    }
}
```

HTTP/2 下的优化思路与 HTTP/1.1 不同：请求数不再是最主要的瓶颈，域名分片、资源合并的收益明显下降，重点转向减小单个资源体积、合理设置缓存与优先级。上线前仍需做兼容性与压测，尤其是老客户端与中间设备。

## 十二、WebSocket 代理

WebSocket 是在一条 TCP 连接上做全双工通信的协议，适合聊天、实时推送、协同编辑等场景。它先用 HTTP/1.1 完成握手，再"升级"为长连接。

把 HTTP 想象成寄信（一问一答，写完就结束），WebSocket 更像对讲机（按住频道后双方随时可以说话）。也正因为它是长连接，代理层必须保证连接不被中途掐断。

Nginx 从 1.3.13 起支持 WebSocket 代理：当后端返回 `101 Switching Protocols`、且客户端请求带 `Upgrade` 头时，Nginx 会在客户端与后端之间建立隧道。关键在于 `Upgrade` 与 `Connection` 属于**逐跳头（hop-by-hop）**，默认不会转发，必须显式透传。

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;                              # 1.29.7 起默认即为 1.1
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        proxy_read_timeout 3600s;   # 长连接场景需放宽读超时，默认 60s 容易被动断开
        proxy_send_timeout 3600s;
    }
}
```

配套注意点：

- 后端（如 Spring 的 WebSocket/STOMP 端点）要正确处理握手与数据帧，否则 Nginx 侧配置正确也会失败。
- 多实例部署时需要会话粘性（`ip_hash` 或基于 Cookie 的粘性策略），否则同一客户端的帧会落到不同实例。
- 如果前面还有负载均衡设备或 CDN，同样需要允许 WebSocket 升级，并把空闲超时调大。
- `proxy_read_timeout` 只统计"两次读操作之间"的间隔，不是整个连接的总时长，因此长连接把间隔放宽即可。

## 十三、IP 访问控制：allow / deny

`ngx_http_access_module` 提供最基础的网络层访问控制，适合给后台管理口、内部接口加一道门。

规则按配置中出现的顺序逐条检查，**命中第一条即生效**，后面的规则不再看。这也是"顺序写反会得到相反结果"的根因。

```nginx
server {
    location /admin/ {
        allow 192.168.1.100;     # 单个地址
        allow 10.0.0.0/24;       # 网段（CIDR）
        allow 2001:db8::/32;     # IPv6 网段
        deny  all;               # 其余全部拒绝

        proxy_pass http://backend;
    }
}
```

规则可以写在 `http`、`server`、`location` 任一层，内层会覆盖外层同类型判断。几条实践经验：

- `deny all;` 放在最后，否则前面的 `allow` 永远不会被检查到。
- 反向代理场景下，`deny` 比较的是 `$remote_addr`。如果 Nginx 前面还有一层代理或 CDN，需要用 `real_ip` 相关指令还原真实客户端地址，否则限制的是上一跳的 IP。
- 需要按国家/地区或大段地址做规则时，可以用 `geo` 模块把 IP 映射成变量，再配合 `if` 或 `map` 使用；按国家判断通常还需要 GeoIP 类模块。

## 十四、限流、防爬虫与 DDoS 缓解

访问控制只能挡"已知的坏 IP"，而刷接口、爬虫、DDoS 的共同特征是"量大"。本节讲 Nginx 能做的限速与拦截，以及它的能力边界。

**请求速率限制**（`ngx_http_limit_req_module`）：按 key（通常是客户端 IP）用一个漏桶算法限速。

```nginx
http {
    # 每个 IP 平均 5 请求/秒，状态存 10MB 共享内存
    limit_req_zone $binary_remote_addr zone=perip:10m rate=5r/s;

    server {
        location /api/ {
            limit_req zone=perip burst=10 nodelay;
            limit_req_status 429;
            proxy_pass http://backend;
        }
    }
}
```

- `rate` 支持 `r/s` 与 `r/m`；`$binary_remote_addr` 比 `$remote_addr` 更省内存。
- `burst` 允许的突发请求数，默认 `0`；超出的请求默认被延迟处理，加了 `nodelay` 则直接拒绝（返回 `limit_req_status` 指定的状态码）。

**并发连接限制**（`ngx_http_limit_conn_module`）：

```nginx
http {
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    server {
        location /download/ {
            limit_conn addr 1;        # 每个 IP 同时只允许 1 条连接
            limit_conn_status 429;
        }
    }
}
```

注意：在 HTTP/2、HTTP/3 下，每个并发请求会被当作一条独立连接计数，与 HTTP/1.1 的直觉不同。

**防爬虫与恶意请求的常用模块：**

| 模块 / 指令 | 作用 |
| --- | --- |
| `ngx_http_access_module`（`allow`/`deny`） | 按 IP 或网段放行、拒绝 |
| `ngx_http_geo_module`（`geo`） | 把客户端 IP 映射为变量，便于做分组规则 |
| `ngx_http_limit_req_module` | 限制请求速率，压制高频抓取 |
| `ngx_http_limit_conn_module` | 限制并发连接数 |
| `ngx_http_referer_module`（`valid_referers`、`$invalid_referer`） | 防盗链，只允许来自指定来源页的请求 |
| `ngx_http_rewrite_module` | 按 UA、参数等条件做重定向或直接拒绝 |
| `ngx_http_headers_module`（`add_header`） | 添加 `X-Frame-Options`、`Content-Security-Policy` 等安全响应头 |

这里需要澄清两处常见误解：官方文档的模块清单中**没有** `ngx_http_security_headers_module`，设置安全响应头应使用 `ngx_http_headers_module` 的 `add_header`；`ngx_http_bot_protection_module` 同样不是官方模块，识别恶意爬虫需要引入第三方模块、商业版能力或上游 WAF，不应假设它开箱可用。

**DDoS 缓解的现实边界：**

1. 限速与限连接（`limit_req`、`limit_conn`）能压住单 IP 的高频请求。
2. 缓存与代理缓冲能减少回源，让后端不被瞬间流量打穿；`proxy_request_buffering`、`client_body_buffer_size` 等参数影响大请求的处理方式。
3. IP 黑/白名单可拦截已知恶意来源。
4. 多实例 + 负载均衡可避免单点被打垮。
5. 与 CDN、云 WAF、清洗中心联动是应对大流量攻击的主要手段。
6. Nginx 自身也可能成为攻击目标（连接耗尽、慢速攻击），需要配合内核参数与上游防护。

结论要诚实：Nginx 是"缓解"手段，面对大规模流量型攻击，专业清洗服务与运营商侧防护才是主力。

## 十五、超时与缓冲区参数速查

超时和缓冲是最常被调整、也最容易调错的参数。本节给出一张默认值速查表，并澄清一个常被混淆的概念——"缓冲区溢出"。

| 指令 | 默认值 | 作用与超时后的结果 |
| --- | --- | --- |
| `client_header_timeout` | `60s` | 读请求头超时 → 408 |
| `client_body_timeout` | `60s` | 两次读请求体之间超时 → 408 |
| `send_timeout` | `60s` | 两次写响应之间超时 → 关闭连接 |
| `keepalive_timeout` | `75s` | 客户端空闲长连接保持时间，`0` 为关闭 |
| `keepalive_requests` | `1000` | 单条长连接可处理的请求数上限 |
| `client_max_body_size` | `1m` | 请求体上限，超出 → 413 |
| `client_header_buffer_size` | `1k` | 请求头缓冲 |
| `large_client_header_buffers` | `4 8k` | 请求头超长时使用的更大缓冲 |
| `client_body_buffer_size` | `8k\|16k` | 请求体缓冲，超出部分落临时文件 |
| `proxy_connect_timeout` | `60s` | 与上游建连超时（官方提示通常不超过 75 秒） |
| `proxy_read_timeout` | `60s` | 两次读上游响应之间超时 → 504 |
| `proxy_send_timeout` | `60s` | 两次写上游请求之间超时 |
| `proxy_buffering` | `on` | 是否缓冲上游响应 |
| `proxy_buffer_size` | `4k\|8k` | 上游响应头缓冲，超出视为响应非法 |
| `proxy_buffers` | `8 4k\|8k` | 上游响应体缓冲块数量与大小 |
| `worker_connections` | `512` | 单 worker 最大连接数（含上游连接） |

调参经验（属实践总结，非官方承诺）：上传接口要把 `client_max_body_size` 与 `client_body_buffer_size` 一起放大；大响应后端要评估 `proxy_buffers` 与 `proxy_max_temp_file_size`；慢接口优先看 `proxy_read_timeout`，不要盲目全局放大，否则故障会被拖得更久。

关于内存：这些缓冲是按连接分配的，数值调大只是推高"并发连接数 × 缓冲大小"的内存占用，并不会让吞吐变高；按真实请求/响应体大小设置即可，并给系统预留足够内存给连接状态与临时文件。

### 进阶了解（可跳过）

初学阶段可以略过这一小节，知道"两者不是一回事"即可。

一种常见误解是把"缓冲区溢出"当成 Nginx 要防的攻击类型，实际上是两个层面的问题：

- **缓冲区溢出**是 C 程序把数据写到缓冲区边界之外，覆盖相邻内存，属于内存安全漏洞。它的防护依赖编译器与操作系统机制，例如栈保护（stack canary）、地址空间布局随机化（ASLR）、不可执行栈等，并不是"写代码时用到的某种技巧"。
- **Nginx 的缓冲区参数**（`client_body_buffer_size`、`proxy_buffers` 等）是应用层的收发缓冲，影响内存占用与是否落盘，与内存安全漏洞无关。
- Nginx 自身也会有安全公告（CVE），实践做法是关注官方安全公告、及时升级版本、最小化编译模块，而不是依赖单个参数。

## 十六、用 Lua 扩展请求处理（OpenResty）

有些逻辑用声明式配置表达很别扭，例如"先查缓存、再校验签名、最后改写响应体"。这类场景可以用 Lua 脚本嵌入请求处理流程。

把它想成在流水线上临时加一个可编程工位：请求经过某个阶段时，交给你的 Lua 代码处理，处理完再继续往下走。

**先明确归属**：Lua 能力来自第三方模块 `lua-nginx-module`，不属于 Nginx 官方源码；OpenResty 是把 Nginx 与该模块（以及一系列常用库）打包在一起的发行版，生产上通常直接使用 OpenResty 而不是自己编译。

常见的用途：

1. **请求处理**：改写请求头、查询参数、请求体。
2. **响应处理**：修改响应体与响应头。
3. **访问控制**：基于复杂条件（签名、Token、灰度规则）放行或拒绝。
4. **缓存控制**：实现自定义的缓存键与失效逻辑。
5. **复杂重定向**：按多条件组合决定跳转目标。

接入步骤：

1. 准备支持 Lua 的 Nginx（OpenResty，或自行编译并加载该模块）。
2. 用 `lua_package_path` / `lua_package_cpath` 指定 Lua 代码与 C 模块的搜索路径。
3. 在 `location` 中用阶段指令挂载脚本：`access_by_lua_file`（访问阶段，适合鉴权）、`content_by_lua_file`（内容阶段，直接生成响应）。
4. 脚本中用 `ngx.var`、`ngx.req`、`ngx.say` 等 API 读写请求与响应。

```nginx
http {
    lua_package_path  "/etc/nginx/lua/?.lua;;";
    lua_package_cpath "/etc/nginx/lua/?.so;;";

    server {
        location /api/ {
            access_by_lua_file /etc/nginx/lua/auth.lua;   # 鉴权通过后继续代理
            proxy_pass http://backend;
        }

        location /hello {
            content_by_lua_file /etc/nginx/lua/hello.lua; # 直接返回内容，不走后端
        }
    }
}
```

关于加载方式需要说明一点：`lua-nginx-module` 并没有 `lua_include` 指令，复用代码的标准做法是把公共逻辑写成 Lua 模块，在脚本里用 `require` 引入，并保证模块所在目录已加入 `lua_package_path`。

性能提醒：Lua 代码运行在工作进程的事件循环里，任何阻塞操作（同步 IO、长时间循环）都会拖慢该进程上的所有请求。官方文档也反复强调要避免阻塞型调用；上线前应做压测，并注意脚本异常的处理路径。

## 十七、常用运维命令与排错

前面各节讲的是"怎么配"，这一节讲"配完之后怎么确认它生效、出问题怎么定位"。

```bash
nginx -v                 # 版本
nginx -V                 # 版本 + 编译参数（确认模块是否编进来）
nginx -t                 # 校验配置语法
nginx -T                 # 打印完整生效配置（含 include 展开）
nginx -s reload          # 平滑重载
nginx -s quit            # 优雅退出
nginx -s stop            # 立即停止
```

状态码与常见原因对照：

| 现象 | 常见原因 | 排查方向 |
| --- | --- | --- |
| 502 Bad Gateway | 后端不可达、后端提前断连、上游返回非法响应 | 后端端口/进程、`error.log`、`proxy_read_timeout` |
| 504 Gateway Time-out | 后端处理超过 `proxy_read_timeout` | 后端耗时、慢 SQL、超时是否需单独放大 |
| 413 Request Entity Too Large | 请求体超过 `client_max_body_size` | 上传接口单独放大该值 |
| 499（Nginx 自定义） | 客户端在响应前主动断开 | 客户端超时设置、后端响应过慢 |
| 429 Too Many Requests | 触发 `limit_req` / `limit_conn` | 调整 `rate`、`burst` 或换 key |
| 静态资源 404 | `root` / `alias` 路径写错 | `nginx -T` 看生效路径；注意 `alias` 与 `location` 的斜杠 |

排错时的顺序建议：先用 `nginx -T` 确认"你以为生效的配置"确实生效；再看 `error.log` 的具体报错；最后对照上游服务的日志确认问题在代理层还是应用层。

## 参考资料

- NGINX 官方文档：Core functionality（`worker_processes`、`worker_connections`、`thread_pool`、`worker_cpu_affinity` 等指令与默认值）
- NGINX 官方文档：Module ngx_http_core_module（`location` 匹配规则、`keepalive_timeout`、`client_*` 系列、`listen` 参数）
- NGINX 官方文档：Module ngx_http_upstream_module（负载均衡算法、`server` 参数、`keepalive` 系列）
- NGINX 官方文档：Module ngx_http_proxy_module（`proxy_*` 超时、缓冲、缓存指令）
- NGINX 官方文档：Module ngx_http_gzip_module 与 ngx_http_gzip_static_module
- NGINX 官方文档：Module ngx_http_v2_module；WebSocket proxying 专题页
- NGINX 官方文档：Module ngx_http_access_module、ngx_http_limit_req_module、ngx_http_limit_conn_module、ngx_http_geo_module、ngx_http_referer_module、ngx_http_rewrite_module、ngx_http_headers_module
- OpenResty 项目文档：lua-nginx-module（`lua_package_path`、`access_by_lua_file`、`content_by_lua_file` 等）
