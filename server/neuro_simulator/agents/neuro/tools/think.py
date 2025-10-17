# neuro_simulator/agent/tools/think.py
"""The Think tool for the agent."""

import logging
from typing import Dict, Any, List

from neuro_simulator.agents.tools.base import BaseTool
from neuro_simulator.utils import console

logger = logging.getLogger("neuro_agent")


class ThinkTool(BaseTool):
    """Tool for the agent to output its thought process."""

    def __init__(self, **kwargs):
        pass

    @property
    def name(self) -> str:
        return "think"

    @property
    def description(self) -> str:
        return "Outputs your inner monologue or thought process. Use this to analyze the situation, state your strategy, and plan your response before calling other tools like 'speak'."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "thought",
                "type": "string",
                "description": "The content of your thought process.",
                "required": True,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes the think action by printing the thought to the console.
        """
        thought = kwargs.get("thought")
        if not isinstance(thought, str) or not thought:
            raise ValueError("The 'thought' parameter must be a non-empty string.")

        console.box_it_up(
            thought.split('\n'),
            title="Neuro's Thoughts",
            border_color=console.THEME["THINK"],
        )

        return {"status": "success", "message": "Thought process has been logged."}

