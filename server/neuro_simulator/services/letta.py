# neuro_simulator/services/letta.py
import asyncio
import logging
from typing import Union, List, Dict, Any, Optional

from fastapi import HTTPException, status
from letta_client import Letta, MessageCreate, TextContent, LlmConfig, AssistantMessage

from ..core.agent_interface import BaseAgent
from ..core.config import config_manager

# Standard logger for this module
logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

# Global client instance, initialized once
letta_client: Union[Letta, None] = None

def initialize_letta_client():
    """Initializes the global Letta client if not already initialized."""
    global letta_client
    if letta_client:
        return

    try:
        if not config_manager.settings.api_keys.letta_token:
            raise ValueError("LETTA_API_TOKEN is not set. Cannot initialize Letta client.")
        
        client_args = {'token': config_manager.settings.api_keys.letta_token}
        if config_manager.settings.api_keys.letta_base_url:
            client_args['base_url'] = config_manager.settings.api_keys.letta_base_url
            logger.info(f"Letta client is being initialized for self-hosted URL: {config_manager.settings.api_keys.letta_base_url}")
        else:
            logger.info("Letta client is being initialized for Letta Cloud.")

        letta_client = Letta(**client_args)

        agent_id = config_manager.settings.api_keys.neuro_agent_id
        if agent_id:
            try:
                agent_data = letta_client.agents.retrieve(agent_id=agent_id)
                logger.info(f"Successfully verified Letta Agent, ID: {agent_data.id}, Name: {agent_data.name}")
            except Exception as e:
                error_msg = f"Error: Cannot retrieve Letta Agent (ID: {agent_id}). Details: {e}"
                logger.error(error_msg)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
    except Exception as e:
        logger.error(f"Failed to initialize Letta client: {e}")
        letta_client = None

def get_letta_client() -> Letta:
    if letta_client is None:
        raise ValueError("Letta client is not initialized.")
    return letta_client

