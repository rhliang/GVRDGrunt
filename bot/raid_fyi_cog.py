import textwrap
import discord
import re
from discord.ext.commands import command, has_permissions, BadArgument, EmojiConverter
from datetime import datetime

__author__ = 'Richard Liang'


class RaidFYICog():
    """
    A cog that handles raid FYI functionality in the GVRD guilds.

    When the .fyi command is issued in a chat channel, the remainder of the message

    """
    summary_str_template = textwrap.dedent(
        """\
        Channel: {}
        Subscription message: {}
        Approve emoji: {} 
        Role: {}
        """
    )

    def __init__(self, bot, db, logging_cog=None):
        self.bot = bot
        self.db = db  # a RoleReactionSubscriptionDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike

    @command(
        help="Configure raid FYI functionality.",
        aliases=["activate_fyi", "enable_fyi"]
    )
    @has_permissions(administrator=True)
    async def configure_fyi(
            self,
            ctx,
            fyi_emoji
    ):
        """
        Configure the raid FYI functionality for this guild.

        :param ctx:
        :param fyi_emoji:
        :return:
        """
        emoji_converter = EmojiConverter()
        try:
            actual_emoji = await emoji_converter.convert(ctx, fyi_emoji)
        except BadArgument:
            actual_emoji = fyi_emoji

        self.db.configure_fyi(ctx.guild, actual_emoji)
        await ctx.channel.send(f"{ctx.author.mention} Raid FYI functionality is now enabled.")

    @command(
        help="Deactivate raid FYI functionality.",
        aliases=["deactivate_fyi"]
    )
    @has_permissions(administrator=True)
    async def disable_fyi(self, ctx):
        """
        Disable raid FYI functionality for this guild.

        :param ctx:
        :return:
        """
        self.db.deactivate_fyi(ctx.guild)
        await ctx.channel.send(f"{ctx.author.mention} Raid FYI functionality is now disabled.")

    @command(help="Map a chat channel to an FYI channel.", aliases=["mapchattofyi"])
    @has_permissions(administrator=True)
    async def map_chat_to_fyi(self, ctx, chat_channel: discord.TextChannel, fyi_channel: discord.TextChannel):
        """
        Create a mapping from a chat channel to an FYI channel.

        :param ctx:
        :param chat_channel:
        :param fyi_channel:
        :return:
        """
        self.db.register_fyi_channel_mapping(ctx.guild, chat_channel, fyi_channel)
        await ctx.channel.send(f"{ctx.author.mention} FYIs from {chat_channel} will be posted in {fyi_channel}.")

    @command(help="De-register FYI functionality for the specified chat channel")
    @has_permissions(administrator=True)
    async def deregister_fyi_mapping(self, ctx, chat_channel: discord.TextChannel):
        """
        Deregister the FYI mapping from a chat channel.

        :param ctx:
        :param chat_channel:
        :return:
        """
        self.db.deregister_fyi_channel_mapping(ctx.guild, chat_channel)
        await ctx.channel.send(f"{ctx.author.mention} FYIs from {chat_channel} will now be ignored.")

    @command(help="De-register FYI functionality for all channels")
    @has_permissions(administrator=True)
    async def deregister_all_fyi_mappings(self, ctx):
        """
        Deregister all raid FYI mappings.

        :param ctx:
        :return:
        """
        self.db.deregister_all_fyi_channel_mappings(ctx.guild)
        await ctx.channel.send(f"{ctx.author.mention} FYIs from all channels will now be ignored.")

    @command(help="Show FYI configuration", aliases=["show_fyi_config", "show_fyi_settings"])
    @has_permissions(manage_nicknames=True)
    async def show_fyi_configuration(self, ctx):
        """
        Deregister all of this guild's chat channel FYI mappings.

        :param ctx:
        :return:
        """
        fyi_info = self.db.get_fyi_info(ctx.guild)
        if fyi_info is None:
            await ctx.channel.send(f"{ctx.author.mention} Raid FYI functionality is not configured.")
            return

        mapping_list_str = "(none)"
        channel_mappings = fyi_info["channel_mappings"]
        if len(channel_mappings) > 0:
            chats_sorted = sorted(channel_mappings.keys(), key=lambda channel: channel.name)
            mapping_list_str = "\n".join(
                ["- {} -> {}".format(chat, channel_mappings[chat]) for chat in chats_sorted]
            )

        summary_message = f"""\
{ctx.author.mention}
FYI emoji: {fyi_info["fyi_emoji"]}
Channel mappings:
{mapping_list_str}
"""

        await ctx.channel.send(summary_message)

    @command(
        help="Post an FYI to the corresponding FYI channel.",
        rest_is_raw=True,
        aliases=["FYI", "Fyi"]
    )
    async def fyi(self, ctx):
        """
        Post an FYI from this channel to its corresponding FYI channel.
        :param ctx:
        :return:
        """
        fyi_info = self.db.get_fyi_info(ctx.guild)
        if fyi_info is None:
            return
        if ctx.channel not in fyi_info["channel_mappings"]:
            return

        # Get the clean content of the message.
        cleaned_content = ctx.message.clean_content
        strip_command_regex = re.compile(
            ".*?fyi +(.+)".format(self.bot.command_prefix),
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
        # await fyi_channel.send(
        #     f"FYI from {ctx.author.mention} at {datetime.now().strftime('%I:%M:%S%p')}:\n{stripped_content}\n\u200b"
        # )
        await fyi_channel.send(f"FYI from {ctx.author.mention}:\n{stripped_content}")

        await ctx.message.add_reaction(fyi_info["fyi_emoji"])

