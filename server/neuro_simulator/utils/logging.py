# neuro_simulator/utils/logging.py
import logging
import sys
from collections import deque
from typing import Deque

from neuro_simulator.core.config import config_manager
from neuro_simulator.utils import console

# Define a single, consistent format for all logs
LOG_FORMAT = "%(asctime)s - [%(name)-32s] - %(levelname)-8s - %(message)s"
DATE_FORMAT = "%H:%M:%S"


# --- Custom Colored Formatter for Console Output ---
class ColoredFormatter(logging.Formatter):
    """A custom log formatter that adds color ONLY to the log level name."""

    def __init__(self, fmt):
        super().__init__(fmt, datefmt=DATE_FORMAT)
        self.level_colors = {
            logging.DEBUG: console.THEME["DEBUG"],
            logging.INFO: console.THEME["INFO"],
            logging.WARNING: console.THEME["WARNING"],
            logging.ERROR: console.THEME["ERROR"],
            logging.CRITICAL: console.THEME["CRITICAL"],
        }

    def format(self, record):
        # Create a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)

        # Remove the 'neuro_simulator.' prefix for conciseness
        if record_copy.name.startswith("neuro_simulator."):
            record_copy.name = record_copy.name[16:]

        # Truncate long logger names to maintain alignment
        name_len = len(record_copy.name)
        max_name_len = 32  # Must match the width in LOG_FORMAT
        if name_len > max_name_len:
            record_copy.name = f"...{record_copy.name[name_len - max_name_len + 3:]}"

        # Get the color for the level
        color = self.level_colors.get(record_copy.levelno)

        # If a color is found, apply it to the levelname
        if color:
            record_copy.levelname = f"{color}{record_copy.levelname}{console.RESET}"

        # Use the parent class's formatter with the modified record
        return super().format(record_copy)


# Create two independent, bounded queues for different log sources
server_log_queue: Deque[str] = deque(maxlen=1000)
agent_log_queue: Deque[str] = deque(maxlen=1000)


class QueueLogHandler(logging.Handler):
    """A handler that sends log records to a specified queue."""

    def __init__(self, queue: Deque[str]):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        self.queue.append(log_entry)


# Map string log levels to logging constants
_log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

def configure_server_logging():
    """Configures the server (root) logger to use the server_log_queue and a standard format."""
    # Non-colored formatter for the queue (for the web UI)
    queue_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Colored formatter for the console
    console_formatter = ColoredFormatter(LOG_FORMAT)

    # Create a handler that writes to the server log queue for the web UI
    server_queue_handler = QueueLogHandler(server_log_queue)
    server_queue_handler.setFormatter(queue_formatter)

    # Create a handler that writes to the console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # Get the root logger, clear any existing handlers, and add our new ones
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(server_queue_handler)
    root_logger.addHandler(console_handler)

    # Set log level from config
    log_level_str = config_manager.settings.server.log_level.upper()
    level = _log_level_map.get(log_level_str, logging.INFO)
    root_logger.setLevel(level)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Force uvicorn error logger to use our handlers
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers = [server_queue_handler, console_handler]
    uvicorn_error_logger.propagate = False
  # Prevent double-logging

    root_logger.info(
        "Server logging configured for queue and console."
    )
