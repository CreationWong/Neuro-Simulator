# Neuro-Simulator 服务端

*关注Vedal喵，关注Vedal谢谢喵*

*本临时README由AI自动生成*

这是 Neuro Simulator 的后端服务，基于 Python 和 FastAPI 构建，负责处理直播逻辑、AI 交互、TTS 合成等核心功能。

## 功能特性

- **多 LLM 支持**：支持 Gemini 和 OpenAI API，用于生成观众聊天内容
- **配置管理**：支持通过 API 动态修改和热重载配置
- **外部控制**：完全使用外部API端点操控服务端运行

## 目录结构

```
server/
├── main.py              # 应用入口和核心逻辑
├── config.py            # 配置管理模块
├── letta.py             # Letta Agent 集成
├── chatbot.py           # 观众聊天生成器
├── audio_synthesis.py   # 音频合成模块
├── stream_chat.py       # 聊天消息处理
├── stream_manager.py    # 直播管理器
├── websocket_manager.py # WebSocket 连接管理
├── process_manager.py   # 进程管理器
├── shared_state.py      # 全局状态管理
├── log_handler.py       # 日志处理模块
├── requirements.txt     # Python 依赖列表
├── settings.yaml.example # 配置文件模板
├── setup.py             # Python 包安装配置
├── neuro_cli.py         # 命令行接口脚本
└── media/               # 媒体文件目录
```

## 安装与配置

### 方法一：使用 pip 安装（推荐）

1. **安装包**
   ```bash
   pip install .
   ```

2. **运行服务**
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

### 方法二：传统方式运行

1. **创建并激活虚拟环境**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置设置**
   复制配置文件模板并根据需要进行修改：
   ```bash
   cp settings.yaml.example settings.yaml
   ```
   
   编辑 `settings.yaml` 文件，填入必要的 API 密钥和配置项：
   - Letta Token 和 Agent ID
   - Gemini/OpenAI API Key
   - Azure TTS Key 和 Region

4. **启动服务**
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```

服务默认运行在 `http://127.0.0.1:8000`。

## API 接口

后端提供丰富的 API 接口用于控制和管理：

- `/api/stream/*` - 直播控制接口（启动/停止/重启/状态）
- `/api/configs/*` - 配置管理接口（获取/更新/重载配置）
  - `api_keys` `server` 等敏感配置项无法从接口获取和修改。
- `/api/logs` - 日志获取接口
- `/api/tts/synthesize` - TTS 合成接口
- `/api/system/health` - 健康检查接口
- `/ws/stream` - 直播内容 WebSocket 接口
- `/ws/logs` - 日志流 WebSocket 接口

详细接口说明可通过 `http://127.0.0.1:8000/docs` 访问 API 文档查看。

## 配置说明

配置文件 `settings.yaml` 包含以下主要配置项：

- `api_keys` - 各种服务的 API 密钥
- `stream_metadata` - 直播元数据（标题、分类、标签等）
- `neuro_behavior` - Neuro 行为设置
- `audience_simulation` - 观众模拟设置
- `tts` - TTS 语音合成设置
- `performance` - 性能相关设置
- `server` - 服务器设置（主机、端口、CORS 等）

## 安全说明

1. 通过 `panel_password` 配置项可以设置控制面板访问密码
2. 敏感配置项（如 API 密钥）不会通过 API 接口暴露
3. 支持 CORS，但仅允许预配置的来源访问

## 故障排除

- 确保所有必需的 API 密钥都已正确配置
- 检查网络连接是否正常
- 查看日志文件获取错误信息
- 确保端口未被其他程序占用 
