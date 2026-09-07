# 第 1 集 AI Code Reviewer 环境配置

### <font style="color:rgb(26, 28, 30);">. 安装 JDK 21 (必须步骤)</font>
<font style="color:rgb(26, 28, 30);">Spring AI 强依赖 JDK 17+，推荐使用 JDK 21 (LTS)。</font>

#### <font style="color:rgb(26, 28, 30);">🍎</font><font style="color:rgb(26, 28, 30);"> macOS 用户 (推荐 Homebrew)</font>
<font style="color:rgb(26, 28, 30);">打开终端 (Terminal)，依次执行：</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Bash</font>**

```plain
# 1. 安装 JDK 21
brew install openjdk@21

# 2. 配置系统软连接 (关键！解决 Cursor 找不到 JDK 的问题)
sudo ln -sfn /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-21.jdk

# 3. 配置环境变量 (以 zsh 为例)
echo 'export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 4. 验证
java -version
# 输出应包含: openjdk version "21.0.9" ...
```

#### <font style="color:rgb(26, 28, 30);">🪟</font><font style="color:rgb(26, 28, 30);"> Windows 用户</font>
+ **<font style="color:rgb(26, 28, 30);">下载</font>**<font style="color:rgb(26, 28, 30);">：访问</font><font style="color:rgb(26, 28, 30);"> </font>[<font style="color:rgb(36, 131, 226);">Oracle 官网</font>](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.oracle.com%2Fjava%2Ftechnologies%2Fdownloads%2F%23jdk21-windows)<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">下载</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">x64 Installer</font><font style="color:rgb(26, 28, 30);">。</font>
+ **<font style="color:rgb(26, 28, 30);">安装</font>**<font style="color:rgb(26, 28, 30);">：双击运行，一路点击“下一步”。</font>
+ **<font style="color:rgb(26, 28, 30);">验证</font>**<font style="color:rgb(26, 28, 30);">：打开 CMD (命令提示符)，输入</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">java -version</font><font style="color:rgb(26, 28, 30);">。</font>

---

### <font style="color:rgb(26, 28, 30);">2. 安装与配置 Maven</font>
#### <font style="color:rgb(26, 28, 30);">🍎</font><font style="color:rgb(26, 28, 30);"> macOS 用户</font>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Bash</font>**

```plain
brew install maven
# 验证
mvn -v
```

#### <font style="color:rgb(26, 28, 30);">🪟</font><font style="color:rgb(26, 28, 30);"> Windows 用户</font>
+ <font style="color:rgb(26, 28, 30);">下载 Maven zip 包解压。</font>
+ <font style="color:rgb(26, 28, 30);">配置环境变量</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">MAVEN_HOME</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">指向解压目录。</font>
+ <font style="color:rgb(26, 28, 30);">将</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">%MAVEN_HOME%\bin</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">添加到 Path 中。</font>

#### <font style="color:rgb(26, 28, 30);">🚀</font><font style="color:rgb(26, 28, 30);"> 加速技巧 (阿里云镜像)</font>
<font style="color:rgb(26, 28, 30);">为了防止依赖下载卡死，建议修改</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">settings.xml</font><font style="color:rgb(26, 28, 30);">。</font>

+ **<font style="color:rgb(26, 28, 30);">Mac 位置</font>**<font style="color:rgb(26, 28, 30);">:</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">/opt/homebrew/opt/maven/libexec/conf/settings.xml</font>
+ **<font style="color:rgb(26, 28, 30);">Windows 位置</font>**<font style="color:rgb(26, 28, 30);">:</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">Maven安装目录/conf/settings.xml</font>

<font style="color:rgb(26, 28, 30);">在</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);"><mirrors></font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">标签内添加：</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Xml</font>**

```plain
<mirror>
  <id>aliyunmaven</id>
  <mirrorOf>central</mirrorOf>
  <name>Aliyun Public</name>
  <url>https://maven.aliyun.com/repository/public</url>
</mirror>
```

---

### <font style="color:rgb(26, 28, 30);">3. 获取阿里云百炼 API Key (大模型大脑)</font>
<font style="color:rgb(26, 28, 30);">我们需要获取一个 Key 来调用通义千问模型。</font>

+ **<font style="color:rgb(26, 28, 30);">访问平台</font>**<font style="color:rgb(26, 28, 30);">：登录</font><font style="color:rgb(26, 28, 30);"> </font>[<font style="color:rgb(36, 131, 226);">阿里云百炼控制台</font>](https://www.google.com/url?sa=E&q=https%3A%2F%2Fbailian.console.aliyun.com%2F)<font style="color:rgb(26, 28, 30);">。</font>
+ **<font style="color:rgb(26, 28, 30);">开通服务</font>**<font style="color:rgb(26, 28, 30);">：点击“开通 DashScope”，新用户通常有免费额度。</font>
+ **<font style="color:rgb(26, 28, 30);">创建密钥</font>**<font style="color:rgb(26, 28, 30);">：</font>
    - <font style="color:rgb(26, 28, 30);">点击左侧菜单</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">“API-KEY 管理”</font>**<font style="color:rgb(26, 28, 30);">。</font>
    - <font style="color:rgb(26, 28, 30);">点击</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">“创建新的 API-KEY”</font>**<font style="color:rgb(26, 28, 30);">。</font>
    - **<font style="color:rgb(26, 28, 30);">复制保存</font>**<font style="color:rgb(26, 28, 30);">：</font><font style="color:rgb(50, 48, 44);">sk-xxxxxxxxxxxx</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(关掉弹窗后就看不到了，务必保存到记事本)。</font>

---

### <font style="color:rgb(26, 28, 30);">4. 配置 Cursor (开发神器)</font>
+ **<font style="color:rgb(26, 28, 30);">下载</font>**<font style="color:rgb(26, 28, 30);">：</font>[<font style="color:rgb(36, 131, 226);">Cursor 官网</font>](https://www.google.com/url?sa=E&q=https%3A%2F%2Fcursor.sh%2F)<font style="color:rgb(26, 28, 30);">。</font>
+ **<font style="color:rgb(26, 28, 30);">安装插件</font>**<font style="color:rgb(26, 28, 30);">：</font>
    - <font style="color:rgb(26, 28, 30);">打开 Cursor。</font>
    - <font style="color:rgb(26, 28, 30);">点击左侧边栏的</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">Extensions</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(扩展)。</font>
    - <font style="color:rgb(26, 28, 30);">搜索</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">"Java"</font>**<font style="color:rgb(26, 28, 30);">。</font>
    - <font style="color:rgb(26, 28, 30);">安装</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">"Extension Pack for Java"</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(Microsoft 出品)。</font>
+ **<font style="color:rgb(26, 28, 30);">验证</font>**<font style="color:rgb(26, 28, 30);">：</font>
    - <font style="color:rgb(26, 28, 30);">重启 Cursor。</font>
    - <font style="color:rgb(26, 28, 30);">新建一个 </font><font style="color:rgb(50, 48, 44);">.java</font><font style="color:rgb(26, 28, 30);"> 文件，看是否有代码高亮和智能提示。</font>



> 更新: 2025-12-16 10:42:20  
> 原文: <https://www.yuque.com/tulingzhouyu/db22bv/dmer9may1s3oyg8p>