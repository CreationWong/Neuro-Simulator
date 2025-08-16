# Neuro Simulator

***关注Vedal喵，关注Vedal谢谢喵***

*本临时README和所有代码均由AI生成*

Neuro Simulator 是一个模拟 Neuro-sama 直播的项目
它通过调用 Letta（一个为 LLM 添加自主记忆功能的项目）以及其他 LLM 服务，也可使用自带的有记忆 Agent，模拟一场 Neuro-sama 的单人直播
它能生成实时的虚拟聊天内容，并通过 TTS 合成语音，提供沉浸式的 Twitch vedal987 频道观看体验

## 特性

### 预览

*这图是较旧版本的，现在小牛已经和现实中一样换新家了*

演示视频：[哔哩哔哩](https://www.bilibili.com/video/BV1Aot4zTEwt)

<img src="docs/assets/start.gif" width="500" />

### 核心亮点

- **多客户端支持**：支持多个客户端连接，实时广播内容
- **配置热重载**：通过 Web 控制面板修改和热重载配置
- **双 Agent 模式**：支持 Letta Agent 和内建 Agent，提供更多自定义选项
- **Agent 记忆管理**：内建 Agent 支持多种记忆类型（初始化记忆、核心记忆、临时记忆、上下文）

## 快速开始

1.  **准备外部服务**：确保你拥有必要的 API 密钥，包括 LLM（Gemini/OpenAI）和 Azure TTS；如果使用 Letta，也请注册好相关的 API
2.  **安装服务端**：
    ```bash
    pip install neuro-simulator
    ```
3.  **运行服务端**：
    ```bash
    neuro
    ```
    记得填写好配置目录中的 `config.yaml`
      - 不指定 `--dir` 则自动创建和默认使用 `~/.config/neuro-simulator/` 作为工作目录
      - 在默认或指定目录及需要的文件不存在时，程序会自动用自带模板复制一份到工作目录下

4.  **安装客户端**：
    ```bash
    cd client
    npm install
    ```
5.  **运行客户端**：
    ```bash
    npm run dev
    ```
6.  **部署控制面板**：
    ```bash
    cd dashboard_web
    python -m http.server 8080
    ```

更多更复杂或者更简单的使用方式，请参见三个部分的详细文档

## 项目结构

```
Neuro-Simulator/
├── server/           # 服务端
├── client/           # 客户端
├── dashboard_web/    # Web控制面板
├── docs/             # 文档和示例文件
│   ├── letta_agents_example/  # Letta Agent 模板示例
│   ├── assets/       # README中使用的媒体文件
│   └── working_dir_example/   # 工作目录示例
└── README.md         # 项目说明文档
```

## 详细文档

有关安装、配置和使用的详细信息，请参阅详细的 README 文件：

- [服务端 README](server/README.md)
- [客户端 README](client/README.md)
- [控制面板 README](dashboard_web/README.md)

## 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进项目，虽然大概率会是 Gemini 2.5 或者 Qwen Coder 来处理🤣