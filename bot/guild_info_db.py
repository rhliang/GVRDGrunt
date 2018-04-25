import sqlite3
import discord
from discord.ext.commands import RoleConverter


class GuildInfoDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        self.conn = sqlite3.connect(self.path_to_db)  # database can be initialized with db_initialization.sql

    def get_screenshot_handling_info(self, guild):
        """
        Return some raw guild information required for handling screenshots.

        Because we don't have a context object, we can't convert channel IDs to channels
        or role IDs to roles.
        :param guild:
        :return:
        """
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select screenshot_channel, help_channel, denied_message, welcome_role
                from guild_info 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            guild_info_tuple = guild_info_cursor.fetchone()

        if guild_info_tuple is None:
            return None

        return {
            "screenshot_channel_id": guild_info_tuple[0],
            "help_channel_id": guild_info_tuple[1],
            "denied_message": guild_info_tuple[2],
            "welcome_role_id": guild_info_tuple[3]
        }


    async def get_guild(self, ctx):
        """
        Return the dictionary of information corresponding to the specified guild.

        :param ctx: a discord.py context object
        :return:
        """
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select log_channel, screenshot_channel, help_channel, denied_message,
                welcome_role, instinct_role, mystic_role, 
                valor_role, welcome_message, welcome_channel 
                from guild_info 
                where guild_id = ?;
                """,
                (ctx.guild.id,)
            )
            guild_info_tuple = guild_info_cursor.fetchone()

        if guild_info_tuple is None:
            return None

        role_converter = RoleConverter()
        standard_roles = []
        mandatory_roles = []
        with self.conn:
            guild_roles_cursor = self.conn.execute(
                """
                select role_id, mandatory
                from guild_standard_roles
                where guild_id = ?;
                """,
                (ctx.guild.id,)
            )
            for role_id, mandatory in guild_roles_cursor:
                role = await role_converter.convert(ctx, str(role_id))
                if mandatory:
                    mandatory_roles.append(role)
                else:
                    standard_roles.append(role)

        log_channel = None
        screenshot_channel = None
        help_channel = None
        denied_message = guild_info_tuple[3]
        welcome_role = None
        instinct_role = None
        mystic_role = None
        valor_role = None
        welcome_message = guild_info_tuple[8]
        welcome_channel = None
        if guild_info_tuple[0] is not None:
            log_channel = ctx.guild.get_channel(guild_info_tuple[0])
        if guild_info_tuple[1] is not None:
            screenshot_channel = ctx.guild.get_channel(guild_info_tuple[1])
        if guild_info_tuple[2] is not None:
            help_channel = ctx.guild.get_channel(guild_info_tuple[2])
        if guild_info_tuple[4] is not None:
            welcome_role = await role_converter.convert(ctx, str(guild_info_tuple[4]))
        if guild_info_tuple[5] is not None:
            instinct_role = await role_converter.convert(ctx, str(guild_info_tuple[5]))
        if guild_info_tuple[6] is not None:
            mystic_role = await role_converter.convert(ctx, str(guild_info_tuple[6]))
        if guild_info_tuple[7] is not None:
            valor_role = await role_converter.convert(ctx, str(guild_info_tuple[7]))
        if guild_info_tuple[9] is not None:
            welcome_channel = ctx.guild.get_channel(guild_info_tuple[9])
        return {
            "log_channel": log_channel,
            "screenshot_channel": screenshot_channel,
            "help_channel": help_channel,
            "denied_message": denied_message,
            "welcome_role": welcome_role,
            "instinct_role": instinct_role,
            "mystic_role": mystic_role,
            "valor_role": valor_role,
            "welcome_message": welcome_message,
            "welcome_channel": welcome_channel,
            "standard_roles": standard_roles,
            "mandatory_roles": mandatory_roles
        }

    def register_guild(self, ctx):
        """
        Create a new, empty record for the guild.

        :param ctx:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into guild_info (guild_id) values(?);
                """,
                (ctx.guild.id,)
            )

    def set_channel(self, ctx, channel: discord.TextChannel, type):
        """
        Set the log channel for the guild that ctx comes from.

        :param ctx:
        :param channel:
        :param type: one of "log", "screenshot", or "help"
        :return:
        """
        if type not in ("log", "screenshot", "help"):
            raise discord.InvalidArgument('channel type must be one of "log", "screenshot", or "help"')
        with self.conn:
            self.conn.execute(
                f"""
                update guild_info
                set {type}_channel = ?
                where guild_id = ?;
                """,
                (
                    channel.id,
                    ctx.guild.id
                )
            )

    def set_denied_message(self, ctx, denied_message):
        """
        Set the message sent when requesting a new screenshot.

        :param ctx:
        :param denied_message:
        :return:
        """
        with self.conn:
            self.conn.execute(
                f"""
                update guild_info
                set denied_message = ?
                where guild_id = ?;
                """,
                (
                    denied_message,
                    ctx.guild.id
                )
            )

    def set_welcome_role(self, ctx, welcome_role: discord.Role):
        """
        Set the guild's welcome role.

        :param ctx:
        :param welcome_role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                update guild_info
                set welcome_role = ?
                where guild_id = ?;
                """,
                (
                    welcome_role.id,
                    ctx.guild.id
                )
            )

    def set_team_role(self, ctx, team, role: discord.Role):
        """
        Set the guild's team role.

        :param ctx:
        :param team:
        :param role:
        :return:
        """
        team_lower = team.lower()
        if team_lower not in ("instinct", "mystic", "valor"):
            raise discord.InvalidArgument('team must be one of "instinct", "mystic", or "valor" (case-insensitive)')
        with self.conn:
            self.conn.execute(
                f"""
                update guild_info
                set {team_lower}_role = ?
                where guild_id = ?;
                """,
                (
                    role.id,
                    ctx.guild.id
                )
            )

    def set_welcome(self, ctx, welcome_message, welcome_channel: discord.TextChannel):
        """
        Set the guild's welcome message and welcome channel.

        :param ctx:
        :param welcome_message:
        :param welcome_channel:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                update guild_info
                set welcome_message = ?,
                welcome_channel = ?
                where guild_id = ?;
                """,
                (
                    welcome_message,
                    welcome_channel.id,
                    ctx.guild.id
                )
            )

    def add_standard_role(self, ctx, role: discord.Role, mandatory: bool):
        """
        Add a guild role to the list of standard roles given to a user on verification.

        :param ctx:
        :param role:
        :param mandatory:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into guild_standard_roles (guild_id, role_id, mandatory) values(?, ?, ?);
                """,
                (
                    ctx.guild.id,
                    role.id,
                    mandatory
                )
            )
