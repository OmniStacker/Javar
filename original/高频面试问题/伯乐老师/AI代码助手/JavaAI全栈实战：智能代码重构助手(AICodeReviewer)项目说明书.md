# Java AI 全栈实战：智能代码重构助手 (AI Code Reviewer) 项目说明书

**<font style="color:rgb(26, 28, 30);">项目代号</font>**<font style="color:rgb(26, 28, 30);">：</font><font style="color:rgb(50, 48, 44);">Java-AI-Reviewer-v1.0</font><font style="color:rgb(26, 28, 30);">  
</font>**<font style="color:rgb(26, 28, 30);">适用人群</font>**<font style="color:rgb(26, 28, 30);">：Java 开发者、Spring Boot 学习者、AI 应用探索者  
</font>**<font style="color:rgb(26, 28, 30);">核心技术</font>**<font style="color:rgb(26, 28, 30);">：JDK 21 + Spring Boot 3 + Spring AI + Alibaba Qwen</font>

---

## <font style="color:rgb(26, 28, 30);">1. </font><font style="color:rgb(26, 28, 30);">📖</font><font style="color:rgb(26, 28, 30);"> 项目背景与简介</font>
### <font style="color:rgb(26, 28, 30);">1.1 痛点分析</font>
<font style="color:rgb(26, 28, 30);">在日常开发中，我们经常遇到以下问题：</font>

+ <font style="color:rgb(26, 28, 30);">接手“屎山”代码，逻辑混乱，不敢乱改。</font>
+ <font style="color:rgb(26, 28, 30);">团队 Code Review（代码评审）耗时耗力，甚至容易引发争论。</font>
+ <font style="color:rgb(26, 28, 30);">新手写代码缺乏规范，导致生产环境出现空指针（NPE）、性能 O(n²) 等隐患。</font>

### <font style="color:rgb(26, 28, 30);">1.2 项目定义</font>
<font style="color:rgb(26, 28, 30);">本项目是一个</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">基于大语言模型（LLM）的智能代码审计系统</font>**<font style="color:rgb(26, 28, 30);">。它就像一位 24 小时待命的“资深架构师”，能够实时对输入的代码进行：</font>

+ **<font style="color:rgb(26, 28, 30);">多维度评分</font>**<font style="color:rgb(26, 28, 30);">：直观了解代码质量。</font>
+ **<font style="color:rgb(26, 28, 30);">毒舌/专业点评</font>**<font style="color:rgb(26, 28, 30);">：精准定位 Bug 和安全隐患。</font>
+ **<font style="color:rgb(26, 28, 30);">自动重构</font>**<font style="color:rgb(26, 28, 30);">：一键生成符合大厂规范的优雅代码。</font>

---

## <font style="color:rgb(26, 28, 30);">2. </font><font style="color:rgb(26, 28, 30);">🏗️</font><font style="color:rgb(26, 28, 30);"> 技术架构方案</font>
<font style="color:rgb(26, 28, 30);">本项目坚持</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">“Java Native”</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">路线，不依赖 Python，利用 Spring 生态无缝接入 AI。</font>

| **<font style="color:rgb(26, 28, 30);">模块</font>** | **<font style="color:rgb(26, 28, 30);">技术选型</font>** | **<font style="color:rgb(26, 28, 30);">选择理由</font>** |
| --- | --- | --- |
| **<font style="color:rgb(26, 28, 30);">开发语言</font>** | <font style="color:rgb(26, 28, 30);">Java 21</font> | <font style="color:rgb(26, 28, 30);">Spring Boot 3 的基石，性能更强，LTS 长期支持。</font> |
| **<font style="color:rgb(26, 28, 30);">核心框架</font>** | <font style="color:rgb(26, 28, 30);">Spring Boot 3.2.x</font> | <font style="color:rgb(26, 28, 30);">约定大于配置，生态最成熟。</font> |
| **<font style="color:rgb(26, 28, 30);">AI 框架</font>** | **<font style="color:rgb(26, 28, 30);">Spring AI</font>** | <font style="color:rgb(26, 28, 30);">Spring 官方出品，标准化调用 OpenAI、Ollama 等模型。</font> |
| **<font style="color:rgb(26, 28, 30);">大模型</font>** | **<font style="color:rgb(26, 28, 30);">阿里云通义千问 (Qwen)</font>** | <font style="color:rgb(26, 28, 30);">兼容 OpenAI 协议，国内访问快，Token 便宜/免费，中文理解能力强。</font> |
| **<font style="color:rgb(26, 28, 30);">前端交互</font>** | <font style="color:rgb(26, 28, 30);">HTML5 + SSE</font> | <font style="color:rgb(26, 28, 30);">实现类似 ChatGPT 的</font>**<font style="color:rgb(26, 28, 30);">流式打字机</font>**<font style="color:rgb(26, 28, 30);">效果，提升用户体验。</font> |
| **<font style="color:rgb(26, 28, 30);">工具支持</font>** | <font style="color:rgb(26, 28, 30);">Cursor + Maven</font> | <font style="color:rgb(26, 28, 30);">AI 辅助编程，极大提高开发效率。</font> |


