import discord
from discord.ext.commands import command, has_permissions, BadArgument, RoleConverter

__author__ = 'Richard Liang'


class GuildLoggingCog():
    """
    A cog that handles guild-specific logging in the GVRD guilds.
    """
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db  # a GuildLoggingDB or workalike

    def logging_configured(self, guild):
        """
        True if this guild's logging is configured; False otherwise.
        :return:
        """
        logging_info = self.db.get_logging_info(guild)
        return logging_info is not None

    @command(help="Display the guild's logging configuration.")
    @has_permissions(manage_roles=True)
    @has_permissions(manage_nicknames=True)
    async def show_logging(self, ctx):
        """
        Display the guild logging configuration.

        :param ctx:
        :return:
        """
        logging_info = self.db.get_logging_info(ctx.guild)
        if logging_info is None:
            await ctx.message.channel.send(f'{ctx.author.mention} This guild does not have a log channel configured.')
            return

        logging_channel = ctx.guild.get_channel(logging_info["log_channel_id"])
        await ctx.message.channel.send(f'Log messages are sent to channel {logging_channel}')

    @command()
    @has_permissions(administrator=True)
    async def configure_log_channel(self, ctx, log_channel: discord.TextChannel):
        """
        Configure this guild's log channel.

        :param ctx:
        :param log_channel:
        :return:
        """
        self.db.configure_guild_logging(ctx.guild, log_channel)
        await ctx.message.channel.send(
            f'{ctx.author.mention} Log channel is set to {log_channel}.'
        )

    @command(help="Clear the guild's logging configuration.")
    @has_permissions(administrator=True)
    async def disable_logging(self, ctx):
        """
        Disable logging for this guild.

        :param ctx:
        :return:
        """
        self.db.clear_guild_logging(ctx.guild)
        await ctx.message.channel.send(f"{ctx.author.mention} Logging is disabled for this guild.")

    async def log_to_channel(self, guild, message_string):
        """
        Send a log message to the guild's logging channel.

        If logging is not configured, do nothing.

        :param guild:
        :param message_string:
        :return:
        """
        logging_info = self.db.get_logging_info(guild)
        if logging_info is None:
            return

        log_channel = guild.get_channel(logging_info["log_channel_id"])
        await log_channel.send(message_string)
