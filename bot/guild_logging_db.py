import sqlite3
import discord


class GuildLoggingDB(object):
    """
    Handles persistent storage of guild logging information.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        self.conn = sqlite3.connect(self.path_to_db)  # database can be initialized with db_initialization.sql

    def get_logging_info(self, guild):
        """
        Return the guild's logging information.

        :param guild:
        :return:
        """
        with self.conn:
            guild_info_cursor = self.conn.execute(
                "select log_channel_id from guild_logging where guild_id = ?;",
                (guild.id,)
            )
            guild_info_tuple = guild_info_cursor.fetchone()

        if guild_info_tuple is None:
            return None

        return dict(
            zip(
                ["log_channel_id"],
                guild_info_tuple
            )
        )

    def configure_guild_logging(self, guild, log_channel: discord.TextChannel):
        """
        Configure the guild's logging channel.

        :param guild:
        :param log_channel:
        :raises:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into guild_logging (guild_id, log_channel_id)
                values (?, ?);
                """,
                (guild.id, log_channel.id)
            )

    def clear_guild_logging(self, guild):
        """
        Remove this guild's logging information from the database.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from guild_logging where guild_id = ?;",
                (guild.id,)
            )
