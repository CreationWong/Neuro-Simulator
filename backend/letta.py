# backend/letta.py
from letta_client import Letta, MessageCreate, TextContent, LlmConfig, AssistantMessage
from fastapi import HTTPException, status
from config import LETTA_API_TOKEN, LETTA_BASE_URL, NEURO_AGENT_ID

# 初始化 Letta 客户端
letta_client: Letta | None = None
try:
    if not LETTA_API_TOKEN:
        raise ValueError("LETTA_API_TOKEN is not set. Cannot initialize Letta client.")
    
    client_args = {'token': LETTA_API_TOKEN}
    if LETTA_BASE_URL:
        client_args['base_url'] = LETTA_BASE_URL
        print(f"Letta client is being initialized for self-hosted URL: {LETTA_BASE_URL}")
    else:
        print("Letta client is being initialized for Letta Cloud.")

    letta_client = Letta(**client_args)

    if NEURO_AGENT_ID:
        try:
            agent_data = letta_client.agents.retrieve(agent_id=NEURO_AGENT_ID)
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
            if hasattr(agent_data, 'system_prompt') and agent_data.system_prompt:
                print(f"  -> System Prompt: {agent_data.system_prompt[:100]}...")
            else:
                print("  -> 警告: Neuro Agent 没有配置 system_prompt。请在 Letta UI 或通过 API 设置。")

        except Exception as e:
            print(f"错误: 无法获取 Neuro Letta Agent (ID: {NEURO_AGENT_ID})。请确保 ID 正确，且 Letta Cloud 服务可访问。")
            print(f"详情: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Neuro Agent {NEURO_AGENT_ID} 无法找到或访问: {e}")
except Exception as e:
    print(f"初始化 Letta 客户端失败: {e}")
    letta_client = None

def get_letta_client():
    if letta_client is None: raise ValueError("Letta client is not initialized.")
    return letta_client

async def reset_neuro_agent_memory():
    if letta_client is None or not NEURO_AGENT_ID: return
    try:
        letta_client.agents.messages.reset(agent_id=NEURO_AGENT_ID)
        print(f"Neuro Agent {NEURO_AGENT_ID} 记忆已重置。")
    except Exception as e:
        print(f"警告: 重置 Neuro Agent 记忆失败: {e}。")

async def get_neuro_response(chat_messages: list[dict]) -> str:
    if letta_client is None or not NEURO_AGENT_ID:
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

    print(f"正在向 Neuro Agent 发送输入 (包含 {len(chat_messages)} 条消息)...")

    try:
        response = letta_client.agents.messages.create(
            agent_id=NEURO_AGENT_ID,
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
        print(f"错误: 调用 Letta Agent ({NEURO_AGENT_ID}) 失败: {e}")
        return "与 Letta 的连接似乎有问题，我无法回应。"