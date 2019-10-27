import sqlite3
import discord

from bot.convert_using_guild import emoji_converter


# create table raid_rsvp_configuration(
#     guild_id primary key,
#     join_emoji,
#     join_emoji_type
# );
#
# create table raid_rsvp(
#     guild_id,
#     creator_id,
#     chat_channel_id,
#     command_msg_id primary key,
#     rsvp_channel_id,
#     rsvp_msg_id
# );

class RaidRSVPDB(object):
    """
    A class representing the SQLite database we use to store our information.

    This piggybacks off of the FYI functionality -- if the FYI functionality is not configured,
    this won't work.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        # The database can be initialized with raid_fyi_initialization.sql
        self.conn = sqlite3.connect(self.path_to_db)

    def get_rsvp_info(self, guild: discord.Guild):
        """
        Return this guild's raid RSVP configuration.

        :param guild:
        :return:
        """
        result = {}
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select 
                    join_emoji,
                    join_emoji_type
                from raid_rsvp_configuration 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            rsvp_info_tuple = guild_info_cursor.fetchone()
            if rsvp_info_tuple is None:
                return None

            join_emoji, join_emoji_type = rsvp_info_tuple
            result["join_emoji"] = join_emoji
            if join_emoji_type == "custom":
                result["join_emoji"] = emoji_converter(guild, join_emoji)

        return result

    def configure_rsvp(
            self,
            guild: discord.Guild,
            join_emoji
    ):
        """
        Configure the guild's RSVP functionality.

        :param guild:
        :param join_emoji:
        :raises:
        :return:
        """
        emoji_type = "normal"
        emoji_stored_value = join_emoji
        if isinstance(join_emoji, discord.Emoji):
            emoji_type = "custom"
            emoji_stored_value = join_emoji.id

        with self.conn:
            self.conn.execute(
                """
                insert into raid_rsvp_configuration 
                (
                    guild_id,
                    join_emoji,
                    join_emoji_type
                )
                values (?, ?, ?);
                """,
                (
                    guild.id,
                    emoji_stored_value,
                    emoji_type
                )
            )

    def deactivate_rsvp(self, guild: discord.Guild):
        """
        Disable the guild's RSVP functionality by removing its configuration from the database.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from raid_rsvp where guild_id = ?;",
                (guild.id,)
            )

    def add_rsvp(
            self,
            guild: discord.Guild,
            creator: discord.Member,
            chat_channel: discord.TextChannel,
            command_msg_id,
            rsvp_channel: discord.TextChannel,
            rsvp_msg_id
    ):
        """
        Create a record for an RSVP.

        :param guild:
        :param creator:
        :param chat_channel:
        :param command_msg_id:
        :param rsvp_channel:
        :param rsvp_msg_id:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into raid_rsvp 
                (
                    guild_id,
                    creator_id,
                    chat_channel_id,
                    command_msg_id,
                    rsvp_channel_id,
                    rsvp_msg_id
                )
                values (?, ?, ?, ?, ?, ?);
                """,
                (
                    guild.id,
                    creator.id,
                    chat_channel.id,
                    command_msg_id,
                    rsvp_channel.id,
                    rsvp_msg_id
                )
            )

    def delete_rsvp_by_command(
            self,
            guild: discord.Guild,
            chat_channel: discord.TextChannel,
            command_msg_id
    ):
        """
        Delete an RSVP using its original command to look it up.

        :param guild:
        :param chat_channel:
        :param command_msg_id:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from raid_rsvp "
                "where guild_id = ? "
                "and chat_channel_id = ? "
                "and command_msg_id = ?;",
                (guild.id, chat_channel.id, command_msg_id)
            )

    def delete_rsvp_by_announcement(
            self,
            guild: discord.Guild,
            rsvp_channel: discord.TextChannel,
            rsvp_msg_id
    ):
        """
        Delete an RSVP using its announcement message to look it up.

        :param guild:
        :param rsvp_channel:
        :param rsvp_msg_id:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from raid_rsvp "
                "where guild_id = ? "
                "and rsvp_channel_id = ? "
                "and rsvp_msg_id = ?;",
                (guild.id, rsvp_channel.id, rsvp_msg_id)
            )
