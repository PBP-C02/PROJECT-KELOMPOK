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