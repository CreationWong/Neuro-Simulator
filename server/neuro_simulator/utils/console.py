"""
A centralized module for console UI, including ANSI color codes and display utilities.
"""

import re
import shutil
import textwrap

# ==============================================================================
# ANSI Color Definitions
# ==============================================================================

# --- Basic ANSI Color Codes ---
# Using simple \x1b format for broad compatibility.
RESET = "\x1b[0m"

# Standard Colors
BLACK = "\x1b[30m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
BLUE = "\x1b[34m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
WHITE = "\x1b[37m"

# Bright/Bold Colors
BRIGHT_BLACK = "\x1b[90m"  # Often rendered as Grey
BRIGHT_RED = "\x1b[91m"
BRIGHT_GREEN = "\x1b[92m"
BRIGHT_YELLOW = "\x1b[93m"
BRIGHT_BLUE = "\x1b[94m"
BRIGHT_MAGENTA = "\x1b[95m"
BRIGHT_CYAN = "\x1b[96m"
BRIGHT_WHITE = "\x1b[97m"

# Special Formatting
BOLD = "\x1b[1m"
UNDERLINE = "\x1b[4m"
BOLD_RED = "\x1b[31;1m"

# For logging levels and semantic actions
THEME = {
    # Log Levels
    "DEBUG": BLUE,
    "INFO": GREEN,
    "WARNING": YELLOW,
    "ERROR": RED,
    "CRITICAL": BOLD_RED,

    # Agent Actions (User-defined Framework)
    "SPEAK": YELLOW,
    "THINK": CYAN,
    "MEMORY": MAGENTA,
    "TOOL": GREEN,

    # Other Modules & Statuses
    "EXTERNAL": BLUE,
    "STATUS": BLUE,
}

# --- 24-bit Color Utilities ---

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converts a hex color string to an (R, G, B) tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError("Invalid hex color format. Must be 6 hex digits.")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_fg(r: int, g: int, b: int) -> str:
    """Returns the ANSI escape code for a 24-bit foreground color."""
    return f"\033[38;2;{r};{g};{b}m"

def rgb_bg(r: int, g: int, b: int) -> str:
    """Returns the ANSI escape code for a 24-bit background color."""
    return f"\033[48;2;{r};{g};{b}m"

# --- Project-specific Color Palette (Hex) ---
# Centralized for consistency in branding.

PALETTE = {
    # Neuro-sama official/fan colors
    "NEURO_PINK_START": "#8b3f5e",
    "NEURO_PINK_END": "#fda6ad",
    "SAMA_PINK": "#ff78b6",
    "SAMA_PURPLE": "#ef9ffd",
    "SAMA_TEAL": "#36bbbc",
    "SAMA_ORANGE": "#dda256",

    # Standard UI feedback colors
    "INFO_BLUE": "#3498db",
    "SUCCESS_GREEN": "#2ecc71",
    "WARNING_YELLOW": "#f1c40f",
    "ERROR_RED": "#e74c3c",
    "CRITICAL_RED": "#c0392b",
    "DEBUG_GREY": "#7f8c8d",
}


# ==============================================================================
# Console UI Functions
# ==============================================================================

def box_it_up(
    lines: list[str],
    title: str = "",
    border_color: str = RESET,
    content_color: str = RESET,
):
    """Wraps a list of strings in a decorative, auto-wrapping box and prints them."""
    if not lines:
        return

    # --- Text Wrapping Logic ---
    terminal_width = shutil.get_terminal_size((120, 24)).columns
    max_content_width = terminal_width - 4 - 6  # box borders and padding

    def visible_len(s: str) -> int:
        return len(re.sub(r"\033\[[\d;]*m", "", s))

    wrapped_lines = []
    for line in lines:
        color_prefix = content_color if content_color != RESET else ""
        color_suffix = RESET if color_prefix else ""

        # Don't wrap pre-colored lines to avoid mangling codes
        if "\033[" in line or visible_len(line) <= max_content_width:
            wrapped_lines.append(line)
            continue

        # If the line is too long, wrap it
        wrapped_sub_lines = textwrap.wrap(
            line,
            width=max_content_width,
            replace_whitespace=False,
            drop_whitespace=True,
        )
        for sub_line in wrapped_sub_lines:
            wrapped_lines.append(f"{color_prefix}{sub_line}{color_suffix}")

    if not wrapped_lines:
        return

    # --- Drawing Logic ---
    width = max(visible_len(line) for line in wrapped_lines)
    if title:
        width = max(width, len(title) + 2)

    # Top border
    if title:
        top_border_str = f"╭───┤ {title} ├{'─' * (width - len(title) - 1)}╮"
    else:
        top_border_str = f"╭───{'─' * width}───╮"
    print(f"{border_color}{top_border_str}{RESET}")

    # Content lines
    for line in wrapped_lines:
        padding = width - visible_len(line)
        print(
            f"{border_color}│{RESET}"
            f"   {line}{' ' * padding}   "
            f"{border_color}│{RESET}"
        )

    # Bottom border
    bottom_border_str = f"╰───{'─' * width}───╯"
    print(f"{border_color}{bottom_border_str}{RESET}")