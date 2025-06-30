# backend/letta.py
from letta_client import Letta, MessageCreate, TextContent, LlmConfig, AssistantMessage
from fastapi import HTTPException, status
# 从 config 模块导入 Letta 相关配置 (现在不导入 NEURO_AGENT_SYSTEM_PROMPT)
from config import LETTA_API_TOKEN, LETTA_BASE_URL, NEURO_AGENT_ID

# 初始化 Letta 客户端
letta_client: Letta | None = None
try:
    if not LETTA_API_TOKEN:
        print("Warning: LETTA_API_TOKEN is not set. Letta client might not function correctly.")
    if not LETTA_BASE_URL:
        raise ValueError("LETTA_BASE_URL is not set. Cannot initialize Letta client.")
    
    letta_client = Letta(token=LETTA_API_TOKEN, base_url=LETTA_BASE_URL)
    print(f"Letta client initialized with base URL: {LETTA_BASE_URL}")

    # 启动时检查 Neuro Agent 是否存在
    if NEURO_AGENT_ID:
        try:
            agent_data = letta_client.agents.retrieve(agent_id=NEURO_AGENT_ID)
            print(f"成功获取 Letta Agent 详情，ID: {agent_data.id}, 名称: {agent_data.name}")
            llm_model_info = "N/A"
            if hasattr(agent_data, 'model') and agent_data.model:
                llm_model_info = agent_data.model
            elif agent_data.llm_config:
                if isinstance(agent_data.llm_config, LlmConfig):
                    llm_config_dict = agent_data.llm_config.model_dump() if hasattr(agent_data.llm_config, 'model_dump') else agent_data.llm_config.__dict__
                    llm_model_info = llm_config_dict.get('model_name') or llm_config_dict.get('name') or llm_config_dict.get('model')
                if not llm_model_info:
                    llm_model_info = str(agent_data.llm_config)
            print(f"Neuro Agent 名称: {agent_data.name}, LLM 模型: {llm_model_info}")
            # 打印 Letta Agent 的 system_prompt，方便调试
            if hasattr(agent_data, 'system_prompt') and agent_data.system_prompt:
                print(f"Neuro Agent System Prompt: {agent_data.system_prompt[:100]}...") # 只打印前100字符
            else:
                print("Neuro Agent 没有配置 system_prompt。请在 Letta UI 或通过 API 设置。")


        except Exception as e:
            print(f"错误: 无法获取 Neuro Letta Agent (ID: {NEURO_AGENT_ID})。请确保 ID 正确，且 Letta 服务器正在运行并可访问。")
            print(f"详情: {e}")
            # 如果 Agent 无法获取，这通常是一个致命错误，应该阻止应用启动
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Neuro Agent {NEURO_AGENT_ID} 无法找到或访问: {e}")
except Exception as e:
    print(f"初始化 Letta 客户端失败: {e}")
    letta_client = None # 将 letta_client 设为 None，以便后续代码检查其可用性


def get_letta_client():
    """返回 Letta 客户端实例。"""
    if letta_client is None:
        raise ValueError("Letta client is not initialized.")
    return letta_client

async def reset_neuro_agent_memory():
    """重置 Neuro Agent 的记忆。"""
    if letta_client is None:
        print("Letta client not initialized, cannot reset agent memory.")
        return
    if not NEURO_AGENT_ID:
        print("NEURO_AGENT_ID not set, cannot reset agent memory.")
        return
    try:
        letta_client.agents.messages.reset(agent_id=NEURO_AGENT_ID)
        print(f"Neuro Agent {NEURO_AGENT_ID} 记忆已重置。")
    except Exception as e:
        print(f"警告: 重置 Neuro Agent 记忆失败: {e}。它可能保留了之前的上下文。")

async def get_neuro_response(chat_messages: list[dict]) -> str:
    """
    向 Neuro Agent 发送聊天消息并获取响应。
    chat_messages: 包含 {"username": str, "text": str} 的列表。
    """
    if letta_client is None or not NEURO_AGENT_ID:
        print("Letta client or Agent ID not configured, cannot get Neuro response.")
        return "我暂时无法回应，请稍后再试。" # 失败时提供默认响应

    user_message_content = []
    if chat_messages:
        # 将聊天消息合并成一个字符串，作为用户输入发送
        # Letta Agent 会利用其内置的 system_prompt 来理解这些消息的上下文
        injected_chat_lines = [f"{chat['username']}: {chat['text']}" for chat in chat_messages]
        injected_chat_text = (
            "Recent stream chat messages:\n" + 
            "\n".join(injected_chat_lines) + 
            "\n\nPlease respond naturally, considering these messages and your role as a streamer."
        )
        user_message_content.append(TextContent(text=injected_chat_text))
    else:
        # Fallback if no chat messages, but Neuro still needs to say something
        user_message_content.append(TextContent(text="No recent chat. What should I say to my audience?"))


    print(f"正在向 Neuro Agent 发送输入，包含 {len(chat_messages)} 条消息。")

    try:
        response = letta_client.agents.messages.create(
            agent_id=NEURO_AGENT_ID,
            messages=[
                MessageCreate(
                    role="user", 
                    content=user_message_content
                )
            ]
        )

        ai_full_response_text = "I couldn't process that. Please try again."
        if response and response.messages:
            for msg in response.messages:
                if isinstance(msg, AssistantMessage):
                    if hasattr(msg, 'content') and msg.content:
                        content_items = msg.content if isinstance(msg.content, list) else [msg.content]
                        for item in content_items:
                            if isinstance(item, TextContent) and item.text:
                                ai_full_response_text = item.text
                                break
                            elif isinstance(item, str): # Fallback for plain string content
                                ai_full_response_text = item
                                break
                    if ai_full_response_text != "I couldn't process that. Please try again.":
                        break
        
        return ai_full_response_text

    except Exception as e:
        print(f"调用 Letta Agent ({NEURO_AGENT_ID}) 失败: {e}")
        return "与 Letta 的连接似乎有问题，我无法回应。"