class LettaAgent(BaseAgent):
    """Letta Agent implementation that adheres to the BaseAgent interface."""
    
    def __init__(self):
        self.client: Letta = None
        self.agent_id: str = None

    async def initialize(self):
        initialize_letta_client()
        self.client = get_letta_client()
        self.agent_id = config_manager.settings.api_keys.neuro_agent_id
        if not self.agent_id:
            raise ValueError("Letta agent ID (neuro_agent_id) is not configured.")

    async def reset_memory(self):
        """Resets message history and clears the conversation_summary block."""
        try:
            # Reset message history
            await asyncio.to_thread(self.client.agents.messages.reset, agent_id=self.agent_id)
            logger.info(f"Letta Agent (ID: {self.agent_id}) message history has been reset.")

            # Find and clear the conversation_summary block
            blocks = await asyncio.to_thread(self.client.agents.blocks.list, agent_id=self.agent_id)
            summary_block = next((block for block in blocks if block.name == "conversation_summary"), None)
            
            if summary_block:
                await asyncio.to_thread(
                    self.client.agents.blocks.modify,
                    agent_id=self.agent_id,
                    block_id=summary_block.id,
                    content=""
                )
                logger.info(f"Cleared content of 'conversation_summary' block (ID: {summary_block.id}) for Letta Agent.")
            else:
                logger.warning("'conversation_summary' block not found for Letta Agent, skipping clearing.")

        except Exception as e:
            logger.warning(f"Failed during Letta Agent memory reset: {e}")

    async def process_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        # Check if this is a superchat message based on the specific structure
        # from neuro_response_cycle
        is_superchat = (
            len(messages) == 2 and
            messages[0].get("role") == "system" and
            messages[1].get("role") == "system" and
            "HIGHLIGHTED MESSAGE" in messages[1].get("content", "")
        )

        if is_superchat:
            try:
                # Extract username and text from the superchat message
                # Format is "=== HIGHLIGHTED MESSAGE ===\n{username}: {text}"
                content_lines = messages[1]["content"].split('\n', 1)
                user_and_text = content_lines[1]
                parts = user_and_text.split(':', 1)
                sc_username = parts[0].strip()
                sc_text = parts[1].strip()
                injected_chat_lines = [f"{sc_username}: {sc_text}"]
                injected_chat_text = (
                    "Here is a highlighted message from my Twitch chat:\n---\n" +
                    "\n".join(injected_chat_lines) +
                    "\n---\nNow, as the streamer Neuro-Sama, please continue the conversation naturally."
                )
                logger.info(f"Processing highlighted message for Letta: {injected_chat_lines[0]}")
            except (IndexError, AttributeError) as e:
                logger.error(f"Failed to parse superchat for Letta, falling back. Error: {e}")
                # Fallback to default empty prompt if parsing fails
                injected_chat_text = "My chat is quiet right now. As Neuro-Sama, what should I say to engage them?"

        elif messages:
            injected_chat_lines = [f"{chat['username']}: {chat['text']}" for chat in messages if 'username' in chat and 'text' in chat]
            injected_chat_text = (
                "Here are some recent messages from my Twitch chat:\n---\n" +
                "\n".join(injected_chat_lines) + 
                "\n---\nNow, as the streamer Neuro-Sama, please continue the conversation naturally."
            )
        else:
            injected_chat_text = "My chat is quiet right now. As Neuro-Sama, what should I say to engage them?"

        logger.info(f"Sending input to Letta Agent ({len(messages)} messages)...")

        response_text = ""
        error_str = None

        try:
            response = await asyncio.to_thread(
                self.client.agents.messages.create,
                agent_id=self.agent_id,
                messages=[MessageCreate(role="user", content=injected_chat_text)]
            )

            if not response or not response.messages:
                raise ValueError("Letta response is empty or contains no messages.")

            for message in reversed(response.messages):
                if isinstance(message, AssistantMessage) and hasattr(message, 'content'):
                    content = message.content
                    if isinstance(content, str) and content.strip():
                        response_text = content.strip()
                        break
                    elif isinstance(content, list) and content:
                        first_part = content[0]
                        if isinstance(first_part, TextContent) and hasattr(first_part, 'text') and first_part.text.strip():
                            response_text = first_part.text.strip()
                            break
            
            if not response_text:
                logger.warning(f"No valid AssistantMessage content found in Letta response.")
                response_text = "I'm not sure what to say to that."

        except Exception as e:
            logger.error(f"Error calling Letta Agent ({self.agent_id}): {e}")
            error_str = str(e)
            response_text = "Someone tell Vedal there is a problem with my AI."

        return {
            "input_messages": messages,
            "final_response": response_text,
            "llm_response": response_text,
            "tool_executions": [],
            "error": error_str
        }

    # Memory Block Management
    async def get_memory_blocks(self) -> List[Dict[str, Any]]:
        try:
            blocks = await asyncio.to_thread(self.client.agents.blocks.list, agent_id=self.agent_id)
            return [block.model_dump() for block in blocks]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting memory blocks from Letta: {e}")

    async def get_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        try:
            block = await asyncio.to_thread(self.client.agents.blocks.retrieve, agent_id=self.agent_id, block_id=block_id)
            return block.model_dump()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting memory block from Letta: {e}")

    async def create_memory_block(self, title: str, description: str, content: List[str]) -> Dict[str, str]:
        try:
            block = await asyncio.to_thread(
                self.client.agents.blocks.create,
                agent_id=self.agent_id,
                name=title,
                content="\n".join(content),
                description=description
            )
            return {"block_id": block.id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating memory block in Letta: {e}")

    async def update_memory_block(self, block_id: str, title: Optional[str], description: Optional[str], content: Optional[List[str]]):
        try:
            update_params = {}
            if title is not None: update_params["name"] = title
            if description is not None: update_params["description"] = description
            if content is not None: update_params["content"] = "\n".join(content)

            await asyncio.to_thread(
                self.client.agents.blocks.modify,
                agent_id=self.agent_id,
                block_id=block_id,
                **update_params
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating memory block in Letta: {e}")

    async def delete_memory_block(self, block_id: str):
        try:
            await asyncio.to_thread(self.client.agents.blocks.delete, agent_id=self.agent_id, block_id=block_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting memory block in Letta: {e}")

    # Unsupported Features for Letta Agent
    async def get_init_memory(self) -> Dict[str, Any]:
        raise HTTPException(status_code=400, detail="Getting init memory is not supported for Letta agent")

    async def update_init_memory(self, memory: Dict[str, Any]):
        raise HTTPException(status_code=400, detail="Updating init memory is not supported for Letta agent")

    async def get_temp_memory(self) -> List[Dict[str, Any]]:
        raise HTTPException(status_code=400, detail="Getting temp memory is not supported for Letta agent")

    async def add_temp_memory(self, content: str, role: str):
        raise HTTPException(status_code=400, detail="Adding to temp memory is not supported for Letta agent")

    async def clear_temp_memory(self):
        raise HTTPException(status_code=400, detail="Clearing temp memory is not supported for Letta agent")

    async def get_available_tools(self) -> str:
        return "Tool management is not supported for Letta agent via this API"

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        raise HTTPException(status_code=400, detail="Tool execution is not supported for Letta agent via this API")

    async def get_message_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        # Letta's history is managed on their server and not directly exposed.
        # Return an empty list to prevent breaking internal consumers like the admin panel.
        return []
