# Neuro Simulator

Neuro Simulator 是一个虚拟主播模拟器，结合了前端、后端和 Electron 桌面应用。它能够模拟虚拟主播 Neurosama 的直播场景，包括视频播放、聊天互动和语音合成等功能。

## 技术栈

**前端:**

*   [TypeScript](https://www.typescriptlang.org/)
*   [Vite](https://vitejs.dev/) - 前端构建工具
*   [Electron](https://www.electronjs.org/) - 跨平台桌面应用框架

**后端:**

*   [Python](https://www.python.org/)
*   [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架
*   [Uvicorn](https://www.uvicorn.org/) - ASGI 服务器
*   [Google Generative AI](https://ai.google/discover/generativeai/) - 用于聊天机器人功能
*   [Azure Cognitive Services](https://azure.microsoft.com/en-us/products/cognitive-services) - 用于语音合成

## 项目结构

```
neuro-simulator/
├── backend/            # Python FastAPI 后端服务
│   ├── main.py         # FastAPI 应用入口
│   ├── requirements.txt # Python 依赖
│   └── ...
├── electron/           # Electron 主进程和预加载脚本
│   ├── main.ts
│   └── preload.ts
├── src/                # 前端源代码 (TypeScript)
│   ├── main.ts         # 前端应用入口
│   └── ...
├── public/             # 静态资源
├── run_dev.bat         # Windows 开发环境一键启动脚本
├── package.json        # Node.js 依赖和项目脚本
└── ...
```

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/neuro-simulator.git
cd neuro-simulator
```

### 2. 后端设置

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

c. **配置环境变量**

在 `backend` 目录下创建一个 `.env` 文件，参照 `settings.yaml.example` 来配置必要的 API 密钥和设置，例如 Google AI 和 Azure 的凭据。

d. **启动后端服务**

```bash
uvicorn main:app --reload
```

后端服务将在 `http://127.0.0.1:8000` 上运行。

### 3. 前端设置

a. **安装 Node.js 依赖**

```bash
# 在项目根目录
npm install
```

b. **启动前端开发服务器**

```bash
npm run dev
```

这将启动 Vite 开发服务器和 Electron 应用。

### 4. (可选) Windows 一键启动

在 Windows 上，你可以直接运行根目录下的 `run_dev.bat` 脚本来同时启动前后端开发环境。

## 配置

应用的大部分配置都在 `backend/settings.yaml` 文件中（通过 `.env` 文件加载）。请确保在启动前根据 `settings.yaml.example` 文件创建并正确填写配置。

关键配置项包括：

*   Google AI API 密钥
*   Azure Speech Service 密钥和区域
*   Letta Client (如果使用)

---
*这个 README 是自动生成的。* 