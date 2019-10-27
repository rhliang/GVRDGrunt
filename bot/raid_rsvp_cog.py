import textwrap
import discord
import re
from discord.ext.commands import command, has_permissions, BadArgument, EmojiConverter
from datetime import datetime

__author__ = 'Richard Liang'


class RaidRSVPCog():
    """
    A cog that handles raid RSVP functionality in the GVRD guilds.

    When the .rsvp command is issued in a chat channel, the remainder of the message is relayed just
    as with an FYI, but a rollcall (as counted by reactions added to either the original message
    or the announcement) is also added.
    """
    def __init__(self, bot, db, fyi_db, logging_cog=None):
        self.bot = bot
        self.db = db  # a RaidRSVPDB or workalike
        self.fyi_db = fyi_db  # a RaidFYIDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike

    @command(
        help="Configure raid RSVP functionality.",
        aliases=["activate_rsvp", "enable_rsvp"]
    )
    @has_permissions(administrator=True)
    async def configure_rsvp(
            self,
            ctx,
            join_emoji
    ):
        """
        Configure the raid RSVP functionality for this guild.

        :param ctx:
        :param join_emoji:
        :return:
        """
        emoji_converter = EmojiConverter()
        try:
            actual_emoji = await emoji_converter.convert(ctx, join_emoji)
        except BadArgument:
            actual_emoji = join_emoji

        self.db.configure_rsvp(ctx.guild, actual_emoji)
        await ctx.channel.send(f"{ctx.author.mention} Raid RSVP functionality is now enabled.")

    @command(
        help="Deactivate raid RSVP functionality.",
        aliases=["deactivate_rsvp"]
    )
    @has_permissions(administrator=True)
    async def disable_rsvp(self, ctx):
        """
        Disable raid FYI functionality for this guild.

        :param ctx:
        :return:
        """
        self.db.deactivate_fyi(ctx.guild)
        await ctx.channel.send(f"{ctx.author.mention} Raid FYI functionality is now disabled.")

    @command(
        help="Post an RSVP to the corresponding FYI/RSVP channel.",
        rest_is_raw=True,
        aliases=["RSVP", "Rsvp"]
    )
    async def rsvp(self, ctx):
        """
        Post an RSVP from this channel to its corresponding FYI/RSVP channel.
        :param ctx:
        :return:
        """
        fyi_info = self.fyi_db.get_fyi_info(ctx.guild)
        if fyi_info is None:
            return
        if ctx.channel not in fyi_info["channel_mappings"]:
            return
        rsvp_info = self.db.get_rsvp_info(ctx.guild)
        if rsvp_info is None:
            return

        # Get the clean content of the message.
        cleaned_content = ctx.message.clean_content
        strip_command_regex = re.compile(
            ".*?rsvp +(.+)".format(self.bot.command_prefix),
            flags=re.IGNORECASE | re.DOTALL
        )
        try:
            stripped_clean_content_match = strip_command_regex.match(cleaned_content)
        except re.error:
            # Swallow this error and move on.
            return

        if stripped_clean_content_match is None:
            return
        stripped_content = stripped_clean_content_match.expand("\\1")
        if not stripped_content:  # this is blank
            return

        fyi_channel = fyi_info["channel_mappings"][ctx.channel]
        await fyi_channel.send(
            f"RSVP from {ctx.author.mention} at {datetime.now().strftime('%I:%M:%S%p')}:\n{stripped_content}\n\u200b"
        )
        await ctx.message.add_reaction(rsvp_info["join_emoji"])
