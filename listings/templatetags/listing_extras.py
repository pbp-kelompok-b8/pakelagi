from django import template

register = template.Library()


@register.filter
def rupiah(value):
    """285000 -> 'Rp 285.000' (titik sebagai pemisah ribuan, gaya Indonesia). Ini biar dia konsisten"""
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return ""
    return "Rp " + f"{amount:,}".replace(",", ".")
