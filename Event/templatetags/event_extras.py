from django import template

register = template.Library()

@register.filter
def get_sport_emoji(sport_type):
    """Return emoji for sport type"""
    emoji_map = {
        'tennis': '🎾',
        'basketball': '🏀',
        'soccer': '⚽',
        'badminton': '🏸',
        'volleyball': '🏐',
        'futsal': '⚽',
        'paddle': '🏓',
        'table_tennis': '🏓',
        'swimming': '🏊',
    }
    return emoji_map.get(sport_type, '🏃')

@register.filter
def rupiah(value):
    """Format number with dot thousand separators (e.g. 2000 -> 2.000)."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    formatted = f"{amount:,.0f}".replace(",", ".")
    return formatted
