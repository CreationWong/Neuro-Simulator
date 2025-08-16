# Neuro-Simulator 控制面板

*本临时README由AI自动生成*

这是一个独立部署的 Web 控制面板，用于管理 Neuro Simulator 服务端
通过这个面板，你可以方便地控制直播进程、管理配置和监控日志

## 功能特性

1. **连接管理**
   - 可连接到任意部署的 Neuro Simulator 服务端
   - 支持带密码认证的连接
   - 可随时断开连接

2. **直播控制**
   - 启动/停止/重启直播进程
   - 实时显示直播状态

3. **配置管理**
   - 获取当前配置
   - 修改并保存配置
   - 热重载配置

4. **日志监控**
   - 实时查看后端日志
   - 可调整日志显示行数
   - 支持手动刷新日志

5. **Agent管理**
   - 查看和管理Agent的记忆（初始化记忆、临时记忆、核心记忆）
   - 查看Agent的对话上下文历史
   - 查看Agent的日志
   - 管理Agent的工具

## 目录结构

```
dashboard_web/
├── index.html       # 主页面
├── css/
│   └── style.css    # 样式文件
├── js/
│   └── main.js      # 主要 JavaScript 代码
├── assets/
│   └── favicon.ico  # 网站图标
└── README.md        # 说明文档
```

## 部署方式

这是一个纯静态 Web 应用，可以部署在任何支持静态文件托管的服务上：

1. **Nginx 部署**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           root /path/to/dashboard_web;
           index index.html;
           try_files $uri $uri/ =404;
       }
   }
   ```

2. **Apache 部署**
   ```apache
   <VirtualHost *:80>
       ServerName your-domain.com
       DocumentRoot /path/to/dashboard_web;
       
       <Directory /path/to/dashboard_web>
           Options Indexes FollowSymLinks
           AllowOverride None
           Require all granted
       </Directory>
   </VirtualHost>
   ```

3. **Node.js 静态服务器**
   ```bash
   npm install -g serve
   serve -s /path/to/dashboard_web
   ```

4. **Python 简单 HTTP 服务器**
   ```bash
   cd /path/to/dashboard_web
   python -m http.server 8080
   ```

## 使用方法

1. 在浏览器中打开控制面板

2. 输入后端地址（例如：`http://localhost:8000` ）

3. 如果后端设置了 `API token` ，请在"访问密码"字段中输入

4. 点击"连接"按钮
   - 设置参数使用浏览器的 `LocalStorage` 进行持久存储

5. 连接成功后即可使用各项功能：
   - 在"控制"标签页中管理直播进程
   - 在"配置"标签页中修改配置
   - 在"日志"标签页中查看实时日志

## 配置后端 API Token

在后端的 `config.yaml` 文件中，找到 `server` 部分并设置 `panel_password` 字段：

```yaml
server:
  host: "127.0.0.1"
  port: 8000
  panel_password: "your-secret-api-token-here"  # 设置你的 API token
  client_origins:
    - "http://localhost:5173"
    - "http://127.0.0.1:5173"
```

另外，如果面板和服务端不能用 `localhost` 互相连通，请记得在 `client_origins` 中添加控制面板的地址

如果想偷懒，可以设置为：

```yaml
  panel_password: ""
  client_origins:
    - "*"
```

在这种情况下，请自行确保服务器安全，强烈建议仅用于纯内网乃至本机部署

## 安全说明

1. 控制面板通过 `API token` 进行身份验证
2. 敏感配置项（如 API 密钥）不会通过面板暴露
3. 建议在生产环境中使用 `HTTPS` 部署控制面板

## 界面说明

### 连接标签页
- 后端地址：输入后端服务的 `URL`
- 访问密码：输入后端设置的 `API token` （如果有的话）
- 点击按钮执行连接/断开连接操作

### 控制标签页
- 显示当前直播状态
- 启动/停止/重启直播按钮

### 配置标签页
- 显示和修改可配置选项
- 包括直播元数据、Neuro 行为设置、观众模拟设置和性能设置
- 点击按钮执行重置和保存配置操作
  - 保存配置时会自动执行热重载

### 日志标签页
- 实时显示后端日志
- 可选择显示日志行数
- 刷新日志按钮

### Agent管理标签页
- **对话上下文**：查看Agent的对话历史记录
- **记忆管理**：
  - 初始记忆：查看和编辑Agent的初始记忆
  - 临时记忆：查看、添加和清空Agent的临时记忆
  - 核心记忆：查看、添加、编辑和删除Agent的核心记忆块
- **工具管理**：查看Agent可用的工具列表
- **Agent日志**：查看Agent的详细日志信息

## 故障排除

1. 确保后端服务已启动并可访问
2. 检查网络连接是否正常
3. 验证后端地址和 `API token` 是否正确
4. 如果使用 `HTTPS` 部署控制面板，请确保后端也使用 `HTTPS`
5. 检查浏览器控制台获取错误信息

*作为看这篇💩文档的奖励，可以直接使用我部署的 https://dashboard.neuro.jiahui.cafe 连接到你的服务端，但是不保证始终能用，而且请配置好server的 `CORS`*
