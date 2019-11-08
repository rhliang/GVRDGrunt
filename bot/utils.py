import discord


def emoji_to_db(emoji):
    """
    Given a discord.Emoji object, extract its type and its ID if applicable.
    :param emoji: a discord.Emoji object
    :return:
    """
    emoji_type = "normal"
    emoji_stored_value = emoji
    if isinstance(emoji, discord.Emoji):
        emoji_type = "custom"
        emoji_stored_value = emoji.id
    return emoji_type, emoji_stored_value
