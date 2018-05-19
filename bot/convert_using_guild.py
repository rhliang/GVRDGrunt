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


def get_matching_roles_case_insensitive(guild, role_name):
    """
    Find any guild roles that correspond to the given role name.

    If there is an unambiguous match, return a singleton list with the role.
    Otherwise, return a list of all possible matches.  This first attempts to
    match the role name as given; if nothing is found and the role name starts
    with "@", it tries the same thing after stripping the "@" off the name.

    :param guild:
    :param role_name:
    :return: a list of all possible matching roles.
    """
    possible_roles = []
    for role in guild.roles:
        if role.name == role_name:
            return [role]
        if role.name.lower() == role_name.lower():
            possible_roles.append(role)

    if len(possible_roles) == 0 and role_name[0] == "@":
        for role in guild.roles:
            if role_name[1:] == role.name:
                return [role]
            if role_name[1:].lower() == role.name.lower():
                possible_roles.append(role)

    return possible_roles


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
