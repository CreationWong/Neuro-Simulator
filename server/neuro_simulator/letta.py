# backend/letta.py
from letta_client import Letta, MessageCreate, TextContent, LlmConfig, AssistantMessage
from fastapi import HTTPException, status
from .config import config_manager

# 初始化 Letta 客户端
letta_client: Letta | None = None
try:
    if not config_manager.settings.api_keys.letta_token:
        raise ValueError("LETTA_API_TOKEN is not set. Cannot initialize Letta client.")
    
    # 使用 settings 对象进行配置
    client_args = {'token': config_manager.settings.api_keys.letta_token}
    if config_manager.settings.api_keys.letta_base_url:
        client_args['base_url'] = config_manager.settings.api_keys.letta_base_url
        print(f"Letta client is being initialized for self-hosted URL: {config_manager.settings.api_keys.letta_base_url}")
    else:
        print("Letta client is being initialized for Letta Cloud.")

    letta_client = Letta(**client_args)

    if config_manager.settings.api_keys.neuro_agent_id:
        try:
            agent_data = letta_client.agents.retrieve(agent_id=config_manager.settings.api_keys.neuro_agent_id)
            print(f"成功获取 Letta Agent 详情，ID: {agent_data.id}")
            llm_model_info = "N/A"
            if hasattr(agent_data, 'model') and agent_data.model:
                llm_model_info = agent_data.model
            elif agent_data.llm_config:
                if isinstance(agent_data.llm_config, LlmConfig):
                    llm_config_dict = agent_data.llm_config.model_dump() if hasattr(agent_data.llm_config, 'model_dump') else agent_data.llm_config.__dict__
                    llm_model_info = llm_config_dict.get('model_name') or llm_config_dict.get('name') or llm_config_dict.get('model')
                if not llm_model_info:
                    llm_model_info = str(agent_data.llm_config)
            print(f"  -> Agent 名称: {agent_data.name}")
            print(f"  -> LLM 模型: {llm_model_info}")

        except Exception as e:
            error_msg = f"错误: 无法获取 Neuro Letta Agent (ID: {config_manager.settings.api_keys.neuro_agent_id})。请确保 ID 正确，且服务可访问。详情: {e}"
            print(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
except Exception as e:
    print(f"初始化 Letta 客户端失败: {e}")
    letta_client = None

def get_letta_client():
    if letta_client is None: raise ValueError("Letta client is not initialized.")
    return letta_client

async def reset_neuro_agent_memory():
    """
    重置 Agent 的记忆，包括：
    1. 清空所有消息历史记录。
    2. 清空指定的 'conversation_summary' 核心内存块。
    """
    agent_id = config_manager.settings.api_keys.neuro_agent_id
    if letta_client is None or not agent_id: 
        print("Letta client 或 Agent ID 未配置，跳过重置。")
        return

    # --- 步骤 1: 重置消息历史记录 (上下文) ---
    try:
        letta_client.agents.messages.reset(agent_id=agent_id)
        print(f"Neuro Agent (ID: {agent_id}) 的消息历史已成功重置。")
    except Exception as e:
        print(f"警告: 重置 Agent 消息历史失败: {e}。")

    # --- 步骤 2: 清空 'conversation_summary' 核心内存块 ---
    block_label_to_clear = "conversation_summary"
    try:
        print(f"正在尝试清空核心记忆块: '{block_label_to_clear}'...")
        
        # 调用 modify 方法，将 value 设置为空字符串
        letta_client.agents.blocks.modify(
            agent_id=agent_id,
            block_label=block_label_to_clear,
            value="" 
        )
        
        print(f"核心记忆块 '{block_label_to_clear}' 已成功清空。")
    except Exception as e:
        # 优雅地处理块不存在的情况
        # API 在找不到块时通常会返回包含 404 或 "not found" 的错误
        error_str = str(e).lower()
        if "not found" in error_str or "404" in error_str:
             print(f"信息: 核心记忆块 '{block_label_to_clear}' 不存在，无需清空。")
        else:
             print(f"警告: 清空核心记忆块 '{block_label_to_clear}' 失败: {e}。")


async def get_neuro_response(chat_messages: list[dict]) -> str:
    if letta_client is None or not config_manager.settings.api_keys.neuro_agent_id:
        print("警告: Letta client 或 Agent ID 未配置，无法获取响应。")
        return "我暂时无法回应，请稍后再试。"

    if chat_messages:
        injected_chat_lines = [f"{chat['username']}: {chat['text']}" for chat in chat_messages]
        injected_chat_text = (
            "Here are some recent messages from my Twitch chat:\n---\n" + 
            "\n".join(injected_chat_lines) + 
            "\n---\nNow, as the streamer Neuro-Sama, please continue the conversation naturally."
        )
    else:
        injected_chat_text = "My chat is quiet right now. As Neuro-Sama, what should I say to engage them?"

    print(f"正在向 Neuro Agent 发送输入 (包含 {len(chat_messages)} 条消息)..." )

    try:
        response = letta_client.agents.messages.create(
            agent_id=config_manager.settings.api_keys.neuro_agent_id,
            messages=[MessageCreate(role="user", content=injected_chat_text)]
        )

        ai_full_response_text = ""
        if response and response.messages:
            last_message = response.messages[-1]
            if isinstance(last_message, AssistantMessage) and hasattr(last_message, 'content'):
                content = last_message.content
                if isinstance(content, str):
                    ai_full_response_text = content.strip()
                elif isinstance(content, list) and content:
                    first_part = content[0]
                    if isinstance(first_part, TextContent) and hasattr(first_part, 'text'):
                        ai_full_response_text = first_part.text.strip()
        
        if not ai_full_response_text:
            print(f"警告: 未能从 Letta 响应中解析出有效的文本。响应对象: {response}")
            return "I seem to be at a loss for words right now."

        print(f"成功从 Letta 解析到响应: '{ai_full_response_text[:70]}...'")
        return ai_full_response_text

    except Exception as e:
        print(f"错误: 调用 Letta Agent ({config_manager.settings.api_keys.neuro_agent_id}) 失败: {e}")
        return "Someone tell Vedal there is a problem with my AI."
