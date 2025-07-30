# Neuro-Sama 模拟器Web控制面板

这是一个独立的Web控制面板，用于管理Neuro-Sama模拟器后端服务。

## 功能特性

1. **连接管理**
   - 可连接到任意部署的Neuro-Sama后端实例
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

## 部署方式

这是一个纯静态Web应用，可以部署在任何支持静态文件托管的服务上：

1. **Nginx部署**
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

2. **Apache部署**
   ```apache
   <VirtualHost *:80>
       ServerName your-domain.com
       DocumentRoot /path/to/dashboard_web
       
       <Directory /path/to/dashboard_web>
           Options Indexes FollowSymLinks
           AllowOverride None
           Require all granted
       </Directory>
   </VirtualHost>
   ```

3. **Node.js静态服务器**
   ```bash
   npm install -g serve
   serve -s /path/to/dashboard_web
   ```

4. **Python简单HTTP服务器**
   ```bash
   cd /path/to/dashboard_web
   python -m http.server 8080
   ```

## 使用方法

1. 在浏览器中打开控制面板
2. 输入后端地址（例如：http://localhost:8000）
3. 如果后端设置了API token，在"访问密码"字段中输入该token
4. 点击"连接"按钮
5. 连接成功后即可使用各项功能

## 配置后端API Token

在后端的`settings.yaml`文件中，找到`server`部分并设置`panel_password`字段：

```yaml
server:
  host: "127.0.0.1"
  port: 8000
  panel_password: "your-secret-api-token-here"  # 设置你的API token
  client_origins:
    - "http://localhost:5173"
    - "http://127.0.0.1:5173"
```

## 开发说明

项目结构：
```
dashboard_web/
├── index.html          # 主页面
├── css/
│   └── style.css       # 样式文件
├── js/
│   └── main.js         # 主要JavaScript逻辑
└── assets/
    └── favicon.ico     # 网站图标
```

主要技术栈：
- 原生HTML/CSS/JavaScript
- Fetch API用于HTTP请求
- WebSocket用于实时日志
- 无外部依赖库

## 注意事项

1. 确保后端服务已启动并可访问
2. 如果使用HTTPS部署控制面板，请确保后端也使用HTTPS，避免混合内容问题
3. 控制面板与后端之间需要网络连通性