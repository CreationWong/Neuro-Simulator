from neuro_simulator.utils.state import app_state
import re

# ANSI escape codes for colors
class Colors:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

def display_banner():
    """Displays an ASCII art banner with server and status information."""
    logo = r"""
███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗     ███████╗ █████╗ ███╗   ███╗ █████╗
████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗    ██╔════╝██╔══██╗████╗ ████║██╔══██╗
██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║    ███████╗███████║██╔████╔██║███████║
██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║    ╚════██║██╔══██║██║╚██╔╝██║██╔══██║
██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝    ███████║██║  ██║██║ ╚═╝ ██║██║  ██║
╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝
"""
    print(logo)

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
        return len(re.sub(r'\033\[\d+m', '', s))

    width = max(visible_len(line) for line in lines_with_color)
    if title:
        width = max(width, len(title) + 2)

    # Top border
    if title:
        top_border_str = f"╭───┤ {title} ├{"─" * (width - len(title) - 1)}╮"
    else:
        top_border_str = f"╭───{"─" * width}───╮"
    print(f"{border_color}{top_border_str}{Colors.RESET}")

    # Content lines
    for line in lines_with_color:
        padding = width - visible_len(line)
        print(f"{border_color}│{Colors.RESET}"
              f"   {line}{' ' * padding}   "
              f"{border_color}│{Colors.RESET}")

    # Bottom border
    bottom_border_str = f"╰───{"─" * width}───╯"
    print(f"{border_color}{bottom_border_str}{Colors.RESET}")