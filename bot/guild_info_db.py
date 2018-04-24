import sqlite3
import discord
from discord.ext.commands import RoleConverter, TextChannelConverter


class GuildInfoDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        self.conn = sqlite3.connect(self.path_to_db)

    def initialize(self):
        """
        Creates the guild info table and the guild region roles table.
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                create table guild_info(
                    guild_id primary key,
                    log_channel,
                    welcome_role,
                    instinct_role,
                    mystic_role,
                    valor_role,
                    welcome_message,
                    welcome_channel
                );
                """
            )

            self.conn.execute(
                """
                create table guild_standard_roles(
                    role_id primary key,
                    guild_id
                );
                """
            )

    async def get_guild(self, ctx):
        """
        Return the dictionary of information corresponding to the specified guild.

        :param ctx: a discord.py context object
        :return:
        """
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select log_channel, welcome_role, instinct_role, mystic_role, 
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
        with self.conn:
            guild_roles_cursor = self.conn.execute(
                """
                select role_id
                from guild_standard_roles
                where guild_id = ?;
                """,
                (ctx.guild.id,)
            )
            guild_roles = [await role_converter.convert(ctx, str(row[0])) for row in guild_roles_cursor]

        channel_converter = TextChannelConverter()
        log_channel = None
        welcome_role = None
        instinct_role = None
        mystic_role = None
        valor_role = None
        welcome_message = guild_info_tuple[5]
        welcome_channel = None
        if guild_info_tuple[0] is not None:
            log_channel = await channel_converter.convert(ctx, str(guild_info_tuple[0]))
        if guild_info_tuple[1] is not None:
            welcome_role = await role_converter.convert(ctx, str(guild_info_tuple[1]))
        if guild_info_tuple[2] is not None:
            instinct_role = await role_converter.convert(ctx, str(guild_info_tuple[2]))
        if guild_info_tuple[3] is not None:
            mystic_role = await role_converter.convert(ctx, str(guild_info_tuple[3]))
        if guild_info_tuple[4] is not None:
            valor_role = await role_converter.convert(ctx, str(guild_info_tuple[4]))
        if guild_info_tuple[6] is not None:
            welcome_channel = await channel_converter.convert(ctx, str(guild_info_tuple[6]))
        return {
            "log_channel": log_channel,
            "welcome_role": welcome_role,
            "instinct_role": instinct_role,
            "mystic_role": mystic_role,
            "valor_role": valor_role,
            "welcome_message": welcome_message,
            "welcome_channel": welcome_channel,
            "standard_roles": guild_roles
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

    def set_log_channel(self, ctx, log_channel: discord.TextChannel):
        """
        Set the log channel for the guild that ctx comes from.

        :param ctx:
        :param channel:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                update guild_info
                set log_channel = ?
                where guild_id = ?;
                """,
                (
                    log_channel.id,
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
        assert team.lower() in ("instinct", "mystic", "valor")
        with self.conn:
            self.conn.execute(
                """
                update guild_info
                set {}_role = ?
                where guild_id = ?;
                """.format(team.lower()),
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

    def add_standard_role(self, ctx, role: discord.Role):
        """
        Add a guild role to the list of standard roles given to a user on verification.

        :param ctx:
        :param role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into guild_standard_roles (guild_id, role_id) values(?, ?);
                """,
                (
                    ctx.guild.id,
                    role.id
                )
            )
