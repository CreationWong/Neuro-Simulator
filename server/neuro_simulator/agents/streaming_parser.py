# server/neuro_simulator/agents/streaming_parser.py
"""
A utility for parsing complete JSON objects from a streaming text source.
"""
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Union

logger = logging.getLogger(__name__)


async def parse_json_stream(
    text_stream: AsyncGenerator[str, None],
) -> AsyncGenerator[Union[Dict[str, Any], List[Any]], None]:
    """
    Parses a stream of text chunks to find and yield complete JSON objects or arrays.
    This parser uses the built-in json.JSONDecoder to robustly find JSON objects
    in a stream.

    Args:
        text_stream: An async generator yielding text chunks.

    Yields:
        A parsed JSON object (dict) or array (list).
    """
    buffer = ""
    decoder = json.JSONDecoder()

    async for chunk in text_stream:
        # Add new data to the buffer and remove leading whitespace
        buffer = (buffer + chunk).lstrip()

        while buffer:
            try:
                # Try to decode a JSON object from the beginning of the buffer
                obj, end_index = decoder.raw_decode(buffer)

                # If successful, yield the object
                logger.debug("Successfully parsed a JSON object from stream.")
                yield obj

                # Remove the parsed object from the buffer and any leading whitespace
                buffer = buffer[end_index:].lstrip()

            except json.JSONDecodeError:
                # Not enough data to form a complete JSON object, break the inner loop
                # and wait for more chunks to arrive.
                break