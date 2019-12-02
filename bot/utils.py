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


def break_up_long_message(message_text):
    """
    Given a message text, break it into chunks of < 2000 characters.
    :param message_text:
    :return:
    """
    chunks = []
    curr_message = ""
    for line in message_text.splitlines(keepends=True):
        if len(curr_message) + len(line) > 2000:
            chunks.append(curr_message)
            curr_message = line
        else:
            curr_message += line
    chunks.append(curr_message)
    return chunks
