# Neuro Simulator

*关注Vedal喵，关注Vedal谢谢喵*

*本临时README由AI自动生成*

Neuro Simulator 通过调用 Letta（一个为 LLM 添加自主记忆功能的项目）以及其他 LLM 服务，模拟一场 Neuro-sama 的单人直播。它能生成实时的虚拟聊天内容，并通过 TTS 合成语音，提供沉浸式的观看体验。

## 特性

### 预览
<img src="docs/medias/start.gif" width="500" /> 

### 服务端

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
├── server/           # 服务端
├── client/           # 客户端
├── dashboard_web/    # Web控制面板
├── docs/             # 文档和示例文件
│   ├── letta_agents_example/  # Letta Agent 模板示例
│   ├── medias/       # README中使用的媒体文件
│   └── working_dir_example/   # 工作目录示例
└── README.md         # 项目说明文档
```

## 安装与运行

### 0. 准备外部服务

为了运行本项目，你至少需要拥有这些外部服务的API资源：
- Letta Cloud或自托管的Letta Server，以及在其中配置完毕的Agent，作为本项目的核心
  - 官方文档：https://docs.letta.com/
  - Agent配置示例：参见./docs/letta_agents_example/
- Gemini或兼容OpenAI API的LLM服务商，这一项除了被本项目的Chatbot调用外，也可在Letta中使用，具体参考Letta文档
  - Letta文档中关于自定义LLM的说明：https://docs.letta.com/connecting-model-providers/
  - 推荐使用SiliconFlow，规模9B以下模型不限量免费调用：https://cloud.siliconflow.cn/i/lnHouO6z
- Azure语音服务API，作为本项目TTS的唯一来源
  - 注册免费层F0即可，每月额度0.5M字符：https://azure.microsoft.com/products/ai-services/ai-speech/

### 1. 服务端安装

**若无需二次开发，可以直接使用pip安装：**
```bash
python3 -m venv venv
# Windows
venv/Scripts/pip install neuro-simulator
# macOS/Linux
venv/bin/pip install neuro-simulator
```

**若需要二次开发，请克隆项目：**
```bash
git clone https://github.com/your-username/Neuro-Simulator.git
cd Neuro-Simulator/server
python3 -m venv venv
# Windows
venv/Scripts/pip install -e .
# macOS/Linux
venv/bin/pip install -e .
```

### 2. 运行服务端

```bash
# 使用默认配置 (~/.config/neuro-simulator/)
neuro

# 指定工作目录
neuro -D /path/to/your/config

# 指定主机和端口
neuro -H 0.0.0.0 -P 8080

# 组合使用
neuro -D /path/to/your/config -H 0.0.0.0 -P 8080
```

服务默认运行在 `http://127.0.0.1:8000`。

### 3. 客户端安装

**若无需二次开发，可以直接从Releases中下载（仅支持Win/Linux）**

**若需要二次开发，请克隆项目：**
```bash
git clone https://github.com/your-username/Neuro-Simulator.git
cd Neuro-Simulator/client
npm install
```

### 4. 运行客户端

**开发模式：**
```bash
npm run dev
# 或者使用Tauri开发模式
npm run tauri dev
```

这将启动 Vite 开发服务器，默认在 `http://localhost:5173` 上运行。

**构建生产版本：**
```bash
npm run build
# 或者使用Tauri构建
npm run tauri build
```

点击客户端界面右上角的头像可以修改客户端设置，如后端 URL、用户名和头像等。

### 5. 控制面板部署

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

此外，你可以在 `docs/working_dir_example/` 目录中找到一个完整的工作目录示例，包括推荐的目录结构和配置文件模板。
