from neuro_simulator.utils.state import app_state
from neuro_simulator.utils import console

def _colorize_logo(text: str) -> str:
    """Applies complex coloring rules to the ASCII logo."""
    lines = text.strip("\n").split("\n")
    colored_lines = []

    # --- Color and Range Definitions ---
    NEURO_RANGE = (0, 43)
    S_RANGE = (48, 55)
    A1_RANGE = (56, 63)
    M_RANGE = (64, 74)
    A2_RANGE = (75, 82)

    NEURO_START_RGB = console._hex_to_rgb(console.PALETTE["NEURO_PINK_START"])
    NEURO_END_RGB = console._hex_to_rgb(console.PALETTE["NEURO_PINK_END"])
    
    SAMA_COLORS_RGB = {
        "S": console._hex_to_rgb(console.PALETTE["SAMA_PINK"]),
        "A1": console._hex_to_rgb(console.PALETTE["SAMA_PURPLE"]),
        "M": console._hex_to_rgb(console.PALETTE["SAMA_TEAL"]),
        "A2": console._hex_to_rgb(console.PALETTE["SAMA_ORANGE"]),
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
                color_code = console.rgb_fg(r, g, b)
            # SAMA Solid Colors
            elif S_RANGE[0] <= i <= S_RANGE[1]:
                r, g, b = SAMA_COLORS_RGB["S"]
                color_code = console.rgb_fg(r, g, b)
            elif A1_RANGE[0] <= i <= A1_RANGE[1]:
                r, g, b = SAMA_COLORS_RGB["A1"]
                color_code = console.rgb_fg(r, g, b)
            elif M_RANGE[0] <= i <= M_RANGE[1]:
                r, g, b = SAMA_COLORS_RGB["M"]
                color_code = console.rgb_fg(r, g, b)
            elif A2_RANGE[0] <= i <= A2_RANGE[1]:
                r, g, b = SAMA_COLORS_RGB["A2"]
                color_code = console.rgb_fg(r, g, b)

            new_line += f"{color_code}{char}" if color_code else char
        
        colored_lines.append(new_line)
    
    return "\n".join(colored_lines) + console.RESET

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
        console.box_it_up(messages["STATUS"], title="Status", border_color=console.BLUE)
    if messages["WARNING"]:
        console.box_it_up(messages["WARNING"], title="Warning", border_color=console.YELLOW)
    if messages["ERROR"]:
        console.box_it_up(messages["ERROR"], title="Error", border_color=console.RED)
    if messages["FATAL"]:
        console.box_it_up(messages["FATAL"], title="Fatal", border_color=console.RED, content_color=console.RED)