### <font style="color:rgb(26, 28, 30);">系统数据流图</font>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Mermaid</font>**

```properties
graph LR
User[用户提交代码] --> Frontend[前端页面]
Frontend -->|SSE 流式请求| Controller[Spring Boot Controller]
Controller -->|封装 System Prompt| AIService[AI 服务层]
AIService -->|HTTP/OpenAI 协议| Model[阿里千问大模型]
Model -->|Token 流| AIService
AIService -->|Stream| Frontend
Frontend -->|Markdown 渲染| User
```

---

## <font style="color:rgb(26, 28, 30);">3. </font><font style="color:rgb(26, 28, 30);">🛠️</font><font style="color:rgb(26, 28, 30);"> 环境准备与快速启动</font>
### <font style="color:rgb(26, 28, 30);">3.1 前置要求</font>
+ **<font style="color:rgb(26, 28, 30);">JDK</font>**<font style="color:rgb(26, 28, 30);">：必须版本 ≥</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">21</font>**
+ **<font style="color:rgb(26, 28, 30);">Maven</font>**<font style="color:rgb(26, 28, 30);">：版本 ≥ 3.6</font>
+ **<font style="color:rgb(26, 28, 30);">API Key</font>**<font style="color:rgb(26, 28, 30);">：阿里云百炼平台申请的 Key (</font><font style="color:rgb(50, 48, 44);">sk-xxxxxxxx</font><font style="color:rgb(26, 28, 30);">)</font>

### <font style="color:rgb(26, 28, 30);">3.2 配置文件 (</font><font style="color:rgb(50, 48, 44);">application.yml</font><font style="color:rgb(26, 28, 30);">)</font>
<font style="color:rgb(26, 28, 30);">这是项目运行的核心配置，请务必检查：</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Yaml</font>**

```plain
spring:
  application:
    name: ai-code-reviewer
  ai:
    openai:
      # ⚠️ 关键点：使用阿里兼容 OpenAI 的接口地址
      base-url: https://dashscope.aliyuncs.com/compatible-mode/v1
      api-key: ${ALI_API_KEY} # 你的 Key
      chat:
        options:
          # 推荐模型：qwen-turbo (性价比高) 或 qwen-plus
          model: qwen-turbo
          temperature: 0.7 # 0.7 保证一定的创造性，0.2 偏严谨
```

### <font style="color:rgb(26, 28, 30);">3.3 启动命令</font>
<font style="color:rgb(26, 28, 30);">在项目根目录下执行：</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Bash</font>**

```plain
mvn spring-boot:run
```

<font style="color:rgb(26, 28, 30);">启动成功后，访问：</font><font style="color:rgb(50, 48, 44);">http://localhost:8080</font>

---

## <font style="color:rgb(26, 28, 30);">4. </font><font style="color:rgb(26, 28, 30);">💻</font><font style="color:rgb(26, 28, 30);"> 核心代码解析 (面试/学习重点)</font>
### <font style="color:rgb(26, 28, 30);">4.1 后端：流式响应 (Flux)</font>
<font style="color:rgb(26, 28, 30);">为什么不用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">String</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">而用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">Flux<String></font><font style="color:rgb(26, 28, 30);">？因为大模型生成内容较慢，我们需要生成一个字就推给前端一个字，避免用户枯等。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Java</font>**

```plain
// Controller 层核心逻辑
@PostMapping(value = "/api/review", produces = MediaType.TEXT_EVENT_STREAM_VALUE) // 1. 声明 SSE 格式
public Flux<String> reviewCode(@RequestBody String userCode) {
    // 2. 定义人设 (System Prompt)
    String systemPrompt = "你是一位资深 Java 架构师，请审查代码并输出 Markdown 格式报告...";
    
    // 3. 调用 AI 并开启流式传输 (stream)
    return chatClient.prompt()
            .system(systemPrompt)
            .user(userCode)
            .stream() // 关键调用
            .content();
}
```

### <font style="color:rgb(26, 28, 30);">4.2 前端：解析 SSE 数据流</font>
<font style="color:rgb(26, 28, 30);">前端通过</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">fetch</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">API 读取 ReadableStream。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">JavaScript</font>**

