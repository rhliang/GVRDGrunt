import discord
from discord.ext.commands import command, Cog

from bot.bot_perms_cog import BotPermsChecker

__author__ = 'Richard Liang'


class GuildLoggingCog(BotPermsChecker, Cog):
    """
    A cog that handles guild-specific logging in the GVRD guilds.
    """
    def __init__(self, bot, db, bot_permissions_db):
        super(GuildLoggingCog, self).__init__(bot, bot_permissions_db)  # a BotPermsDB or workalike
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
    async def show_logging(self, ctx):
        """
        Display the guild logging configuration.

        :param ctx:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        logging_info = self.db.get_logging_info(ctx.guild)
        if logging_info is None:
            await ctx.message.channel.send(f'{ctx.author.mention} This guild does not have a log channel configured.')
            return

        logging_channel = logging_info["log_channel"]
        await ctx.message.channel.send(f'Log messages are sent to channel {logging_channel}')

    @command()
    async def configure_log_channel(self, ctx, log_channel: discord.TextChannel):
        """
        Configure this guild's log channel.

        :param ctx:
        :param log_channel:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        self.db.configure_guild_logging(ctx.guild, log_channel)
        await ctx.message.channel.send(
            f'{ctx.author.mention} Log channel is set to {log_channel}.'
        )

    @command(help="Clear the guild's logging configuration.")
    async def disable_logging(self, ctx):
        """
        Disable logging for this guild.

        :param ctx:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        self.db.clear_guild_logging(ctx.guild)
        await ctx.message.channel.send(f"{ctx.author.mention} Logging is disabled for this guild.")

    async def log_to_channel(self, guild, *args, **kwargs):
        """
        Send a log message to the guild's logging channel.

        If logging is not configured, do nothing.

        :param guild:
        :return:
        """
        logging_info = self.db.get_logging_info(guild)
        if logging_info is None:
            return

        log_channel = logging_info["log_channel"]
        await log_channel.send(*args, **kwargs)
