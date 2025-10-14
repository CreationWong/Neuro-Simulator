from neuro_simulator.utils.state import app_state
import re

# ANSI escape codes for colors
class Colors:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converts a hex color string to an (R, G, B) tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def _colorize_logo(text: str) -> str:
    """Applies complex coloring rules to the ASCII logo."""
    lines = text.strip("\n").split("\n")
    colored_lines = []

    # --- Color and Range Definitions ---
    # Note: Ranges are 0-indexed, converted from user's 1-based columns.
    NEURO_RANGE = (0, 43)
    S_RANGE = (48, 55)
    A1_RANGE = (56, 63)
    M_RANGE = (64, 74)
    A2_RANGE = (75, 82)

    NEURO_START_RGB = _hex_to_rgb("#8b3f5e")
    NEURO_END_RGB = _hex_to_rgb("#fda6ad")
    
    SAMA_COLORS_RGB = {
        "S": _hex_to_rgb("#ff78b6"),
        "A1": _hex_to_rgb("#ef9ffd"),
        "M": _hex_to_rgb("#36bbbc"),
        "A2": _hex_to_rgb("#dda256"),
    }

    for line in lines:
        new_line = ""
        for i, char in enumerate(line):
            if char.isspace():
                new_line += char
                continue

            color_code = ""
            # NEURO Gradient
            if NEURO_RANGE[0] <= i <= NEURO_RANGE[1]:
                fraction = (i - NEURO_RANGE[0]) / (NEURO_RANGE[1] - NEURO_RANGE[0])
                r = int(NEURO_START_RGB[0] + (NEURO_END_RGB[0] - NEURO_START_RGB[0]) * fraction)
                g = int(NEURO_START_RGB[1] + (NEURO_END_RGB[1] - NEURO_START_RGB[1]) * fraction)
                b = int(NEURO_START_RGB[2] + (NEURO_END_RGB[2] - NEURO_START_RGB[2]) * fraction)
                color_code = f"\033[38;2;{r};{g};{b}m"
            # SAMA Solid Colors
            elif S_RANGE[0] <= i <= S_RANGE[1]:
                r, g, b = SAMA_COLORS_RGB["S"]
                color_code = f"\033[38;2;{r};{g};{b}m"
            elif A1_RANGE[0] <= i <= A1_RANGE[1]:
                r, g, b = SAMA_COLORS_RGB["A1"]
                color_code = f"\033[38;2;{r};{g};{b}m"
            elif M_RANGE[0] <= i <= M_RANGE[1]:
                r, g, b = SAMA_COLORS_RGB["M"]
                color_code = f"\033[38;2;{r};{g};{b}m"
            elif A2_RANGE[0] <= i <= A2_RANGE[1]:
                r, g, b = SAMA_COLORS_RGB["A2"]
                color_code = f"\033[38;2;{r};{g};{b}m"

            new_line += f"{color_code}{char}" if color_code else char
        
        colored_lines.append(new_line)
    
    return "\n".join(colored_lines) + Colors.RESET

def display_banner():
    """Displays an ASCII art banner with server and status information."""
    logo_text = r"""
 
███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗     ███████╗ █████╗ ███╗   ███╗ █████╗
████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗    ██╔════╝██╔══██╗████╗ ████║██╔══██╗
██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║    ███████╗███████║██╔████╔██║███████║
██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║    ╚════██║██╔══██║██║╚██╔╝██║██╔══██║
██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝    ███████║██║  ██║██║ ╚═╝ ██║██║  ██║
╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝
 
"""
    
    colored_logo = _colorize_logo(logo_text)
    print(colored_logo)

    # --- URL and Status Boxes ---
    messages = {
        "STATUS": [],
        "WARNING": [],
        "ERROR": [],
        "FATAL": []
    }

    # Gather URL info into STATUS
    host = getattr(app_state, "server_host", "127.0.0.1")
    port = getattr(app_state, "server_port", 8000)
    display_host = host if host != "0.0.0.0" else "127.0.0.1"
    messages["STATUS"].append(f"Server URL:    http://{display_host}:{port}/")
    messages["STATUS"].append(f"Client URL:    http://{display_host}:{port}/")
    messages["STATUS"].append(f"Dashboard URL: http://{display_host}:{port}/dashboard")

    # Gather messages into categories
    if getattr(app_state, 'is_first_run', False):
        work_dir = getattr(app_state, "work_dir", "(Unknown)")
        messages["WARNING"].append(f"First run in this directory: {work_dir}")

    if getattr(app_state, 'using_default_password', False):
        messages["WARNING"].append("You are using the default panel password. Please change it.")

    missing_providers = getattr(app_state, 'missing_providers', [])
    if missing_providers:
        messages["ERROR"].append(f"Missing providers in config: {', '.join(missing_providers)}")

    unassigned_providers = getattr(app_state, 'unassigned_providers', [])
    if unassigned_providers:
        messages["ERROR"].append(f"Unassigned providers: {', '.join(unassigned_providers)}")

    if missing_providers or unassigned_providers:
        messages["FATAL"].append("Cannot start stream due to missing configuration.")

    # Display boxes for each category that has messages
    if messages["STATUS"]:
        box_it_up(messages["STATUS"], title="Status", border_color=Colors.BLUE)
    if messages["WARNING"]:
        box_it_up(messages["WARNING"], title="Warning", border_color=Colors.YELLOW)
    if messages["ERROR"]:
        box_it_up(messages["ERROR"], title="Error", border_color=Colors.RED)
    if messages["FATAL"]:
        box_it_up(messages["FATAL"], title="Fatal", border_color=Colors.RED, content_color=Colors.RED)

def box_it_up(lines: list[str], title: str = "", border_color: str = Colors.RESET, content_color: str = Colors.RESET):
    """Wraps a list of strings in a decorative box and prints them."""
    if not lines:
        return

    # Apply content color to lines before calculating width
    if content_color and content_color != Colors.RESET:
        lines_with_color = [f"{content_color}{line}{Colors.RESET}" for line in lines]
    else:
        lines_with_color = lines

    def visible_len(s: str) -> int:
        return len(re.sub(r'\033\[[\d;]*m', '', s))

    width = max(visible_len(line) for line in lines_with_color)
    if title:
        width = max(width, len(title) + 2)

    # Top border
    if title:
        top_border_str = f"╭───┤ {title} ├{'─' * (width - len(title) - 1)}╮"
    else:
        top_border_str = f"╭───{'─' * width}───╮"
    print(f"{border_color}{top_border_str}{Colors.RESET}")

    # Content lines
    for line in lines_with_color:
        padding = width - visible_len(line)
        print(f"{border_color}│{Colors.RESET}"
              f"   {line}{' ' * padding}   "
              f"{border_color}│{Colors.RESET}")

    # Bottom border
    bottom_border_str = f"╰───{'─' * width}───╯"
    print(f"{border_color}{bottom_border_str}{Colors.RESET}")