```plain
// 处理数据流的关键代码片段
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    
    // 💡 技巧：去掉 SSE 协议头 "data:"，否则 Markdown 渲染会乱
    const cleanChunk = chunk.replace(/data:/g, ''); 
    
    // 实时渲染
    resultText += cleanChunk;
    resultDiv.innerHTML = marked.parse(resultText);
}
```

---

## <font style="color:rgb(26, 28, 30);">5. </font><font style="color:rgb(26, 28, 30);">🧙‍♂️</font><font style="color:rgb(26, 28, 30);"> Prompt 调优指南 (玩法扩展)</font>
<font style="color:rgb(26, 28, 30);">你可以通过修改</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">CodeReviewController.java</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">中的</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">systemPrompt</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">来改变 AI 的性格。</font>

+ **<font style="color:rgb(26, 28, 30);">场景 A：严格模式 (默认)</font>**
    - _<font style="color:rgb(26, 28, 30);">Prompt:</font>_<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">"你是一位严厉的代码审计员，请找出所有安全漏洞和性能陷阱，评分标准极其严格。"</font>
+ **<font style="color:rgb(26, 28, 30);">场景 B：新手教学模式</font>**
    - _<font style="color:rgb(26, 28, 30);">Prompt:</font>_<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">"你是一位耐心的编程导师，请用通俗易懂的语言解释代码中的问题，并给出学习建议。"</font>
+ **<font style="color:rgb(26, 28, 30);">场景 C：跨语言翻译模式</font>**
    - _<font style="color:rgb(26, 28, 30);">Prompt:</font>_<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">"请不要审查代码，而是将这段代码翻译成 Python 版本，并保持逻辑一致。"</font>

---

## <font style="color:rgb(26, 28, 30);">6. </font><font style="color:rgb(26, 28, 30);">❓</font><font style="color:rgb(26, 28, 30);"> 常见问题 (Q&A)</font>
**<font style="color:rgb(26, 28, 30);">Q1: 启动报错</font>****<font style="color:rgb(26, 28, 30);"> </font>****<font style="color:rgb(50, 48, 44);">class file has wrong version 65.0</font>****<font style="color:rgb(26, 28, 30);">？</font>**

**<font style="color:rgb(26, 28, 30);">A</font>**<font style="color:rgb(26, 28, 30);">: 这是因为你的 JDK 版本低于 21。Spring Boot 3 + Spring AI 必须使用 JDK 17+ (推荐 21)。请检查</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">java -version</font><font style="color:rgb(26, 28, 30);">。</font>

**<font style="color:rgb(26, 28, 30);">Q2: 前端一直显示 Loading，不吐字？</font>**

**<font style="color:rgb(26, 28, 30);">A</font>**<font style="color:rgb(26, 28, 30);">: 检查控制台是否有</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">401 Unauthorized</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(Key 错误) 或</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">404 Not Found</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(Base URL 写错)。确保 Base URL 末尾包含</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">/compatible-mode/v1</font><font style="color:rgb(26, 28, 30);">。</font>

**<font style="color:rgb(26, 28, 30);">Q3: AI 回答被截断了？</font>**

**<font style="color:rgb(26, 28, 30);">A</font>**<font style="color:rgb(26, 28, 30);">: 可能是 Nginx 或 浏览器的超时设置。但在本地环境通常是因为网络波动，建议检查代理配置。</font>

---

## <font style="color:rgb(26, 28, 30);">7. </font><font style="color:rgb(26, 28, 30);">🚀</font><font style="color:rgb(26, 28, 30);"> 下一步计划</font>
- [ ] <font style="color:rgb(28, 27, 27);">增加 </font>**<font style="color:rgb(28, 27, 27);">MySQL</font>**<font style="color:rgb(28, 27, 27);"> 支持，保存每次的审查记录。</font>
- [ ] <font style="color:rgb(28, 27, 27);">增加 </font>**<font style="color:rgb(28, 27, 27);">用户登录</font>**<font style="color:rgb(28, 27, 27);"> 功能。</font>
- [ ] <font style="color:rgb(28, 27, 27);">接入 </font>**<font style="color:rgb(28, 27, 27);">DeepSeek (深度求索)</font>**<font style="color:rgb(28, 27, 27);"> 本地模型，实现完全离线运行。</font>

---

**<font style="color:rgb(26, 28, 30);">版权声明</font>**<font style="color:rgb(26, 28, 30);">：本项目由 [伯乐] 原创开发，仅供学习交流。  
</font>**<font style="color:rgb(26, 28, 30);">获取源码</font>**<font style="color:rgb(26, 28, 30);">：关注 [伯乐讲技术] 回复 "AI源码"。</font>
