# 第 3 集：前端 SSE 流式交互与打字机效果实现

**<font style="color:rgb(26, 28, 30);">摘要</font>**<font style="color:rgb(26, 28, 30);">：本节我们将构建前端页面。你将学到如何使用 JavaScript 的 </font><font style="color:rgb(50, 48, 44);">fetch</font><font style="color:rgb(26, 28, 30);"> API 读取后端传来的数据流 (Stream)，如何清洗 SSE 协议数据，以及如何将 Markdown 实时渲染为漂亮的网页。</font>

## <font style="color:rgb(26, 28, 30);">1. 核心技术栈</font>
<font style="color:rgb(26, 28, 30);">为了保证所有 Java 开发者（哪怕不懂前端）都能看懂，我们采用</font>**<font style="color:rgb(26, 28, 30);">零构建工具</font>**<font style="color:rgb(26, 28, 30);">方案：</font>

+ **<font style="color:rgb(26, 28, 30);">HTML5/CSS3</font>**<font style="color:rgb(26, 28, 30);">：原生编写，左右分栏布局。</font>
+ **<font style="color:rgb(26, 28, 30);">Vanilla JS</font>**<font style="color:rgb(26, 28, 30);">：原生 JavaScript，无框架依赖。</font>
+ **<font style="color:rgb(26, 28, 30);">Marked.js</font>**<font style="color:rgb(26, 28, 30);">：通过 CDN 引入，用于 Markdown 解析（把</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">#</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">变成标题，把</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">```</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">变成代码块）。</font>
+ **<font style="color:rgb(26, 28, 30);">SSE (Server-Sent Events)</font>**<font style="color:rgb(26, 28, 30);">：处理流式响应的核心技术。</font>

---

## <font style="color:rgb(26, 28, 30);">2. 完整代码实现 (</font><font style="color:rgb(50, 48, 44);">index.html</font><font style="color:rgb(26, 28, 30);">)</font>
<font style="color:rgb(26, 28, 30);">请在项目的</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">src/main/resources/static/</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">目录下新建</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">index.html</font><font style="color:rgb(26, 28, 30);">，并粘贴以下代码。这是</font>**<font style="color:rgb(26, 28, 30);">开箱即用</font>**<font style="color:rgb(26, 28, 30);">的完整版本。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Html</font>**

