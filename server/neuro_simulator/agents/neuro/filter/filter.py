import logging
import json
import re
from typing import Any, Dict, List, Optional

from ....core.llm_manager import LLMClient, llm_manager
from ....core.path_manager import path_manager

logger = logging.getLogger(__name__)


class NeuroFilter:
    """
    A filter for Neuro-sama's outputs. It checks for safety and quality,
    and can either approve, replace, or censor the message.
    """

    def __init__(self, llm_provider_id: Optional[str]):
        if llm_provider_id:
            self.llm: Optional[LLMClient] = llm_manager.get_client(llm_provider_id)
        else:
            self.llm = None
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Loads the prompt template from the file."""
        assert path_manager is not None
        prompt_path = path_manager.neuro_agent_dir / "filter_prompt.txt"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Filter prompt template not found at {prompt_path}")
            return ""

    def _parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """Parses tool calls from the LLM's response."""
        try:
            match = re.search(
                r"""```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\])""", response_text
            )
            if not match:
                logger.warning(f"No valid JSON tool call block found in filter response: {response_text}")
                return []
            json_str = match.group(1) or match.group(2)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse tool calls from filter LLM response: {e}")
            return []

    async def process(
        self,
        original_output: str,
    ) -> List[Dict[str, Any]]:
        """
        Processes the original output through the filter.

        Returns:
            A list of tool calls (usually a single 'speak' call).
        """
        if not self.llm or not self._prompt_template:
            logger.warning("Filter LLM or prompt not configured. Passing through output.")
            return [{"name": "speak", "params": {"text": original_output}}]

        prompt = self._prompt_template.format(
            original_output=original_output,
        )

        response_text = await self.llm.generate(prompt)

        filtered_calls = self._parse_tool_calls(response_text)

        # Fallback in case the filter LLM fails to generate a valid call
        if not filtered_calls:
            logger.warning("Filter failed to return a valid tool call. Approving original text as a fallback.")
            return [{"name": "speak", "params": {"text": original_output}}]

        return filtered_calls
