# Neuro Simulator

*关注Vedal喵，关注Vedal谢谢喵*

Neuro Simulator 通过调用Letta（一个为LLM添加自主记忆功能的项目），并调用其他LLM自动生成虚拟聊天，尝试模拟 Neuro-sama 和她的直播。

主要内容：
- 服务端
  - 调用配置好的Letta Agent
  - 根据Letta输出，调用Gemini或OpenAI API动态生成Chat并传入Letta
  - 调用微软Azure TTS合成语音
  - 允许多个客户端连接，向所有客户端广播内容
  - 在控制面板中更改和热重载部分配置、开关和重置直播状态
- 客户端
  - 模拟Twitch的直播界面，渲染Neuro-Sama的直播画面
  - 动态从服务端获取内容
  - 可设置的用户头像名称与服务端URL


## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/Neuro-Simulator.git
cd Neuro-Simulator
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

在 `backend` 目录下复制一份 `settings.yaml.example` 到 `settings.yaml` ，配置必要的 API 密钥和设置。
注意：API Key等敏感设置只能在 `settings.yaml` 中修改。

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
点击客户端界面右上角的头像可以修改一些客户端的设置。

---
*这个 README 是AI自动生成的，等项目真正完善后再认真修改一下。* 
