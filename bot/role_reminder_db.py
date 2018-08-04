import sqlite3
import discord

from bot.convert_using_guild import role_converter


# create table role_reminder(
#     guild_id primary key,
#     reminder_channel_id,
#     reminder_message,
#     wait_time,
#     reminded_role_id
# );
#
# create table guild_verified_role(
#     role_id primary key,
#     guild_id
# );
#
# create table guild_suggested_role(
#     role_id primary key,
#     guild_id
# );
class RoleReminderDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    reminder_fields = (
        "reminder_channel",
        "reminder_message",
        "wait_time",
        "reminded_role"
    )

    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        # The database can be initialized with role_reaction_subscription_initialization.sql
        self.conn = sqlite3.connect(self.path_to_db)

    def get_role_reminder_info(self, guild: discord.Guild):
        """
        Return a dictionary of the guild's role reminder configuration.

        :param guild:
        :return:
        """
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select 
                    reminder_channel_id,
                    reminder_message,
                    wait_time,
                    reminded_role_id
                from role_reminder 
                where guild_id = ?
                """,
                (guild.id,)
            )
            guild_info_tuple = guild_info_cursor.fetchone()

        if guild_info_tuple is None:
            return None

        result = dict(zip(self.reminder_fields, guild_info_tuple))
        result["reminder_channel"] = guild.get_channel(result["reminder_channel"])
        result["reminded_role"] = role_converter(guild, result["reminded_role"])

        with self.conn:
            verified_roles_cursor = self.conn.execute(
                """
                select role_id
                from guild_verified_role
                where guild_id = ?;
                """,
                (guild.id,)
            )
            verified_roles = [role_converter(guild, row[0]) for row in verified_roles_cursor]
        result["verified_roles"] = verified_roles

        with self.conn:
            suggested_roles_cursor = self.conn.execute(
                """
                select role_id
                from guild_suggested_role
                where guild_id = ?;
                """,
                (guild.id,)
            )
            suggested_roles = [role_converter(guild, row[0]) for row in suggested_roles_cursor]

        result["suggested_roles"] = suggested_roles
        return result

    def configure_role_reminder(
            self,
            guild: discord.Guild,
            reminder_channel: discord.TextChannel,
            reminder_message,
            wait_time: int,
            reminded_role: discord.Role
    ):
        """
        Configure the guild's role reminder functionality.

        :param guild:
        :param reminder_channel:
        :param reminder_message:
        :param wait_time:
        :param reminded_role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into role_reminder 
                (
                    guild_id, 
                    reminder_channel_id,
                    reminder_message, 
                    wait_time, 
                    reminded_role_id
                )
                values (?, ?, ?, ?, ?);
                """,
                (
                    guild.id,
                    reminder_channel.id,
                    reminder_message,
                    wait_time,
                    reminded_role.id
                )
            )

    def add_verified_role(
            self,
            guild: discord.Guild,
            role: discord.Role
    ):
        """
        Add a verified role (i.e. a user with one of these is a verified user) for this guild.

        :param guild:
        :param role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into guild_verified_role 
                (
                    guild_id,
                    role_id
                )
                values (?, ?);
                """,
                (
                    guild.id,
                    role.id
                )
            )

    def add_suggested_role(
            self,
            guild: discord.Guild,
            role: discord.Role
    ):
        """
        Add a suggested role for this guild.

        :param guild:
        :param role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into guild_suggested_role 
                (
                    guild_id,
                    role_id
                )
                values (?, ?);
                """,
                (
                    guild.id,
                    role.id
                )
            )

    def remove_role_reminder_data(self, guild: discord.Guild):
        """
        Remove the specified guild's role reminder configuration.

        Note that this does not clear the guild's verified or suggested
        roles.  Thus if the role reminder configuration is cleared and
        re-entered, all the same verified and suggested roles will be
        configured.

        :param guild:
        :param role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from role_reminder where guild_id = ?;",
                (guild.id,)
            )

    def remove_verified_role(self, guild: discord.Guild, verified_role: discord.Role):
        """
        Remove this verified role from the guild.

        :param guild:
        :param verified_role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from guild_verified_role where guild_id = ? and role_id = ?;",
                (guild.id, verified_role.id)
            )

    def clear_verified_roles(self, guild: discord.Guild):
        """
        Remove all verified roles for this guild.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from guild_verified_role where guild_id = ?;",
                (guild.id,)
            )

    def remove_suggested_role(self, guild: discord.Guild, suggested_role: discord.Role):
        """
        Remove this suggested role from the guild.

        :param guild:
        :param suggested_role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from guild_suggested_role where guild_id = ? and role_id = ?;",
                (guild.id, suggested_role.id)
            )

    def clear_suggested_roles(self, guild: discord.Guild):
        """
        Remove all suggested roles for this guild.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from guild_suggested_role where guild_id = ?;",
                (guild.id,)
            )
