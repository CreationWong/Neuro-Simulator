# Neuro-Simulator 服务端

*本临时README由AI自动生成*

这是 Neuro Simulator 的服务端，负责处理直播逻辑、AI 交互、TTS 合成等核心功能。

## 功能特性

- **动态观众**：调用无状态LLM，动态生成观众聊天内容，支持 Gemini 和 OpenAI API
- **配置管理**：支持通过 API 动态修改和热重载配置
- **外部控制**：完全使用外部API端点操控服务端运行

## 目录结构

``` main
neuro_simulator/
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
├── pyproject.toml       # Python 包安装配置
├── cli.py               # 命令行启动脚本
├── config.yaml.example # 自带的备用配置模板
└── media/               # 自带的备用媒体文件
    └── neuro_start.mp4  # 用来计算Start Soon长度，仅读取时长
```

``` workin'dir
working_dir_example/     # 工作目录结构，请将这个目录重命名和复制到你想要的位置（推荐放到~/.config/neuro-simulator）
├── media/               # 媒体文件夹，如缺失会使用自带资源覆盖
│   └── neuro_start.mp4  # 用来计算Start Soon长度，仅读取时长,请和客户端的视频保持一致
├── config.yaml        # 由用户手工创建的配置文件
└── config.yaml.example # 自动生成的配置文件模板，必须手动重命名和填写
```

## 安装与配置

0. **在运行server前，必须有已经配置完成的Letta Agent。**
1. 复制一份 `../docs/working_dir_example` 到你想要的位置，作为配置文件目录.
   - 程序会在未指定 `--dir` 的情况下自动生成一个工作目录，路径为 `~/.config/neuro-simulator/`
2. 然后进入配置文件目录，复制 `config.yaml.example` 到 `config.yaml`
3. 编辑 `config.yaml` 文件，填入必要的 API 密钥和配置项：
   - Letta Token 和 Agent ID
   - Gemini/OpenAI API Key
   - Azure TTS Key 和 Region

可以执行替换media/neuro_start.mp4为其它视频文件，但记得手动替换client中的同名文件。

### 直接安装方式（无需二次开发）

若无需二次开发，可以直接使用pip安装：
```bash
python3 -m venv venv
# Windows
venv/Scripts/pip install neuro-simulator
# macOS/Linux
venv/bin/pip install neuro-simulator
```

### 二次开发方式

若需要二次开发，请克隆项目，在server下建立venv，然后pip install -e ./：
```bash
git clone https://github.com/your-username/Neuro-Simulator.git
cd Neuro-Simulator/server
python3 -m venv venv
# Windows
venv/Scripts/pip install -e .
# macOS/Linux
venv/bin/pip install -e .
```

### 运行服务

```bash
# 使用默认配置 (位于~/.config/neuro-simulator/)
neuro

# 指定工作目录
neuro -D /path/to/your/config

# 指定主机和端口
neuro -H 0.0.0.0 -P 8080

# 组合使用
neuro -D /path/to/your/config -H 0.0.0.0 -P 8080
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

配置文件 `config.yaml` 包含以下主要配置项：

- `api_keys` - 各种服务的 API 密钥
- `stream_metadata` - 直播元数据（标题、分类、标签等）
- `neuro_behavior` - Neuro 行为设置
- `audience_simulation` - 观众模拟设置
- `tts` - TTS 语音合成设置
- `performance` - 性能相关设置
- `server` - 服务器设置（主机、端口、CORS 等）

有关配置文件的完整示例，请参阅项目根目录下的 `docs/working_dir_example/` 文件夹。

## 安全说明

1. 通过 `panel_password` 配置项可以设置控制面板访问密码
2. 敏感配置项（如 API 密钥）不会通过 API 接口暴露
3. 支持 CORS，仅允许预配置的来源访问

## 故障排除

- 确保所有必需的 API 密钥都已正确配置
- 检查网络连接是否正常
- 查看日志文件获取错误信息
- 确保端口未被其他程序占用 
