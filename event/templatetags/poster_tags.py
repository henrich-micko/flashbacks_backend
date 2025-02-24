from django import template


register = template.Library()

@register.simple_tag
def generate_qrcode_for_event(event, front_color, background_color):
    return event.invite_code.generate_qrcode(
        front_color=front_color,
        background_color=background_color
    )