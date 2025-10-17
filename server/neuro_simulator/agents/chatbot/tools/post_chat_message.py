# neuro_simulator/chatbot/tools/post_chat_message.py
"""The Post Chat Message tool for the chatbot agent."""

from typing import Dict, Any, List

from neuro_simulator.agents.tools.base import BaseTool


class PostChatMessageTool(BaseTool):
    """Tool for the chatbot to post a message to the stream chat."""

    def __init__(self, memory_manager):
        super().__init__(memory_manager)

    @property
    def name(self) -> str:
        return "post_chat_message"

    @property
    def description(self) -> str:
        return "Posts a text message to the stream chat, as if you are a viewer."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "text",
                "type": "string",
                "description": "The content of the chat message to post.",
                "required": True,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes the action. This tool doesn't *actually* send the message,
        it just structures the output for the core agent logic to handle.
        """
        text = kwargs.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError("The 'text' parameter must be a non-empty string.")

        # The result is the text to be posted. The core agent will combine this
        # with a generated nickname before sending it to the stream.
        return {"status": "success", "text_to_post": text}