```plain
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI 代码审查助手</title>
    <!-- 1. 引入 Marked.js 用于解析 Markdown -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        /* 简单的现代化 UI 布局 */
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; height: 100vh; display: flex; flex-direction: column; }
        header { background: #2c3e50; color: white; padding: 1rem; text-align: center; font-size: 1.2rem; font-weight: bold; }
        .container { flex: 1; display: flex; overflow: hidden; }
        
        /* 左侧：输入区 */
        .editor-pane { width: 40%; padding: 1rem; background: #f8f9fa; display: flex; flex-direction: column; border-right: 1px solid #ddd; }
        textarea { flex: 1; padding: 1rem; font-family: 'Consolas', monospace; font-size: 14px; border: 1px solid #ddd; resize: none; outline: none; }
        button { margin-top: 1rem; padding: 10px; background: #27ae60; color: white; border: none; cursor: pointer; font-size: 16px; border-radius: 4px; transition: 0.3s; }
        button:hover { background: #219150; }
        button:disabled { background: #ccc; cursor: not-allowed; }

        /* 右侧：结果展示区 */
        .preview-pane { width: 60%; padding: 2rem; overflow-y: auto; background: #fff; line-height: 1.6; }
        
        /* Markdown 样式微调 */
        .preview-pane pre { background: #f4f4f4; padding: 1rem; border-radius: 5px; overflow-x: auto; }
        .preview-pane code { font-family: 'Consolas', monospace; color: #c7254e; background: #f9f2f4; padding: 2px 4px; border-radius: 4px; }
        .preview-pane pre code { color: inherit; background: transparent; }
    </style>
</head>
<body>

<header>🤖 AI 代码审查助手 (Powered by Spring AI)</header>

<div class="container">
    <div class="editor-pane">
        <textarea id="codeInput" placeholder="请在此处粘贴需要审查的 Java 代码..."></textarea>
        <button id="btnSubmit" onclick="submitCode()">🚀 开始审查</button>
    </div>
    <div class="preview-pane" id="resultDiv">
        <p style="color: #888;">AI 审查报告将在此处生成...</p>
    </div>
</div>

<script>
    // 2. 核心交互逻辑
    async function submitCode() {
        const input = document.getElementById('codeInput');
        const btn = document.getElementById('btnSubmit');
        const resultDiv = document.getElementById('resultDiv');

        if (!input.value.trim()) {
            alert("请先输入代码！");
            return;
        }

        // UI 状态重置
        btn.disabled = true;
        btn.innerText = "审查中...";
        resultDiv.innerHTML = "⏳ AI 正在思考...";
        
        let fullText = ""; // 存储累加的文本

        try {
            // 3. 发起 Fetch 请求
            const response = await fetch('/api/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: input.value // 直接发送字符串
            });

            // 4. 获取读取器 (Reader)
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                // 读取数据流
                const { done, value } = await reader.read();
                if (done) break;

                // 解码字节流
                const chunk = decoder.decode(value, { stream: true });
                
                // ⚠️ 5. 关键：清洗数据 (去除 SSE 协议头 "data:")
                // Spring AI 默认返回格式是 "data: 内容 \n\n"
                // 我们需要用正则把 "data:" 和多余换行去掉
                const cleanChunk = chunk.replace(/data:/g, ''); 

                // 累加文本
                fullText += cleanChunk;

                // 实时渲染 Markdown
                resultDiv.innerHTML = marked.parse(fullText);
                
                // 自动滚动到底部
                resultDiv.scrollTop = resultDiv.scrollHeight;
            }
        } catch (error) {
            console.error(error);
            resultDiv.innerHTML = `<span style="color:red;">❌ 请求出错: ${error.message}</span>`;
        } finally {
            // 恢复按钮状态
            btn.disabled = false;
            btn.innerText = "🚀 开始审查";
        }
    }
</script>

</body>
</html>
```

---

## <font style="color:rgb(26, 28, 30);">3. 代码解析 (核心知识点)</font>
### <font style="color:rgb(26, 28, 30);">3.1 为什么要清洗数据 (</font><font style="color:rgb(50, 48, 44);">replace</font><font style="color:rgb(26, 28, 30);">)？</font>
<font style="color:rgb(26, 28, 30);">Spring AI 基于 OpenAI 协议，返回的数据块（Chunk）格式通常长这样：</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Text</font>**

```plain
data: 评
data: 分
data: ：
```

<font style="color:rgb(26, 28, 30);">如果不处理，网页上就会显示大量重复的</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">data:</font><font style="color:rgb(26, 28, 30);">。</font>

+ **<font style="color:rgb(26, 28, 30);">代码方案</font>**<font style="color:rgb(26, 28, 30);">：</font><font style="color:rgb(50, 48, 44);">chunk.replace(/data:/g, '')</font>
+ **<font style="color:rgb(26, 28, 30);">作用</font>**<font style="color:rgb(26, 28, 30);">：利用正则表达式全局替换，把协议头删掉，只保留有效内容。</font>

### <font style="color:rgb(26, 28, 30);">3.2 为什么用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">fetch</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">而不是</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">axios</font><font style="color:rgb(26, 28, 30);">？</font>
<font style="color:rgb(26, 28, 30);">虽然 Axios 很流行，但它默认不支持流式读取（Stream），它倾向于等所有数据下载完再返回。而原生</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">fetch</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">API 的</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">response.body.getReader()</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">是实现打字机效果的最佳原生方案。</font>

### <font style="color:rgb(26, 28, 30);">3.3 Markdown 渲染</font>
<font style="color:rgb(26, 28, 30);">AI 返回的是包含</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">**粗体**</font><font style="color:rgb(26, 28, 30);">、</font><font style="color:rgb(50, 48, 44);">### 标题</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">和</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">```代码块</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">的 Markdown 文本。</font>

