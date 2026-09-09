# AI大模型知识汇总

## 目录

1. [DeepSeek入门指南](#1-deepseek入门指南)
2. [DeepSeek本地部署教程](#2-deepseek本地部署教程)
3. [AI编程工具实战](#3-ai编程工具实战)
4. [IDEA集成DeepSeek](#4-idea集成deepseek)
5. [Spring AI Alibaba整合](#5-spring-ai-alibaba整合)
6. [大模型平台接入最佳实践](#6-大模型平台接入最佳实践)
7. [其他AI模型与工具](#7-其他ai模型与工具)

---

## 1. DeepSeek入门指南

### 1.1 DeepSeek简介

DeepSeek是由杭州深度求索人工智能基础技术研究有限公司开发的一款大型语言模型（LLM），其核心功能包括：

- 自然语言处理（NLP）
- 计算机视觉（CV）
- 强化学习（RL）
- 多模态融合技术

**DeepSeek的成就：**
- 用户下载量：在美国苹果应用商店免费下载排行榜中超越ChatGPT，成为排名第一的应用
- 开源策略和低成本优势吸引了大量企业和投资者的关注

### 1.2 快速上手（30分钟）

#### 1.2.1 创建AI伙伴

**步骤详解：**

1. **访问官网**：浏览器输入 `www.deepseek.com`（不需要下载软件）
2. **注册账号**：输入手机号码 → 选择微信扫码登录/手机注册
   - 首次登录：输入密码时建议使用"大小写字母+数字"组合（例如：Deep2024@seek）

**避坑指南：**
- 如果遇到验证码不显示，尝试刷新页面或切换浏览器
- 注册后建议立即绑定手机号，方便找回账号

**手机端使用：**
- 可以直接在应用商店（安卓或苹果）下载DeepSeek应用

#### 1.2.2 认识AI控制台

**核心界面组成部分：**

1. **欢迎与功能简介**
   - 文本内容：`我是 DeepSeek，很高兴见到你！我可以帮你写代码、读文件、写作者和创意内容，请把你的任务交给我吧~`
   - 作用：明确说明DeepSeek的核心能力

2. **消息输入区域**
   - 提示文字：`给 DeepSeek 发送消息`
   - 作用：用户与DeepSeek互动的主要入口

3. **功能模式选择**
   - **深度思考 (R1)**：适用于需要复杂分析、推理或多步处理的任务（如代码调试、数学推导、逻辑分析等）
   - **联网搜索**：允许DeepSeek访问互联网获取实时信息

### 1.3 API版本使用

#### 1.3.1 官网API入口

- 官网注册：`https://platform.deepseek.com`
- 充值几块钱就够用了
- 如果官网API无法使用，可以用硅基流动的API入口

#### 1.3.2 硅基流动的API

**白嫖2000万Token教程：**

1. 注册账号直接送2000万Token
2. 下载开源软件Cherry Studio（https://cherry-ai.com/）
3. 配置API密钥

**优势：**
- 跟华为云合作搞的服务器，速度快
- 手机电脑pad全能用
- 企业级服务不宕机

### 1.4 有效提问的五个黄金法则

#### 法则1：明确需求
- ❌ 错误示例：`帮我写点东西`
- ✅ 正确姿势：`我需要一封求职邮件，应聘新媒体运营岗位，强调3年公众号运营经验`

#### 法则2：提供背景
- ❌ 错误示例：`分析这个数据`
- ✅ 正确姿势：`这是一家奶茶店过去三个月的销售数据，请分析周末和工作日的销量差异（附CSV数据）`

#### 法则3：指定格式
- ❌ 错误示例：`给几个营销方案`
- ✅ 正确姿势：`请用表格形式列出三种情人节咖啡店促销方案，包含成本预估和预期效果`

#### 法则4：控制长度
- ❌ 错误示例：`详细说明`
- ✅ 正确姿势：`请用200字以内解释区块链技术，让完全不懂技术的老人能听懂`

#### 法则5：及时纠正
- 当回答不满意时，可以：
  - `这个方案成本太高，请提供预算控制在500元以内的版本`
  - `请用更正式的语气重写第二段`

### 1.5 新手必学的魔法指令

**基础指令集：**

1. `/续写`：当回答中断时自动继续生成
2. `/简化`：将复杂内容转换成大白话
3. `/示例`：要求展示实际案例（特别是写代码时）
4. `/步骤`：让AI分步骤指导操作流程
5. `/检查`：帮你发现文档中的错误

### 1.6 文档分析与代码生成

#### 1.6.1 文档分析

**操作流程：**

1. 点击"回形针"图标上传文件（支持PDF/Word/TXT）
2. 输入具体指令

**避坑指南：**
- 超过50页的文档建议先拆分处理
- 扫描版PDF需确保文字可复制

#### 1.6.2 代码生成

**万能模板：**

```
【语言】Python
【功能】自动下载网页图片
【要求】
- 处理SSL证书错误
- 显示下载进度条
- 保存到指定文件夹
```

**执行策略：**

1. 先让AI生成代码
2. 要求添加注释说明
3. 请求逐行解释关键代码段
4. 遇到报错直接粘贴错误信息

### 1.7 学术论文全流程辅助

#### 1.7.1 开题攻坚

**找研究方向：**

```
我是机械工程专业本科生，请推荐5个适合毕设的智能机器人相关课题，要求：
- 具有创新性但不过于前沿
- 需要仿真实验而非实物制作
- 附相关参考文献查找关键词
```

**优化题目：**

示例对话：
- 你：`基于深度学习的机械臂抓取系统研究`
- AI：`建议改为'基于改进YOLOv5的未知物体自适应抓取系统研究'，创新点更明确`

**文献速览：**

上传10篇PDF文献后输入：
```
请用表格对比各文献的研究方法，按'创新点/局限/可借鉴处'三列整理
```

#### 1.7.2 正文写作

**核心技巧：**

- **方法描述**：`请将这段实验步骤改写成学术被动语态：『我们先用CAD画了模型，然后导入ANSYS做力学分析』`
- **数据可视化**：提供Excel数据后输入 `请建议三种适合展示温度变化曲线的图表类型，并说明选择理由`
- **降重技巧**：对指定段落使用指令 `/学术化改写 保持原意但调整句式结构`

#### 1.7.3 查重降重一体化

**查重预检：**

```
分析以下段落：[粘贴文本]
1. 预测查重率及高危段落（标红显示）
2. 识别潜在引用缺失（推荐3篇相关文献）
3. 给出改写建议（同义替换/结构调整）
```

**示例输出：**

原句："机器学习需要大量数据支持"

改写方案："当代AI模型的训练过程，往往依赖于海量样本的持续输入（Wang et al., 2022）"

### 1.8 自媒体运营从0到1

#### 1.8.1 爆款内容生产线

**标题生成术：**

**基础版：**
```
请生成10个关于『时间管理』的小红书标题，要求：
- 使用emoji符号
- 包含数字量化
- 突出痛点解决
```

**进阶版：**
```
将『Python入门教程』改写成吸引大学生的抖音文案标题，要求：
- 使用悬念结构
- 不超过15字
- 带热门话题标签
```

#### 1.8.2 内容创作模板

```
【类型】科普类短视频脚本
【主题】量子计算机原理
【要求】
1. 用「冰箱整理食物」做类比解释量子比特
2. 每30秒设置一个悬念转折
3. 结尾引导点赞话术
```

---

## 2. DeepSeek本地部署教程

### 2.1 本地部署的优势

- deepseek最近非常火，有时很卡顿，用不了
- 本地部署可以解决这个问题
- 几分钟就可以安装完

### 2.2 安装Ollama

#### 2.2.1 下载Ollama

- 官网下载直通车：https://ollama.com
- 操作就像安装QQ一样简单，点击Download

**安装步骤：**

1. 双击下载的.exe安装包
2. 狂点「下一步」直到完成

#### 2.2.2 安装模型

**步骤详解：**

1. 回到Ollama官网，搜索框里搜索deepseek-r1
2. 选择要安装的模型

**模型版本选择：**

- 电脑配置不行：建议选择1.5B版本（15亿参数，最轻量）
- 电脑配置好：可以选择7b以上的版本

3. 复制代码：`ollama run deepseek-r1:1.5b`

4. 按下键盘上的win+R，调出运行窗口，输入cmd回车

5. 粘贴代码到命令行中，点击回车

6. 等待安装完成（会有百分比进度条）

### 2.3 安装可视化工具：ChatBox

**ChatBox客户端：**

- 官网直达：https://chatboxai.app

**安装姿势：**

1. 点击免费下载后，解压后双击ChatBoxSetup.exe
2. 自定义安装路径（别放C盘！建议装D盘）
3. 选择"使用自己的 API Key 或本地模型"
4. 点击右下角的设置，设置好模型
5. 选择Ollama API，选择已经安装好的模型

### 2.4 QWQ-32B本地部署

**QwQ-32B特点：**

- 阿里推出的推理模型
- 性能差不多，相比DeepSeek满血版的6710亿参数，QwQ-32B只有320亿参数
- 成本降低了20倍
- 本地部署成本只需要一张消费级显卡RTX8090即可

**安装步骤：**

1. 安装Ollama（同上）
2. 搜索qwq，选择32b版本
3. 需要20G存储空间，至少32G运行内存，一张H100或者RTX8090即可
4. 复制代码：`ollama run qwq`
5. 安装可视化工具：ChatBox（同上）

---

## 3. AI编程工具实战

### 3.1 AI编程工具发展历程

**发展历程：**

1. **早期阶段**：编程插件（Copilot、豆包MarsCode等）
   - 自动提示代码
   - 查找Bug
   - 优化代码结构

2. **新一代工具**：Cursor、Windsurf
   - 支持自然语言交互
   - 开发者通过对话提出需求
   - AI生成相应的代码模块或解决方案
   - 覆盖软件开发的完整生命周期

3. **Trae IDE**：字节跳动发布
   - 集成Claude 3.5和GPT-4o
   - 中文语义理解优化
   - 免费开放阶段

### 3.2 Trae IDE实战

#### 3.2.1 Trae简介

**核心功能：**

- 集成业界领先的大语言模型Claude 3.5和GPT-4o
- 提供强大的代码生成和智能优化能力
- 目前处于免费开放阶段

**两种核心工作模式：**

1. **Chat模式**：
   - 提供实时的代码理解和分析能力
   - 支持智能问答交互
   - 在编辑器中提供实时的代码建议
   - AI助手深度理解当前项目上下文

2. **Builder模式**：
   - 通过自然语言需求描述
   - 自动完成从项目初始化到功能实现的全流程构建
   - 支持多种项目模板和架构范式

#### 3.2.2 实战体验：从零开始的游戏开发

**下载安装：**

- 官网：https://www.trae.ai/
- 暂时只支持Mac，Windows很快会跟上
- 可以选择中文和主题
- 支持从Cursor或VS Code导入配置

**实战案例：开发《是男人就下100层》小游戏**

1. 选择Builder模式进行对话
2. 描述需求功能
3. AI自动生成代码和功能模块
4. 使用SVG生成游戏图标
5. 运行Python指令，游戏界面即可实现
6. 调试修改：Builder模式适合快速原型开发，Chat模式更擅长精细化调优

**体验与反馈：**

**优势：**
- 中文语义理解：针对中文开发者优化的自然语言处理能力
- 智能化程度：从环境配置到代码生成的全流程智能支持
- 开发体验：简洁的界面设计和流畅的交互体验

**需要加强优化：**
- 模式互补：Builder模式适合快速原型开发，Chat模式更擅长精细化调优
- Builder还是Beta阶段，功能可能不够完善

### 3.3 其他AI编程工具

#### 3.3.1 Cursor

- 支持自然语言交互
- 代码生成能力强
- 需要魔法上网

#### 3.3.2 Windsurf

- 新一代AI编程工具
- 支持MCP服务
- 与Cursor类似

---

## 4. IDEA集成DeepSeek

### 4.1 使用Continue插件

#### 4.1.1 安装Continue插件

1. 在IDEA中点击设置 → 插件
2. 搜索插件`continue`
3. 安装完成后，在右侧便可以看到continue的图标

#### 4.1.2 添加配置DeepSeek-R1模型

1. 选择DeepSeek模型
2. 选择DeepSeek Coder
3. API key来源：到官网注册 `www.deepseek.com`
4. 注册完成后，登录并创建API
5. 复制KEY后，使用

**使用示例：**

```
"这是一个orc的实现逻辑，请优化识别效率与正确率"
```

点击图标，代码自动插入。

**注意：由于恶意攻击，可能导致响应比较缓慢。**

#### 4.1.3 使用CodeGPT插件

**安装CodeGPT插件：**

1. 在IDEA中点击设置 → 插件
2. 搜索插件`codeGPT`
3. 安装完成后，在右侧便可以看到codeGPT的图标

**修改CodeGPT配置：**

在settings下面的CodeGPT--Providers--Custom OpenAI下的URL下修改：

- API key：填入DeepSeek API key
- URL：`https://api.deepseek.com/chat/completions`

**参考配置文档：** `https://api-docs.deepseek.com/zh-cn/`

**将模型改为R1模型**

**代码补全提示：**

- FIM template：选择DeepSeek Coder
- URL：填入 `https://api.deepseek.com/beta/completions`

### 4.2 两分钟IDEA接入满血DeepSeek R1模型

#### 4.2.1 注册硅基流动账号

1. 访问硅基流动：https://cloud.siliconflow.cn/i/wn4Ok7Iz
2. 直接点击注册（获得2000万的Tokens）
3. 在左侧的API密钥菜单栏中，生成API密钥

#### 4.2.2 通过Continue插件接入

**Continue插件配置：**

```json
{
  "models": [
    {
      "title": "deepseek-ai/DeepSeek-R1",
      "model": "deepseek-ai/DeepSeek-R1",
      "contextLength": 30000,
      "provider": "openai",
      "apiBase": "https://api.siliconflow.cn/v1",
      "apiKey": "输入自己的API keys",
      "requestOptions": {
        "extraBodyProperties": {
          "transforms": []
        }
      }
    }
  ],
  "tabAutocompleteModel": [
    {
      "title": "deepseek-ai/DeepSeek-V2.5",
      "provider": "openai",
      "model": "deepseek-ai/DeepSeek-V2.5",
      "contextLength": 30000,
      "apiBase": "https://api.siliconflow.cn/v1",
      "apiKey": "输入自己的API keys",
      "useLegacyCompletionsEndpoint": false
    }
  ]
}
```

**测试示例：**

```
帮我用Java实现一个冒泡排序
```

---

## 5. Spring AI Alibaba整合

### 5.1 Spring AI Alibaba简介

Spring AI Alibaba开源项目基于Spring AI构建，是阿里云通义系列模型及服务在Java AI应用开发领域的最佳实践，提供高层次的AI API抽象与云原生基础设施集成方案，帮助开发者快速构建AI应用。

### 5.2 阿里云百炼平台

**阿里云百炼特点：**

- 可视化AI智能体应用开发平台
- 提供三种大模型应用开发模式：智能体、工作流与智能体编排
- 支持知识库检索、互联网搜索、工作流设计及智能体协作等功能
- 0代码基础就能创建RAG应用

**开通阿里云百炼：**

- 官网：https://bailian.console.aliyun.com/
- 首次开通服务的用户可获得免费试用额度

### 5.3 SpringBoot接入DeepSeek实战

#### 5.3.1 添加依赖

```xml
<dependency>
  <groupId>com.alibaba.cloud.ai</groupId>
  <artifactId>spring-ai-alibaba-starter</artifactId>
  <version>1.0.0-M5.1</version>
</dependency>
```

**注意：由于spring-ai相关依赖包还没有发布到中央仓库，如出现spring-ai-core等相关依赖解析问题，请在pom.xml中加入仓库配置：**

```xml
<repositories>
  <repository>
    <id>spring-milestones</id>
    <name>Spring Milestones</name>
    <url>https://repo.spring.io/milestone</url>
    <snapshots>
      <enabled>false</enabled>
    </snapshots>
  </repository>
</repositories>
```

#### 5.3.2 配置application.yml

```yaml
spring:
  application:
    name: alibaba-ai-demo
  ai:
    dashscope:
      api-key: ${AI_DASHSCOPE_API_KEY}   # api key
      chat:
        options:
          model: deepseek-r1   # 模型名称
```

**注意：**
- Spring AI Alibaba基于Spring Boot 3.x开发
- 本地JDK版本要求为17及以上

#### 5.3.3 注入智能体代理ChatClient

```java
@RestController
public class ChatController {

    private final ChatClient chatClient;

    public ChatController(ChatClient.Builder builder) {
        this.chatClient = builder.build();
    }

    @GetMapping("/chat")
    public String chat(@RequestParam(value = "input") String input) {
        return this.chatClient.prompt()
                .user(input)
                .call()
                .content();
    }
}
```

**ChatClient参数配置：**

1. **全局默认值**：在application.yml文件中指定 `spring.ai.dashscope.chat.options.*`
2. **每次Prompt调用前动态指定**：

```java
String result = dashScopeChatClient
  .prompt(query)
  .options(DashScopeChatOptions.builder().withTopP(0.8).build())
  .call()
  .content();
```

### 5.4 SpringBoot接入QwQ-32B

#### 5.4.1 添加依赖

```xml
<dependency>
  <groupId>com.alibaba.cloud.ai</groupId>
  <artifactId>spring-ai-alibaba-starter</artifactId>
  <version>1.0.0-M5.1</version>
</dependency>
```

#### 5.4.2 配置application.yml

```yaml
spring:
  application:
    name: qwq-demo
  ai:
    dashscope:
      api-key: ${AI_DASHSCOPE_API_KEY}
      chat:
        options:
          model: qwq-32b
```

#### 5.4.3 注入ChatClient

```java
@RestController
public class ChatController {

  private final ChatClient chatClient;

  public ChatController(ChatClient.Builder builder) {
    this.chatClient = builder.build();
  }

  @GetMapping(value = "/stream",produces = "text/html;charset=utf-8")
  public Flux<String> stream(String input) {
    return this.chatClient.prompt()
        .user(input)
        .stream()
        .content();
  }
}
```

### 5.5 SpringBoot+Spring AI Alibaba接入RAG应用

#### 5.5.1 RAG简介

**RAG（Retrieval-Augmented Generation，检索增强生成）**：

- 非常适合于在私域知识问答场景中消除大模型幻觉（编造答案）
- 大模型无法回答预训练阶段没有准确掌握的知识
- 在大模型直接回答私有领域问题之前，给大模型一些参考

**RAG应用的两个关键过程：**

1. **建立索引**：
   - 将私有领域知识的文档（如PDF、Word等格式）存储起来并建立索引
   - 将文档中的文字提取加载出来
   - 切分成小的分块（chunk）以避免超过大模型提示词长度限制
   - 将文本chunk向量化后存储到向量数据库中

2. **检索和生成**：
   - 用户进行提问
   - RAG应用收到用户问题后，去向量数据库中检索和问题相关的chunk
   - 将相关的chunk组合到提示词中给到大模型
   - 大模型结合参考信息给出回答

#### 5.5.2 基于阿里云百炼平台0代码构建RAG应用

**步骤：**

1. **开通阿里云百炼**
   - 官网：https://bailian.console.aliyun.com/
   - 首次开通服务的用户可获得免费试用额度

2. **创建知识库**
   - 单击左侧菜单栏中的"数据管理"
   - 在默认类目下，单击"导入数据"
   - 上传知识库文件
   - 单击左侧菜单栏中的"数据应用-知识索引"
   - 单击"创建知识库"
   - 填写知识库名称，其他参数保持默认
   - 选择文件，选择智能切分，单击"导入完成"

3. **创建RAG应用**
   - 单击左侧边栏的"应用中心-我的应用"
   - 单击"新增应用>直接创建"
   - 配置应用信息：
     - 应用名称：示例名称-学校信息答疑机器人
     - 模型：选择通义千问系列模型
     - 知识检索增强：开启
     - 选择知识库：选择创建好的知识库

4. **测试RAG应用**
   - 在右侧边栏体验窗区域，切换为发布版
   - 输入问题进行测试

5. **发布RAG应用**
   - 点击页面右上角的"发布"按钮
   - 通过API与这个智能体应用进行对话

#### 5.5.3 SpringBoot接入RAG应用

**添加依赖：**

```xml
<dependency>
    <groupId>com.alibaba.cloud.ai</groupId>
    <artifactId>spring-ai-alibaba-starter</artifactId>
    <version>${spring-ai-alibaba.version}</version>
</dependency>
```

**配置application.yml：**

```yaml
spring:
  ai:
    dashscope:
      agent:
        app-id: put-your-app-id-here
      api-key: ${AI_DASHSCOPE_API_KEY}
```

**配置说明：**

- api-key：必填，访问模型服务的key
- app-id：必填，每个百炼应用都有一个id，用户唯一标识这个应用
- workspace-id：选填，默认使用默认业务空间，如果是在独立业务空间创建的应用则需要指定

---

## 6. 大模型平台接入最佳实践

### 6.1 业务系统接入大模型的三种方式

OpenAI第一次开发者大会的主题为"Maximizing LLM Performance"，提出业务系统可以通过三种方式接入大模型：

1. **PROMPT（直接给大模型输入提示词）**
2. **RAG（通过检索增强来提升大模型的能力）**
3. **Fine-tuning（通过微调训练来提升大模型的能力）**

### 6.2 直接PROMPT方式接入

#### 6.2.1 PROMPT的常用技巧

**Zero-Shot, One-Shot, Few-Shot：**

- **Zero-Shot学习**：让模型在没有任何相关数据的情况下，直接用自然语言指令来完成一个新任务
- **One-Shot学习**：让模型在只有一个相关数据的情况下，用自然语言指令和一个例子来完成一个新任务
- **Few-Shot学习**：让模型在有少量相关数据的情况下，用自然语言指令和几个例子来完成一个新任务

**链式思维（Chain of Thoughts）：**

- 把复杂问题拆分成很多环环相扣的步骤，逐步解决问题
- 通过在每个答案之前简单添加"让我们逐步思考（Let's think step by step）"，大模型可以成为出色的零样本推理者
- 将这个简单的技巧应用于MultiArith数学数据集，准确度从18%提升到79%

**任务分解：**

- 当一个任务比较复杂时，将一个复杂的任务分解成更小、更容易处理的子任务
- 经典例子：AB两个城市之间搬运货物，需要分三个步骤，A城市装货，AB城市之间运输，B城市卸货
- HuggingGPT工程：任务分解的典型应用

#### 6.2.2 在PROMPT提示语中嵌入业务知识

在为大模型设计PROMPT时，通常可以将其分为四个可选部分：

1. **用户指令**：明确告诉大模型需要执行的具体任务
2. **上下文信息**：提供相关的背景信息
3. **输出格式**：指定期望的输出格式
4. **示例**：提供相关的示例

### 6.3 通过RAG方式接入

#### 6.3.1 RAG的实现

**RAG的流程：**

1. 文档加载和切分
2. 向量化存储
3. 检索相关文档
4. 生成答案

**知识检索如何实现：**

- 使用向量数据库（如Milvus、Pinecone等）
- 使用嵌入模型（如OpenAI Embeddings、BGE等）
- 使用检索算法（如BM25、向量相似度等）

#### 6.3.2 业务接入RAG检索的例子

**SQLChat + Ollama + OneAPI实战：**

**技术栈核心组件：**

1. **SQLChat**：自然语言转SQL的智能网关
   - 开源的、基于Web的自然语言转SQL工具
   - 支持连接多种数据库（如MySQL、PostgreSQL等）
   - 核心功能：接收用户输入的自然语言问题，调用大模型生成对应的SQL语句，执行查询并返回可视化结果

2. **Ollama**：本地运行大模型的利器
   - 支持在本地运行大模型（如Llama 3、Mistral、CodeLlama等）
   - 支持模型量化（如4-bit精度），降低硬件资源需求
   - 提供API接口，便于与其他工具集成

3. **OneAPI**：统一管理多模型服务的API网关
   - 开源的API管理平台
   - 支持聚合多种大模型服务（如OpenAI、Azure、本地部署的Ollama等）
   - 提供统一的访问接口和权限控制

**部署步骤：**

1. **部署Ollama并加载模型**
   - 访问ollama官网：https://ollama.com/
   - 下载安装后访问：http://localhost:11434/
   - 使用命令下载模型：`ollama run sqlcoder`

2. **部署OneAPI并配置模型**
   - 使用Docker部署：`docker run --name one-api -d --restart always -p 3000:3000 -e SQL_DSN="root:1qaz@WSX@tcp(host.docker.internal:3306)/oneapi" -e TZ=Asia/Shanghai -v /home/ubuntu/data/one-api:/data justsong/one-api`
   - 访问localhost:3000，默认账号：root，密码：123456
   - 配置模型渠道

3. **部署SQLChat**
   - 使用Docker部署：`docker run --name sqlchat -d --hostname host --restart always -p 3761:3000 -e NEXTAUTH_SECRET=hjisabfia -e OPENAI_API_KEY=sk-OLfk67FYybc2zs6GE13561AaEe474775B90dE1543707018a -e OPENAI_API_ENDPOINT=http://host.docker.internal:3000/v1 -e NEXT_PUBLIC_ALLOW_SELF_OPENAI_KEY=true sqlchat/sqlchat`
   - 访问链接：http://localhost:3761/
   - 配置MySQL数据库

### 6.4 通过Fine-tuning方式接入

#### 6.4.1 微调训练的方式

- **全量微调**：对模型的所有参数进行微调
- **LoRA（Low-Rank Adaptation）**：只训练低秩矩阵，参数效率高
- **QLoRA**：量化后的LoRA，进一步降低显存需求

#### 6.4.2 KubeAI大模型平台上如何进行Fine-tuning

（具体操作请参考KubeAI平台文档）

### 6.5 业务系统接入大模型的最佳路径

**渐进式接入大模型：**

1. **第一阶段：PROMPT方式**
   - 最简单最直接的方式
   - 快速验证业务场景
   - 成本最低

2. **第二阶段：RAG方式**
   - 引入私有领域知识
   - 提升大模型准确性
   - 消除幻觉

3. **第三阶段：Fine-tuning方式**
   - 深度定制模型
   - 提升特定任务表现
   - 成本较高

---

## 7. 其他AI模型与工具

### 7.1 接入AI网关Higress实现多个AI大模型的无缝切换

#### 7.1.1 Higress AI网关简介

Higress AI网关提供强大的解决方案，支持：

- 多模型服务
- 消费者鉴权
- 模型自动切换

**应用场景：**

- 企业可能需要同时对接多个大模型，以满足不同业务场景的需求
- 当单个模型出现稳定性问题时，能够迅速回退到另一个模型，确保业务的连续性和稳定性
- 在Multi Agent场景下，一个复杂任务可能需要调用多个模型来协同完成

#### 7.1.2 环境准备

```bash
# 一键安装Higress（需Docker环境）
curl -sS https://higress.cn/ai-gateway/install.sh | bash
```

安装完成后访问控制台http://localhost:8001，完成初始化配置。

**注意：**
- 默认脚本是监听的127.0.0.1
- 如果想通过Windows本地机器访问虚拟机中的Higress，将IP替换为0.0.0.0

#### 7.1.3 模型接入配置

在Higress控制台中，分别配置DeepSeek-R1和QwQ-32B的接入方式：

- 对于厂商模型，选择相应的厂商名进行配置
- 对于自建模型，使用OpenAI兼容模式，填入baseURL即可

**创建路由规则：**

1. 创建名为`aliyun`的路由，匹配模型名称精确匹配`qwq-32b`，转发给阿里云百炼平台的QwQ-32B模型服务
2. 创建名为`deepseek`的路由，匹配模型名称精确匹配`deepseek-`，转发给DeepSeek平台服务

#### 7.1.4 测试示例

```bash
curl 'http://192.168.65.185:8080/v1/chat/completions' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen-turbo",
    "messages": [
      {
        "role": "user",
        "content": "你是谁!"
      }
    ]
  }'
```

#### 7.1.5 Spring AI整合Higress实现多模型无缝切换

**引入依赖：**

```xml
<dependency>
  <groupId>org.springframework.ai</groupId>
  <artifactId>spring-ai-openai-spring-boot-starter</artifactId>
</dependency>
```

**配置application.yml：**

```yaml
spring:
  application:
    name: higress-demo
  ai:
    openai:
      api-key: cbfda275-56ff-4d45-a984-6482502e2f25   # Higress的消费者认证key
      base-url: http://192.168.65.185:8080/v1    # Higress的网关地址
      chat:
        options:
          model: deepseek-chat
```

**使用ChatModel实现对话：**

```java
@RestController
public class ChatModelController {
  private final ChatModel chatModel;

  public ChatModelController(ChatModel chatModel) {
    this.chatModel = chatModel;
  }

  @RequestMapping("/chat")
  public String chat(String input) {
    ChatResponse response = chatModel.call(new Prompt(input));
    return response.getResult().getOutput().toString();
  }
}
```

### 7.2 其他AI工具

#### 7.2.1 Cherry Studio

- 开源的AI客户端
- 支持MCP服务
- 可以接入硅基流动的API

#### 7.2.2 ChatBox

- 可视化AI客户端
- 支持本地模型和云端模型
- 界面简洁美观

#### 7.2.3 SQLChat

- 自然语言转SQL工具
- 支持多种数据库
- 支持私有化部署

---

## 附录：常见问题与解决方案

### 1. DeepSeek服务器繁忙问题

**解决方案：**

1. 使用硅基流动的API
2. 注册账号获得2000万Token
3. 下载ChatBox AI客户端
4. 配置SiliconFlow API
5. 选择DeepSeek R1模型

### 2. 本地部署模型选择

**模型版本选择建议：**

- 电脑配置不行：选择1.5B版本（15亿参数，最轻量）
- 电脑配置好：选择7b以上的版本
- QwQ-32B：需要20G存储空间，至少32G运行内存，一张H100或者RTX8090即可

### 3. API密钥管理

**注意事项：**

- 密钥别泄露，本来就是白嫖的额度，泄露分分钟干完
- 定期更换密钥
- 使用环境变量存储密钥

---

## 总结

本文档系统性地汇总了AI大模型相关的核心知识，包括：

1. **DeepSeek入门指南**：从基础使用到高级功能，涵盖文档分析、代码生成、学术论文辅助等
2. **DeepSeek本地部署教程**：使用Ollama和ChatBox实现本地部署
3. **AI编程工具实战**：Trae、Cursor、Windsurf等工具的使用方法
4. **IDEA集成DeepSeek**：Continue和CodeGPT插件的配置与使用
5. **Spring AI Alibaba整合**：SpringBoot接入DeepSeek、QwQ-32B和RAG应用
6. **大模型平台接入最佳实践**：PROMPT、RAG、Fine-tuning三种接入方式
7. **其他AI模型与工具**：Higress AI网关、Cherry Studio、ChatBox等

通过本文档，开发者可以快速掌握AI大模型的使用方法，并将其应用到实际项目中。