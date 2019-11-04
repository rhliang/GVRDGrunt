import sqlite3
import discord

from bot.convert_using_guild import emoji_converter


# create table raid_fyi(
#     guild_id primary key,
#     fyi_emoji,
#     fyi_emoji_type,
# );
#
# create table raid_fyi_channel_mapping(
#     guild_id,
#     chat_channel_id primary key,
#     fyi_channel_id
# );
class RaidFYIDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        # The database can be initialized with raid_fyi_initialization.sql
        self.conn = sqlite3.connect(self.path_to_db)

    def get_fyi_info(self, guild: discord.Guild):
        """
        Return this guild's raid FYI configuration.

        :param guild:
        :return:
        """
        result = {}
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select 
                    fyi_emoji,
                    fyi_emoji_type
                from raid_fyi 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            fyi_info_tuple = guild_info_cursor.fetchone()
            if fyi_info_tuple is None:
                return None

            fyi_emoji, fyi_emoji_type = fyi_info_tuple
            result["fyi_emoji"] = fyi_emoji
            if fyi_emoji_type == "custom":
                result["fyi_emoji"] = emoji_converter(guild, fyi_emoji)

            channel_mapping_cursor = self.conn.execute(
                """
                select
                    chat_channel_id,
                    fyi_channel_id
                from raid_fyi_channel_mapping
                where guild_id = ?;
                """,
                (guild.id,)
            )
            channel_mappings = {}
            for chat_channel_id, fyi_channel_id in channel_mapping_cursor:
                channel_mappings[guild.get_channel(chat_channel_id)] = guild.get_channel(fyi_channel_id)

        result["channel_mappings"] = channel_mappings
        return result

    def configure_fyi(
            self,
            guild: discord.Guild,
            fyi_emoji
    ):
        """
        Configure the guild's FYI functionality.

        :param guild:
        :param fyi_emoji:
        :raises:
        :return:
        """
        emoji_type = "normal"
        emoji_stored_value = fyi_emoji
        if isinstance(fyi_emoji, discord.Emoji):
            emoji_type = "custom"
            emoji_stored_value = fyi_emoji.id

        with self.conn:
            self.conn.execute(
                """
                insert into raid_fyi 
                (
                    guild_id,
                    fyi_emoji,
                    fyi_emoji_type
                )
                values (?, ?, ?);
                """,
                (
                    guild.id,
                    emoji_stored_value,
                    emoji_type
                )
            )

    def deactivate_fyi(self, guild: discord.Guild):
        """
        Disable the guild's FYI functionality by removing its configuration from the database.

        :param guild:
        :param role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from raid_fyi where guild_id = ?;",
                (guild.id,)
            )

    def register_fyi_channel_mapping(
            self,
            guild: discord.Guild,
            chat_channel: discord.TextChannel,
            fyi_channel: discord.TextChannel
    ):
        """
        Register a chat-channel-to-FYI-channel mapping.

        :param guild:
        :param chat_channel:
        :param fyi_channel:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "insert or ignore into raid_fyi_channel_mapping "
                "(guild_id, chat_channel_id, fyi_channel_id) "
                "values (?, ?, ?)",
                (guild.id, chat_channel.id, fyi_channel.id)
            )

    def deregister_fyi_channel_mapping(self, guild: discord.Guild, chat_channel: discord.TextChannel):
        """
        Deregister the specified FYI channel mapping.

        :param guild:
        :param chat_channel:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from raid_fyi_channel_mapping where guild_id = ? and chat_channel_id = ?",
                (guild.id, chat_channel.id)
            )

    def deregister_all_fyi_channel_mappings(self, guild: discord.Guild):
        """
        Deregister all FYI channel mappings for the specified guild.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from raid_fyi_channel_mapping where guild_id = ?",
                (guild.id,)
            )

