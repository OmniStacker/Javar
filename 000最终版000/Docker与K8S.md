# Docker与Kubernetes知识汇总

## 目录

1. [Docker基础](#1-docker基础)
2. [Kubernetes概述](#2-kubernetes概述)
3. [Kubernetes核心组件](#3-kubernetes核心组件)
4. [Kubernetes基本概念](#4-kubernetes基本概念)
5. [Kubernetes工作资源对象](#5-kubernetes工作资源对象)
6. [Docker与Kubernetes对比](#6-docker与kubernetes对比)
7. [常用操作与命令](#7-常用操作与命令)
8. [部署策略](#8-部署策略)

---

## 1. Docker基础

### 1.1 什么是Docker

Docker是一个开源的容器化平台，可以将应用程序及其依赖打包到一个可移植的容器中，实现"一次构建，到处运行"。

### 1.2 Docker核心概念

**镜像（Image）**：
- 镜像是一个只读的模板，包含了运行应用程序所需的所有内容
- 包括代码、运行时、库、环境变量和配置文件
- 镜像是容器的基础

**容器（Container）**：
- 容器是镜像的运行实例
- 每个容器都是隔离的、轻量级的进程
- 容器之间相互独立，共享主机操作系统内核

**仓库（Repository）**：
- 仓库用于存储和分发Docker镜像
- 分为公共仓库（如Docker Hub）和私有仓库

### 1.3 Docker安装与配置

**安装Docker**：
```bash
yum -y install docker
```

**启动Docker**：
```bash
systemctl start docker
systemctl enable docker  # 设置开机自启
```

**配置镜像加速**：
```json
{
  "registry-mirrors": [
    "https://registry.docker-cn.com",
    "http://hub-mirror.c.163.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

### 1.4 Docker常用命令

```bash
# 镜像操作
docker pull 镜像名           # 拉取镜像
docker images               # 查看本地镜像
docker rmi 镜像ID           # 删除镜像
docker search 镜像名        # 搜索镜像

# 容器操作
docker run -it 镜像名 /bin/bash   # 启动容器
docker run -p 宿主机端口:容器端口 -d --name 容器名 镜像名  # 启动容器并映射端口
docker ps                   # 查看运行中的容器
docker ps -a                # 查看所有容器
docker stop 容器ID          # 停止容器
docker start 容器ID         # 启动容器
docker restart 容器ID       # 重启容器
docker rm 容器ID            # 删除容器
docker logs -f 容器名       # 查看容器日志
docker exec -it 容器ID /bin/bash  # 进入容器

# 其他
docker stats -a             # 查看容器资源使用情况
docker save 镜像名 > 文件名.tar   # 导出镜像
docker load -i 文件名.tar     # 导入镜像
```

---

## 2. Kubernetes概述

### 2.1 什么是Kubernetes

Kubernetes（简称K8s）是一个开源的容器编排系统，用于自动化应用程序容器的部署、扩展和管理。

**K8s源自Google 15年生产环境的运维经验，同时凝聚了社区的最佳创意和实践。**

### 2.2 K8s解决的问题

K8s在基于容器部署的方式上，提供了一个弹性分布式的框架，支持：

- **服务发现与负载均衡**
- **存储管理**
- **自动部署回滚**
- **自动计算与调度**
- **自动扩缩容**
- **故障恢复和自我修复**

**K8s解放了开发者的双手，能够最大程度的让部署的服务健康运行。**

### 2.3 K8s工作原理

一个Kubernetes集群主要由**控制节点Master**和**工作节点Node**构成。

---

## 3. Kubernetes核心组件

### 3.1 Master节点组件

Master节点是集群的控制平面，负责集群的决策（管理），包含四个重要组件：

1. **API Server**
   - 资源操作的唯一入口
   - 接收用户输入的命令
   - 提供认证、授权、API注册和发现等机制

2. **Scheduler**
   - 负责集群资源调度
   - 按照预定的调度策略将Pod调度到相应的Node节点上

3. **Controller Manager**
   - 负责维护集群的状态
   - 如程序部署安排、故障检测、自动扩展、滚动更新等

4. **Etcd**
   - 负责存储集群中各种资源对象的信息
   - 相当于K8s的数据库

### 3.2 Node节点组件

Node节点是集群的数据平面，负责为容器提供运行环境（干活），包含三个重要组件：

1. **Kubelet**
   - 负责维护容器的生命周期
   - 通过控制Docker来创建、更新、销毁容器
   - 定期向API Server汇报Node的状态

2. **KubeProxy**
   - 负责提供集群内部的服务发现和负载均衡

3. **Docker**
   - 负责节点上容器的各种操作

---

## 4. Kubernetes基本概念

### 4.1 节点（Node）

节点是运行应用程序容器的计算实例。每个节点都运行Kubelet和Docker引擎，并由Master节点进行管理和协调。

### 4.2 Pod

Pod是Kubernetes的基本单位，包含一个或多个相关的容器。

**Pod特点**：
- 是最小调度单元
- Pod里面会包含一个或多个容器（Container）
- Pod内的容器共享存储及网络，可通过localhost通信
- 这些容器在同一个Node上运行，共享相同的网络命名空间、IP地址和端口

### 4.3 Service

Service是一个抽象层，定义了Pod的逻辑集合，并提供了访问它们的策略（如IP地址和端口）。

**Service作用**：
- 服务发现
- 负载均衡
- 稳定的网络入口

### 4.4 Labels和Selectors

Labels（标签）是附加到对象（如Pod）上的键值对。

Selectors（选择器）用于筛选具有特定标签的对象。

**作用**：
- 标识和组织对象
- 用于Service和Pod的关联

---

## 5. Kubernetes工作资源对象

### 5.1 Deployment

- 用于管理无状态应用
- 支持滚动更新、回滚、扩缩容
- 最常用的工作负载资源

### 5.2 StatefulSet

- 用于管理有状态应用
- 为每个Pod提供稳定的网络标识和持久化存储
- 适用于数据库、消息队列等

### 5.3 DaemonSet

- 确保所有（或部分）Node上运行一个Pod副本
- 适用于日志收集、监控等场景

### 5.4 区别对比

| 资源类型 | 适用场景 | Pod特性 |
|---------|---------|---------|
| Deployment | 无状态应用 | 可替换、可水平扩展 |
| StatefulSet | 有状态应用 | 有固定标识、有序部署 |
| DaemonSet | 节点守护进程 | 每个节点一个副本 |

---

## 6. Docker与Kubernetes对比

### 6.1 Docker和Kubernetes的区别

| 维度 | Docker | Kubernetes |
|------|--------|------------|
| **定位** | 容器运行时 | 容器编排平台 |
| **功能** | 单机容器管理 | 集群容器管理 |
| **网络** | 单机网络 | 跨节点网络 |
| **存储** | 本地存储 | 分布式存储 |
| **调度** | 无 | 自动调度 |
| **扩缩容** | 手动 | 自动 |

### 6.2 Docker和Kubernetes的作用

**Docker**：
- 提供容器化能力
- 将应用程序打包成镜像
- 运行和管理单个容器

**Kubernetes**：
- 编排和管理多个容器
- 提供集群级别的管理能力
- 实现高可用、自动扩缩容

### 6.3 Docker和LXC的区别

| 维度 | Docker | LXC |
|------|--------|-----|
| **定位** | 应用容器 | 系统容器 |
| **粒度** | 应用级别 | 系统级别 |
| **便携性** | 高 | 低 |
| **启动速度** | 快 | 较慢 |
| **资源占用** | 低 | 较高 |

---

## 7. 常用操作与命令

### 7.1 Docker网络操作

**为容器创建可访问的网络**：
```bash
# 创建网络
docker network create my-network

# 运行容器并加入网络
docker run -d --name container1 --network my-network image1
docker run -d --name container2 --network my-network image2

# 容器间可以通过容器名通信
```

### 7.2 Docker数据共享

**容器之间共享数据**：
```bash
# 使用数据卷
docker run -d --name container1 -v /data image1
docker run -d --name container2 --volumes-from container1 image2
```

**容器与宿主机共享数据**：
```bash
docker run -d --name container1 -v /宿主机路径:/容器路径 image1
```

### 7.3 Docker容器异常排查

**查看容器日志**：
```bash
docker logs -t -f 容器名
```

**进入容器排查**：
```bash
docker exec -it 容器ID /bin/bash
```

**查看容器资源使用**：
```bash
docker stats -a
```

### 7.4 Docker镜像上传

**上传到Docker Hub**：
```bash
# 给镜像打标签
docker tag 镜像名:版本 用户名/镜像名:版本

# 推送镜像
docker push 用户名/镜像名:版本
```

---

## 8. 部署策略

### 8.1 灰度发布

**定义**：逐步将流量切换到新版本，观察无问题后再完全切换。

**特点**：
- 风险低
- 可快速回滚
- 需要流量控制

### 8.2 蓝绿部署

**定义**：准备两套完全相同的环境（蓝组和绿组），通过切换负载均衡实现版本切换。

**特点**：
- 零停机
- 回滚快速
- 资源消耗大

### 8.3 金丝雀部署

**定义**：先让一小部分用户使用新版本，验证通过后逐步扩大范围。

**特点**：
- 风险最低
- 需要精细的流量控制
- 适合大规模系统

### 8.4 Kubernetes滚动升级和回滚

**滚动升级**：
```bash
# 更新镜像
kubectl set image deployment/deployment-name container-name=new-image:tag

# 查看升级状态
kubectl rollout status deployment/deployment-name
```

**回滚**：
```bash
# 回滚到上一版本
kubectl rollout undo deployment/deployment-name

# 回滚到指定版本
kubectl rollout undo deployment/deployment-name --to-revision=2
```

---

## 9. Kubernetes存储管理

### 9.1 存储管理方式

1. **Volume**：Pod级别的存储卷
2. **PersistentVolume (PV)**：集群级别的存储资源
3. **PersistentVolumeClaim (PVC)**：用户对存储的请求

### 9.2 故障恢复和自我修复

Kubernetes的自我修复机制：
- **Liveness Probe**：检测容器是否存活，失败则重启
- **Readiness Probe**：检测容器是否就绪，失败则从Service端点移除
- **Controller Manager**：监控集群状态，自动恢复异常

---

## 10. 其他概念

### 10.1 Docker Compose

**定义**：用于定义和运行多容器Docker应用程序的工具。

**作用**：
- 简化多容器应用的部署
- 使用YAML文件定义服务
- 一键启动所有服务

**使用场景**：
- 本地开发环境
- 测试环境
- 小型部署

### 10.2 Docker Swarm

**定义**：Docker原生的集群管理和编排工具。

**作用**：
- 将多个Docker主机组合成虚拟主机
- 提供服务发现、负载均衡、扩缩容等功能

**使用场景**：
- 轻量级容器编排
- 已有Docker环境
- 对K8s复杂度敏感的场景

### 10.3 Etcd

**定义**：分布式键值存储，用于存储Kubernetes集群的所有数据。

**基本原理**：
- Raft一致性算法
- 高可用、分布式
- 存储集群状态信息

### 10.4 Kubernetes调度器

**作用**：负责在集群中找到适当的节点来运行Pod。

**考虑因素**：
- 节点的处理能力
- 内存、磁盘容量
- 亲和性/反亲和性规则
- 污点和容忍度

---

## 总结

本文档系统性地汇总了Docker与Kubernetes的核心知识点，包括：

1. **Docker基础**：镜像、容器、仓库的概念和常用命令
2. **Kubernetes概述**：定义、解决的问题、工作原理
3. **Kubernetes核心组件**：Master节点和Node节点的组件
4. **Kubernetes基本概念**：Node、Pod、Service、Labels
5. **工作资源对象**：Deployment、StatefulSet、DaemonSet
6. **Docker与Kubernetes对比**：区别和各自的作用
7. **常用操作与命令**：网络、数据共享、日志排查
8. **部署策略**：灰度发布、蓝绿部署、金丝雀部署

通过本文档，可以系统性地掌握容器化技术的核心概念和实践方法。