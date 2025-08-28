# Neuro-Simulator 服务端

*本临时README由AI自动生成*

这是 Neuro Simulator 的服务端，负责处理直播逻辑、AI 交互、TTS 合成等核心功能

## 功能特性

- **动态观众**：调用无状态LLM，动态生成观众聊天内容，支持 Gemini 和 OpenAI API
- **配置管理**：支持通过 API 动态修改和热重载配置
- **外部控制**：完全使用外部API端点操控服务端运行

## 目录结构

``` main
neuro_simulator/
├── __init__.py
├── cli.py               # 命令行启动脚本
├── agent/
│   ├── __init__.py
│   ├── core.py
│   ├── llm.py
│   ├── memory_prompt.txt
│   ├── neuro_prompt.txt
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── chat_history.json
│   │   ├── core_memory.json
│   │   ├── init_memory.json
│   │   ├── manager.py
│   │   └── temp_memory.json
│   └── tools/
│       └── ...
├── api/
│   ├── __init__.py
│   └── system.py
├── assets/
│   └── neuro_start.mp4
├── core/
│   ├── __init__.py
│   ├── agent_factory.py
│   ├── agent_interface.py
│   ├── application.py
│   ├── config.py
│   ├── config.yaml.example
│   └── path_manager.py
├── services/
│   ├── __init__.py
│   ├── audience.py
│   ├── audio.py
│   ├── builtin.py
│   ├── letta.py
│   └── stream.py
└── utils/
    ├── __init__.py
    ├── logging.py
    ├── process.py
    ├── queue.py
    ├── state.py
    └── websocket.py
```

``` workin'dir
working_dir_example/     # 工作目录结构，请将这个目录重命名和复制到你想要的位置（推荐放到~/.config/neuro-simulator）
├── assets/              # 媒体文件夹，如缺失会使用自带资源覆盖
│   └── neuro_start.mp4  # 用来计算Start Soon长度，仅读取时长,请和客户端的视频保持一致
├── config.yaml          # 由用户手工创建的配置文件
├── config.yaml.example  # 自动生成的配置文件模板，必须手动重命名和填写
└── agents/              # Agent相关文件夹
    ├── memories/        # Agent记忆文件夹
    │   ├── core_memory.json
    │   ├── init_memory.json
    │   └── temp_memory.json
    ├── memory_manager/  # 记忆管理器Agent
    │   ├── history.jsonl
    │   ├── memory_prompt.txt
    │   └── tools.json
    ├── neuro/           # Neuro主Agent
    │   ├── history.jsonl
    │   ├── neuro_prompt.txt
    │   └── tools.json
    └── tools/           # Agent工具文件夹
        └── builtin_tools/
```

## 安装与配置

1. 复制一份 `../docs/working_dir_example` 到你想要的位置，作为配置文件目录.
   - 程序会在未指定 `--dir` 的情况下自动生成一个工作目录，路径为 `~/.config/neuro-simulator/`
2. 然后进入配置文件目录，复制 `config.yaml.example` 到 `config.yaml`
3. 编辑 `config.yaml` 文件，填入必要的 API 密钥和配置项：
   - 如果使用 Letta Agent，需要配置 Letta Token 和 Agent ID
   - Gemini/OpenAI API Key（用于观众聊天生成和 Agent）
   - Azure TTS Key 和 Region

可以自行替换 `$dir/assets/neuro_start.mp4` 为其它视频文件，但记得手动替换 client 中的同名文件

### Agent配置

服务端支持两种Agent类型：
1. **Letta Agent**：需要配置 Letta Cloud 或自托管的 Letta Server
2. **内建 Agent**：使用服务端自带的 Agent，支持 Gemini 和OpenAI API

在 `config.yaml` 中通过 `agent_type` 字段选择使用的 Agent 类型：
- `agent_type: "letta"`：使用 Letta Agent
- `agent_type: "builtin"`：使用内建 Agent

当使用内建Agent时，还需要配置：
- `agent.agent_provider`：选择"gemini"或"openai"
- `agent.agent_model`：指定具体的模型名称

### 直接安装方式（无需二次开发）

若无需二次开发，可以直接使用 pip 安装：
```bash
python3 -m venv venv
# Windows
venv/Scripts/pip install neuro-simulator
# macOS/Linux
venv/bin/pip install neuro-simulator
```

### 二次开发方式

若需要二次开发，请克隆项目：
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

服务默认运行在 `http://127.0.0.1:8000`

## API 接口

服务端的主要管理和控制功能已统一迁移至 WebSocket 接口 `/ws/admin`。原有的 HTTP API 仅保留 `/api/system/health` 用于建立 WS 连接前的健康检查

- `/ws/admin`: 用于控制面板的管理接口，提供直播控制、配置管理、日志监控、Agent交互等所有功能，详细规范请参阅 `WEBSOCKET_API.md`
- `/ws/stream`: 客户端使用的直播接口
- `/api/system/health`: 健康检查接口
- `/docs`: 自动生成的API文档 (Swagger UI)

## 配置说明

配置文件 `config.yaml` 包含以下主要配置项：

- `api_keys` - 各种服务的 API 密钥
- `stream_metadata` - 直播元数据（标题、分类、标签等）
- `neuro_behavior` - Neuro 行为设置
- `audience_simulation` - 观众模拟设置
- `tts` - TTS 语音合成设置
- `performance` - 性能相关设置
- `server` - 服务器设置（主机、端口、CORS 等）

有关配置文件的完整示例，请参阅项目根目录下的 `docs/working_dir_example/` 文件夹

## 安全说明

1. 通过 `panel_password` 配置项可以设置控制面板访问密码
2. 敏感配置项（如 API 密钥）不会通过 API 接口暴露
3. 支持 CORS，仅允许预配置的来源访问

## 故障排除

- 确保所有必需的 API 密钥都已正确配置
- 检查网络连接是否正常
- 查看日志文件获取错误信息
- 确保端口未被其他程序占用
