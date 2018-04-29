import sqlite3
import discord

from bot.convert_using_guild import emoji_converter, role_converter


class EXGateDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        self.conn = sqlite3.connect(self.path_to_db)  # database can be initialized with ex_gate_initialization.sql

    def get_ex_gate_info(self, guild: discord.Guild):
        """
        Return some raw guild information required for the EX gating.

        Because we don't have a context object, we can't convert channel IDs to channels
        or role IDs to roles.
        :param guild:
        :return:
        """
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select 
                    disclaimer_channel_id, 
                    disclaimer_message_id, 
                    approve_emoji, 
                    ex_role_id, 
                    wait_time, 
                    approval_message_template
                from ex_gate 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            guild_info_tuple = guild_info_cursor.fetchone()
        if guild_info_tuple is None:
            return None

        result = dict(
            zip(
                [
                    "disclaimer_channel",
                    "disclaimer_message_id",
                    "approve_emoji",
                    "ex_role",
                    "wait_time",
                    "approval_message_template"
                ],
                guild_info_tuple
            )
        )

        # Convert the approve emoji to the appropriate type if it's a custom emoji.
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select approve_emoji_type
                from ex_gate 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            approve_emoji_type = guild_info_cursor.fetchone()[0]
        if approve_emoji_type == "custom":
            result["approve_emoji"] = emoji_converter(guild, result["approve_emoji"])

        # Other conversions.
        result["disclaimer_channel"] = guild.get_channel(result["disclaimer_channel"])
        result["ex_role"] = role_converter(guild, result["ex_role"])

        # Get the strings that are accepted by the guild for granting the EX channels.
        result["accepted_messages"] = []
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select accepted_message
                from ex_gate_accepted_message
                where guild_id = ?;
                """,
                (guild.id,)
            )
        result["accepted_messages"] = [accepted_message[0] for accepted_message in guild_info_cursor]

        return result

    def configure_ex_gating(self, guild: discord.Guild, disclaimer_channel: discord.TextChannel,
                            disclaimer_message_id, approve_emoji, ex_role: discord.Role,
                            wait_time: float, approval_message_template):
        """
        Configure the guild's EX gating.

        :param guild:
        :param disclaimer_channel:
        :param disclaimer_message_id:
        :param approve_emoji:
        :param ex_role:
        :param wait_time:
        :param approval_message_template:
        :raises:
        :return:
        """
        emoji_type = "normal"
        emoji_stored_value = approve_emoji
        if isinstance(approve_emoji, discord.Emoji):
            emoji_type = "custom"
            emoji_stored_value = approve_emoji.id

        with self.conn:
            self.conn.execute(
                """
                insert into ex_gate 
                (
                    guild_id, 
                    disclaimer_channel_id, 
                    disclaimer_message_id, 
                    approve_emoji, 
                    approve_emoji_type, 
                    ex_role_id, 
                    wait_time,
                    approval_message_template
                )
                values (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    guild.id,
                    disclaimer_channel.id,
                    disclaimer_message_id,
                    emoji_stored_value,
                    emoji_type,
                    ex_role.id,
                    wait_time,
                    approval_message_template
                )
            )

    def add_accepted_message(self, guild: discord.Guild, accepted_message):
        """
        The bot will accept this message from a user in the disclaimer channel.

        :param guild:
        :param accepted_message:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into ex_gate_accepted_message (guild_id, accepted_message) values(?, ?);
                """,
                (
                    guild.id,
                    accepted_message
                )
            )

    def clear_accepted_messages(self, guild: discord.Guild):
        """
        Remove all guild accepted messages from the database -- e.g. if a mistake was made entering them.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from ex_gate_accepted_message where guild_id = ?;",
                (guild.id,)
            )

    def remove_ex_gate_data(self, guild: discord.Guild):
        """
        Remove this guild's EX gating information from the database.

        :param guild:
        :return:
        """
        self.clear_accepted_messages(guild)
        with self.conn:
            self.conn.execute(
                "delete from ex_gate where guild_id = ?;",
                (guild.id,)
            )