+ <font style="color:rgb(26, 28, 30);">我们引入了</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">marked.js</font><font style="color:rgb(26, 28, 30);">。</font>
+ <font style="color:rgb(26, 28, 30);">调用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">marked.parse(fullText)</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">即可瞬间把纯文本转为 HTML 标签。</font>

---

## <font style="color:rgb(26, 28, 30);">4. </font><font style="color:rgb(26, 28, 30);">🧙‍♂️</font><font style="color:rgb(26, 28, 30);"> 给 Cursor 的提示词 (自动生成)</font>
<font style="color:rgb(26, 28, 30);">如果你想演示“完全不写代码”，可以将下面的 Prompt 投喂给 Cursor：</font>

<font style="color:rgb(26, 28, 30);">"请在 src/main/resources/static 下生成一个 index.html。</font>

+ <font style="color:rgb(26, 28, 30);">UI：左右分栏，左边 Textarea，右边 Div 显示结果。底部一个按钮。</font>
+ <font style="color:rgb(26, 28, 30);">逻辑：点击按钮发送 POST 请求到 /api/review。</font>
+ **<font style="color:rgb(26, 28, 30);">核心要求</font>**<font style="color:rgb(26, 28, 30);">：使用 fetch API 读取 Stream 流。每收到一个 chunk，就去掉 'data:' 前缀，然后累加到变量中。</font>
+ <font style="color:rgb(26, 28, 30);">引入 marked.js CDN，将累加的文本实时转换为 HTML 并渲染到右侧 Div。</font>
+ <font style="color:rgb(26, 28, 30);">CSS：简单美化，右侧代码块要有背景色。"</font>

---

## <font style="color:rgb(26, 28, 30);">5. </font><font style="color:rgb(26, 28, 30);">🛠️</font><font style="color:rgb(26, 28, 30);"> 避坑指南 (Troubleshooting)</font>
**<font style="color:rgb(26, 28, 30);">Q1: 页面显示</font>****<font style="color:rgb(26, 28, 30);"> </font>****<font style="color:rgb(50, 48, 44);">[object Promise]</font>****<font style="color:rgb(26, 28, 30);"> </font>****<font style="color:rgb(26, 28, 30);">或者</font>****<font style="color:rgb(26, 28, 30);"> </font>****<font style="color:rgb(50, 48, 44);">undefined</font>****<font style="color:rgb(26, 28, 30);">？</font>**

+ **<font style="color:rgb(26, 28, 30);">原因</font>**<font style="color:rgb(26, 28, 30);">：可能是</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">fetch</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">代码写错了，没有</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">await</font><font style="color:rgb(26, 28, 30);">，或者变量名写错。</font>
+ **<font style="color:rgb(26, 28, 30);">解决</font>**<font style="color:rgb(26, 28, 30);">：直接复制上面的完整代码覆盖即可。</font>

**<font style="color:rgb(26, 28, 30);">Q2: 点击按钮没反应，控制台报错 404？</font>**

+ **<font style="color:rgb(26, 28, 30);">原因</font>**<font style="color:rgb(26, 28, 30);">：后端没启动，或者后端接口路径不是</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">/api/review</font><font style="color:rgb(26, 28, 30);">。</font>
+ **<font style="color:rgb(26, 28, 30);">解决</font>**<font style="color:rgb(26, 28, 30);">：检查 Controller 里的</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">@RequestMapping</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">地址。</font>

**<font style="color:rgb(26, 28, 30);">Q3: AI 回复全是乱码？</font>**

+ **<font style="color:rgb(26, 28, 30);">原因</font>**<font style="color:rgb(26, 28, 30);">：解码器问题。</font>
+ **<font style="color:rgb(26, 28, 30);">解决</font>**<font style="color:rgb(26, 28, 30);">：确保使用了 </font><font style="color:rgb(50, 48, 44);">new TextDecoder().decode(value)</font><font style="color:rgb(26, 28, 30);">。</font>



> 更新: 2025-12-16 10:43:24  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/bpwr6gwq8vism8m2>