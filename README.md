# Neuro Simulator

*关注Vedal喵，关注Vedal谢谢喵*

*本临时README由AI自动生成*

Neuro Simulator 是一个基于AI的虚拟主播模拟器，通过调用 Letta（一个为 LLM 添加自主记忆功能的项目）以及其他 LLM 服务，模拟 Neuro-sama 的直播体验。它能生成实时的虚拟聊天内容，并通过 TTS 合成语音，提供沉浸式的观看体验。

## 特性

### 预览
<img src="start.gif" width="500" /> 

### 服务端

- **多 LLM 支持**：支持 Gemini 和 OpenAI API，动态生成聊天内容
- **多客户端支持**：支持多个客户端连接，实时广播内容
- **配置热重载**：通过 Web 控制面板修改和热重载配置
- **外部控制**：完全使用外部API端点操控服务端运行

### 客户端

- **用户交互**：支持观众发送聊天消息
- **个性化设置**：可自定义用户头像和名称

### Web控制面板

- **Web 管理界面**：独立部署的控制面板，方便管理不同的后端服务
- **连接管理**：连接到任意一个可访问的后端实例
- **配置管理**：查看、修改和热重载配置
- **日志监控**：实时查看后端日志

## 项目结构

```
Neuro-Simulator/
├── backend/           # 服务端
├── frontend_twitch/   # 客户端
├── dashboard_web/     # Web控制面板
└── README.md          # 项目说明文档
```

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/Neuro-Simulator.git
cd Neuro-Simulator
```

### 2. 服务端设置

a. **创建并激活虚拟环境**

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

b. **安装 Python 依赖**

```bash
pip install -r requirements.txt
```

c. **调整配置内容**

在 `backend` 目录下复制一份 `settings.yaml.example` 到 `settings.yaml`，配置必要的 API 密钥和设置：

```bash
cp settings.yaml.example settings.yaml
```

然后编辑 `settings.yaml` 文件，填入所需的 API 密钥和配置项。

注意：API Key 等敏感设置只能在 `settings.yaml` 中修改，外部控制面板中无法编辑。

d. **启动服务端**

目前只能使用 uvicorn：

```bash
uvicorn main:app
```

服务端将默认在 `http://127.0.0.1:8000` 上运行。

### 3. 客户端设置

a. **安装 Node.js 依赖**

```bash
cd frontend_twitch
npm install
```

b. **启动客户端开发服务器**

```bash
npm run dev
```

这将启动 Vite 开发服务器，默认在 `http://localhost:5173` 上运行。

c. **构建生产版本**

```bash
npm run build
```

这将使用 Vite 编译一个可部署的生产版本。

点击客户端界面右上角的头像可以修改客户端设置，如后端 URL、用户名和头像等。

### 4. 控制面板部署

控制面板是一个纯静态 Web 应用，可以部署在任何支持静态文件托管的服务上：

```bash
cd dashboard_web
# 使用 Python 简单 HTTP 服务器
python -m http.server 8080
```

然后在浏览器中访问 `http://localhost:8080` 即可打开控制面板。

## 使用说明

1. 确保后服务端已正确配置并运行
2. 在客户端中设置正确的后端 URL
3. 通过控制面板启动直播进程

## 配置说明

服务端通过 `settings.yaml` 文件进行配置，主要包括：

- API 密钥（Letta、Gemini、OpenAI、Azure TTS）
- 直播元数据（标题、分类、标签）
- Neuro 行为设置
- 观众模拟设置
- 性能设置
- 服务器设置

详细配置项请参考 `settings.yaml.example` 文件。
