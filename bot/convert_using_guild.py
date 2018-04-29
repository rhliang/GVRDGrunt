"""
Simple helper functions that convert object IDs to the corresponding Discord objects using only the guild.
"""

def role_converter(guild, role_id):
    """
    Find the guild role corresponding to the given role ID.

    :param guild:
    :param role_id:
    :return:
    """
    for role in guild.roles:
        if role.id == role_id:
            return role


def role_converter_from_name(guild, role_name):
    """
    Find the guild role corresponding to the given role name.

    :param guild:
    :param role_id:
    :return:
    """
    for role in guild.roles:
        if role.name == role_name:
            return role


def emoji_converter(guild, emoji_id):
    """
    Find the guild emoji corresponding to the given emoji ID.

    :param guild:
    :param emoji_id:
    :return:
    """
    for emoji in guild.emojis:
        if emoji.id == emoji_id:
            return emoji
