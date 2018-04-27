import sqlite3
import discord


class EXGateDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        self.conn = sqlite3.connect(self.path_to_db)  # database can be initialized with db_initialization.sql

    def get_ex_gate_info(self, guild):
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
                select disclaimer_channel_id, disclaimer_message_id, ex_role_id
                from ex_gate 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            guild_info_tuple = guild_info_cursor.fetchone()

        if guild_info_tuple is None:
            return None

        return dict(
            zip(
                ["disclaimer_channel_id", "disclaimer_message_id", "ex_role_id"],
                guild_info_tuple
            )
        )

    def register_guild(self, guild, disclaimer_channel: discord.TextChannel,
                       disclaimer_message: discord.Message, ex_role: discord.Role):
        """
        Configure the guild's EX gating.

        :param guild:
        :param disclaimer_channel:
        :param disclaimer_message:
        :param ex_role:
        :raises:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into ex_gate (guild_id, disclaimer_channel_id, disclaimer_message_id, ex_role_id)
                values (?, ?, ?, ?);
                """,
                (guild.id, disclaimer_channel.id, disclaimer_message.id, ex_role.id)
            )

    def remove_ex_gate_data(self, guild):
        """
        Remove this guild's EX gating information from the database.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from guild_standard_roles where guild_id = ?;",
                (guild.id,)
            )
