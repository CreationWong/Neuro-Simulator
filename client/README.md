# Neuro Simulator 客户端

*本临时README由AI自动生成*

这是 Neuro Simulator 的客户端，采用 Twitch 风格的界面设计，为用户提供沉浸式的虚拟主播观看体验

## 目录结构

```
frontend_twitch/
├── index.html          # 主页面
├── package.json        # 项目依赖和脚本
├── vite.config.ts      # Vite 配置文件
├── tsconfig.json       # TypeScript 配置
├── public/             # 静态资源目录
│   ├── avatar.webp     # 默认用户头像
│   ├── background.webp # 背景图片
│   ├── neurosama.png   # Neuro-Sama 头像
│   └── fonts/          # 字体文件
├── src/                # 源代码目录
│   ├── main.ts         # 应用入口
│   ├── style.css       # 全局样式
│   ├── core/           # 核心模块
│   ├── services/       # 服务模块
│   ├── stream/         # 直播相关组件
│   ├── styles/         # 样式文件
│   ├── types/          # TypeScript 类型定义
│   ├── ui/             # UI 组件
│   └── utils/          # 工具函数
└── dist/               # 构建输出目录
```

## 安装与开发

### 直接使用（无需二次开发）

若无需二次开发，可以直接在浏览器中打开 `<http协议>://<服务端地址>/` 使用服务端托管的客户端。
- 每一个客户端页面在浏览器中都是独立运行的，因此如果有多个观众，访问同一个地址即可。

如果硬盘空间太大/电脑里垃圾太少/想要自己独立托管客户端对外服务（这是好习惯，避免暴露服务端地址），可以直接从 `Releases` 下载和使用编译好的文件（仅支持Win/Linux/Web托管）

### 二次开发

若需要二次开发，请克隆项目：
```bash
git clone https://github.com/your-username/Neuro-Simulator.git
cd Neuro-Simulator/client
npm install
```

### 运行开发服务器

```bash
npm run dev
# 或者使用Tauri开发模式
npm run tauri dev
```
开发服务器默认运行在 `http://localhost:5173`

### 构建生产版本

```bash
npm run build
# 或者使用Tauri构建
npm run tauri build
```
构建后的文件将输出到 `dist/` 目录

### 预览生产构建

```bash
npm run preview
```

## 代码结构说明

### 核心模块 (src/core/)

- `appInitializer.ts` - 应用初始化器，负责协调各组件
- `layoutManager.ts` - 页面布局管理器
- `singletonManager.ts` - 单例管理器

### 服务模块 (src/services/)

- `websocketClient.ts` - WebSocket 客户端实现
- `audioPlayer.ts` - 音频播放器
- `apiClient.ts` - HTTP API 客户端

### 直播组件 (src/stream/)

- `neuroAvatar.ts` - Neuro-Sama 头像动画控制
- `videoPlayer.ts` - 视频播放器

### UI 组件 (src/ui/)

- `chatDisplay.ts` - 聊天消息显示
- `chatSidebar.ts` - 聊天侧边栏
- `liveIndicator.ts` - 直播状态指示器
- `muteButton.ts` - 静音按钮
- `neuroCaption.ts` - Neuro 字幕显示
- `settingsModal.ts` - 设置模态框
- `streamInfoDisplay.ts` - 直播信息显示
- `streamTimer.ts` - 直播计时器
- `userInput.ts` - 用户输入框

### 工具函数 (src/utils/)

- `wakeLockManager.ts` - 屏幕常亮管理

## 配置说明

用户可以通过点击界面右上角的头像打开设置来配置：

- 后端服务 URL
- 用户名
- 用户头像
- 重连尝试次数

设置参数使用浏览器的 `LocalStorage` 进行持久存储

当客户端由服务端托管时，会尝试自动连接到服务端，一般无需设置

## 哔哩哔哩直播回放

客户端现在支持从哔哩哔哩动态拉取最新的直播回放视频。由于B站的 API 相关限制，需要通过代理来访问。

- **Tauri 桌面端**: 客户端已内置反向代理，无需额外配置。
- **Vite 开发服务器**: 在 `vite.config.ts` 中已经配置了代理，开发时可直接使用。
- **Web 部署**: 如果您将此项目构建为静态网站并部署到自己的服务器，则需要手动配置反向代理。

以下是一个 Nginx 的反向代理配置示例：

```nginx
location /bilibili-api/ {
    rewrite ^/bilibili-api/(.*)$ /$1 break;
    proxy_pass https://api.bilibili.com/;
    proxy_set_header Host api.bilibili.com;
    proxy_set_header Referer https://www.bilibili.com/;
    proxy_set_header Origin https://www.bilibili.com;
    # 如果遇到412错误，可以尝试移除或修改User-Agent
    proxy_set_header User-Agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36';
}
```

## 故障排除

- 确保后端服务正在运行且可访问
- 检查浏览器控制台获取错误信息
- 确认 `WebSocket` 连接状态
- 验证配置设置是否正确 

> 都是些 AI 生成的垃圾话，看看就好

*作为看这篇💩文档的奖励，可以直接使用我部署的 https://neuro.jiahui.cafe 连接到你的服务端，但是不保证始终能用，而且无法修改neuro_start.mp4*
