# neuro_simulator/chatbot/nickname_gen/generator.py
"""
Nickname generator for the chatbot agent.
Implements a dual-pool system (base and dynamic) with multiple generation strategies.
"""

import logging
import random
from pathlib import Path
from typing import List, Dict, Callable

from ..llm import ChatbotLLMClient
from ...core.config import config_manager
from ...core.path_manager import path_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "chatbot", 1))

class NicknameGenerator:
    """Generates diverse nicknames using a multi-strategy, dual-pool system."""

    def __init__(self):
        if not path_manager:
            raise RuntimeError("PathManager must be initialized before NicknameGenerator.")
        
        self.base_adjectives: List[str] = []
        self.base_nouns: List[str] = []
        self.special_users: List[str] = []
        
        self.dynamic_adjectives: List[str] = []
        self.dynamic_nouns: List[str] = []

        self.llm_client = ChatbotLLMClient()

    def _load_word_pool(self, filename: str) -> List[str]:
        """Loads a word pool from the nickname_gen/data directory."""
        file_path = path_manager.chatbot_nickname_data_dir / filename
        if not file_path.exists():
            logger.warning(f"Nickname pool file not found: {file_path}. The pool will be empty.")
            return []
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    async def initialize(self):
        """Loads base pools and attempts to generate dynamic pools."""
        logger.info("Initializing NicknameGenerator...")
        self.base_adjectives = self._load_word_pool("adjectives.txt")
        self.base_nouns = self._load_word_pool("nouns.txt")
        self.special_users = self._load_word_pool("special_users.txt")

        if not self.base_adjectives or not self.base_nouns:
            logger.warning("Base adjective or noun pools are empty. Nickname generation quality will be affected.")

        if config_manager.settings.chatbot_agent.nickname_generation.enable_dynamic_pool:
            await self._populate_dynamic_pools()
        
        logger.info("NicknameGenerator initialized.")

    async def _populate_dynamic_pools(self):
        """Uses an LLM to generate and populate the dynamic word pools."""
        logger.info("Attempting to populate dynamic nickname pools using LLM...")
        pool_size = config_manager.settings.chatbot_agent.nickname_generation.dynamic_pool_size
        try:
            adj_prompt = f"Generate a list of {pool_size} diverse, cool-sounding English adjectives for online usernames. Output only the words, one per line."
            noun_prompt = f"Generate a list of {pool_size} diverse, cool-sounding English nouns for online usernames. Output only the words, one per line."

            adj_list_str = await self.llm_client.generate(adj_prompt, max_tokens=pool_size * 10)
            noun_list_str = await self.llm_client.generate(noun_prompt, max_tokens=pool_size * 10)

            self.dynamic_adjectives = [line.strip() for line in adj_list_str.split('\n') if line.strip()]
            self.dynamic_nouns = [line.strip() for line in noun_list_str.split('\n') if line.strip()]

            if self.dynamic_adjectives and self.dynamic_nouns:
                logger.info(f"Successfully populated dynamic pools with {len(self.dynamic_adjectives)} adjectives and {len(self.dynamic_nouns)} nouns.")
            else:
                logger.warning("LLM generated empty lists for dynamic pools.")

        except Exception as e:
            logger.error(f"Failed to generate dynamic nickname pool: {e}. Falling back to base pool only.", exc_info=True)
            self.dynamic_adjectives = []
            self.dynamic_nouns = []

    def _get_combined_pools(self) -> tuple[List[str], List[str]]:
        """Returns the combination of base and dynamic pools."""
        adjectives = self.base_adjectives + self.dynamic_adjectives
        nouns = self.base_nouns + self.dynamic_nouns
        return adjectives, nouns

    def _generate_from_word_pools(self) -> str:
        adjectives, nouns = self._get_combined_pools()
        if not adjectives or not nouns:
            return self._generate_random_numeric() # Fallback

        noun = random.choice(nouns)
        # 50% chance to add an adjective
        if random.random() < 0.5:
            adjective = random.choice(adjectives)
            # Formatting variations
            format_choice = random.random()
            if format_choice < 0.4:
                return f"{adjective.capitalize()}{noun.capitalize()}"
            elif format_choice < 0.7:
                return f"{adjective.lower()}_{noun.lower()}"
            else:
                return f"{adjective.lower()}{noun.lower()}"
        else:
            # Add a number suffix 30% of the time
            if random.random() < 0.3:
                return f"{noun.capitalize()}{random.randint(1, 999)}"
            return noun.capitalize()

    def _generate_from_special_pool(self) -> str:
        if not self.special_users:
            return self._generate_from_word_pools() # Fallback
        return random.choice(self.special_users)

    def _generate_random_numeric(self) -> str:
        return f"user{random.randint(10000, 99999)}"

    def generate_nickname(self) -> str:
        """Generates a single nickname based on weighted strategies."""
        strategies: Dict[Callable[[], str], int] = {
            self._generate_from_word_pools: 70,
            self._generate_from_special_pool: 15,
            self._generate_random_numeric: 15,
        }

        # Filter out strategies that can't be run (e.g., empty special pool)
        if not self.special_users:
            strategies.pop(self._generate_from_special_pool, None)
            # Redistribute weight
            if strategies:
                total_weight = sum(strategies.values())
                strategies = {k: v/total_weight * 100 for k,v in strategies.items()}

        if not any(self._get_combined_pools()):
             strategies = {self._generate_random_numeric: 100}

        chosen_strategy = random.choices(
            population=list(strategies.keys()),
            weights=list(strategies.values()),
            k=1
        )[0]

        return chosen_strategy()
