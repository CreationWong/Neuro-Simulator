# Neuro Simulator 前端客户端

*关注Vedal喵，关注Vedal谢谢喵*

*本临时README由AI自动生成*

这是 Neuro Simulator 的前端客户端，采用 Twitch 风格的界面设计，为用户提供沉浸式的虚拟主播观看体验。

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

1. **安装依赖**
   ```bash
   npm install
   ```

2. **启动开发服务器**
   ```bash
   npm run dev
   ```
   开发服务器默认运行在 `http://localhost:5173`

3. **构建生产版本**
   ```bash
   npm run build
   ```
   构建后的文件将输出到 `dist/` 目录

4. **预览生产构建**
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

设置参数使用浏览器的LocalStorage进行持久存储

## 故障排除

- 确保后端服务正在运行且可访问
- 检查浏览器控制台获取错误信息
- 确认 WebSocket 连接状态
- 验证配置设置是否正确 
