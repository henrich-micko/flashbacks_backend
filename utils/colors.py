import re


def is_valid_hex_color(hex_color):
    hex_pattern = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$")
    return bool(hex_pattern.match(hex_color))

def hex_to_rgba(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        a = 255
    elif len(hex_color) == 8:
        r, g, b, a = (int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
    else:
        raise ValueError("Invalid hex color format")
    return (r, g, b, a)

def rgba_to_hex(r, g, b, a=255):
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"

def generate_light_color(color):
    main_rgb = (255, 122, 122)
    light_rgb = (206, 180, 180)
    diff_r, diff_g, diff_b = (light_rgb[i] - main_rgb[i] for i in range(3))
    r, g, b, a = hex_to_rgba(color)
    new_r = max(0, min(255, r + diff_r))
    new_g = max(0, min(255, g + diff_g))
    new_b = max(0, min(255, b + diff_b))
    return rgba_to_hex(new_r, new_g, new_b, a)
