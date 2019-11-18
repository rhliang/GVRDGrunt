from operator import attrgetter
from collections import defaultdict
import discord
import re
from discord.ext.commands import command, BadArgument, EmojiConverter, Cog
from datetime import datetime, timezone

from bot.bot_perms_cog import BotPermsChecker

__author__ = 'Richard Liang'


class RaidFYICog(BotPermsChecker, Cog):
    """
    A cog that handles raid FYI functionality in the GVRD guilds.

    When the .fyi command is issued in a chat channel, the remainder of the message is relayed to
    a corresponding RSVP channel.
    """
    def __init__(self, bot, db, bot_permissions_db, logging_cog=None):
        super(RaidFYICog, self).__init__(bot, bot_permissions_db)  # a BotPermsDB or workalike
        self.db = db  # a RaidFYIDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike

    @command(
        help="Configure raid FYI functionality.",
        aliases=["activate_fyi", "enable_fyi"]
    )
    async def configure_fyi(
            self,
            ctx,
            fyi_emoji,
            timezone_str
    ):
        """
        Configure the raid FYI functionality for this guild.

        :param ctx:
        :param fyi_emoji:
        :param timezone_str: string describing the guild's timezone, as understood by pytz
        :return:
        """
        self.can_configure_bot_validator(ctx)

        emoji_converter = EmojiConverter()
        try:
            actual_emoji = await emoji_converter.convert(ctx, fyi_emoji)
        except BadArgument:
            actual_emoji = fyi_emoji

        self.db.configure_fyi(ctx.guild, actual_emoji, timezone_str)
        await ctx.channel.send(f"{ctx.author.mention} Raid FYI functionality is now enabled.")

    @command(
        help="Deactivate raid FYI functionality.",
        aliases=["deactivate_fyi"]
    )
    async def disable_fyi(self, ctx):
        """
        Disable raid FYI functionality for this guild.

        :param ctx:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        self.db.deactivate_fyi(ctx.guild)
        await ctx.channel.send(f"{ctx.author.mention} Raid FYI functionality is now disabled.")

    @command(
        help="Configure raid FYI functionality.",
        aliases=["activate_enhanced_fyi", "enable_enhanced_fyi"]
    )
    async def configure_enhanced_fyi(
            self,
            ctx,
            rsvp_emoji,
            cancelled_emoji,
            relay_to_chat: bool
    ):
        """
        Configure the enhanced raid FYI functionality for this guild.

        :param ctx:
        :param rsvp_emoji:
        :param cancelled_emoji:
        :param relay_to_chat:
        :return:
        """
        self.can_configure_bot_validator(ctx)

        emoji_converter = EmojiConverter()
        try:
            actual_rsvp_emoji = await emoji_converter.convert(ctx, rsvp_emoji)
        except BadArgument:
            actual_rsvp_emoji = rsvp_emoji

        try:
            actual_cancelled_emoji = await emoji_converter.convert(ctx, cancelled_emoji)
        except BadArgument:
            actual_cancelled_emoji = cancelled_emoji

        self.db.activate_enhanced_fyi(ctx.guild, actual_rsvp_emoji, actual_cancelled_emoji, relay_to_chat)
        await ctx.channel.send(f"{ctx.author.mention} Enhanced FYI functionality is now enabled.")

    @command(
        help="Deactivate raid FYI functionality.",
        aliases=["deactivate_enhanced_fyi"]
    )
    async def disable_enhanced_fyi(self, ctx):
        """
        Disable raid FYI functionality for this guild.

        :param ctx:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        self.db.deactivate_enhanced_fyi(ctx.guild)
        await ctx.channel.send(f"{ctx.author.mention} Raid FYI functionality is now disabled.")

    async def map_chat_to_fyi_helper(
            self,
            guild,
            commander: discord.Member,
            command_channel: discord.TextChannel,
            chat_channel: discord.TextChannel,
            fyi_channel: discord.TextChannel
    ):
        """
        Helper that maps a chat channel to an FYI channel.
        :param guild:
        :param commander:
        :param command_channel:
        :param chat_channel:
        :param fyi_channel:
        :return:
        """
        self.db.register_fyi_channel_mapping(guild, chat_channel, fyi_channel)
        await command_channel.send(f"{commander.mention} FYIs from {chat_channel} will be posted in {fyi_channel}.")

    @command(help="Map a chat channel to an FYI channel.", aliases=["mapchattofyi"])
    async def map_chat_to_fyi(self, ctx, chat_channel: discord.TextChannel, fyi_channel: discord.TextChannel):
        """
        Create a mapping from a chat channel to an FYI channel.

        :param ctx:
        :param chat_channel:
        :param fyi_channel:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        await self.map_chat_to_fyi_helper(ctx.guild, ctx.author, ctx.channel, chat_channel, fyi_channel)

    @command(help="Map a category to an FYI channel.", aliases=["mapcategorytofyi"])
    async def map_category_to_fyi(self, ctx, category: discord.CategoryChannel, fyi_channel: discord.TextChannel):
        """
        Create a mapping from a category to an FYI channel.

        :param ctx:
        :param category:
        :param fyi_channel:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        await ctx.channel.send(f"{ctx.author.mention} FYIs in all channels in {category} "
                               f"will be posted in {fyi_channel}.")
        self.db.register_fyi_category_mapping(ctx.guild, category, fyi_channel)
        for channel in category.channels:
            await self.map_chat_to_fyi_helper(ctx.guild, ctx.author, ctx.channel, channel, fyi_channel)

    async def on_guild_channel_create(self, channel: discord.TextChannel):
        """
        If this channel belongs to a mapped category, map it to the category's FYI channel.
        :param channel:
        :return:
        """
        category_mapping_info = self.db.get_fyi_category(channel.category)
        if category_mapping_info is None:
            return
        # This channel belongs to a mapped category, so we configure its FYI mapping.
        self.db.register_fyi_channel_mapping(channel.guild, channel, category_mapping_info["relay_channel"])
        if self.logging_cog is not None:
            await self.logging_cog.log_to_channel(
                channel.guild,
                f"New channel {channel} belongs to category {channel.category} "
                f"so FYI functionality has been auto-enabled; "
                f"it will log to channel {category_mapping_info['relay_channel']}."
            )

    @command(help="De-register FYI functionality for the specified chat channel")
    async def deregister_fyi_mapping(self, ctx, chat_channel: discord.TextChannel):
        """
        Deregister the FYI mapping from a chat channel.

        :param ctx:
        :param chat_channel:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        self.db.deregister_fyi_channel_mapping(ctx.guild, chat_channel)
        await ctx.channel.send(f"{ctx.author.mention} FYIs from {chat_channel} will now be ignored.")

    @command(help="De-register FYI functionality for all channels")
    async def deregister_all_fyi_mappings(self, ctx):
        """
        Deregister all raid FYI mappings.

        :param ctx:
        :return:
        """
        self.db.deregister_all_fyi_channel_mappings(ctx.guild)
        await ctx.channel.send(f"{ctx.author.mention} FYIs from all channels will now be ignored.")

    @command(help="Show FYI configuration", aliases=["show_fyi_config", "show_fyi_settings"])
    async def show_fyi_configuration(self, ctx):
        """
        Deregister all of this guild's chat channel FYI mappings.

        :param ctx:
        :return:
        """
        self.can_configure_bot_validator(ctx)
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

        category_mapping_str = "(none)"
        category_mappings = fyi_info["category_mappings"]
        if len(category_mappings) > 0:
            categories_sorted = sorted(category_mappings.keys(), key=lambda category: category.name)
            category_mapping_str = "\n".join(
                ["- {} -> {}".format(category, category_mappings[category]) for category in categories_sorted]
            )

        summary_message = f"""\
{ctx.author.mention}
FYI emoji: {fyi_info["fyi_emoji"]}
Timezone: {fyi_info["timezone"]}
Enhanced FYI functionality: {fyi_info["enhanced"]}
Relay to chat: {fyi_info["relay_to_chat"]}
RSVP emoji: {fyi_info["rsvp_emoji"] if fyi_info["enhanced"] else "(None)"}
Cancelled emoji: {fyi_info["cancelled_emoji"] if fyi_info["enhanced"] else "(None)"}
Channel mappings:
{mapping_list_str}
Category mappings:
{category_mapping_str}
"""

        await ctx.channel.send(summary_message)

    @staticmethod
    def build_relay_message_text(
            creator,
            timestamp,
            tz,
            message_content
    ):
        """
        Build a relay message for an FYI.

        :param creator:
        :param timestamp: an aware datetime object in UTC time
        :param tz: a tzinfo object
        :param message_content:
        :return:
        """
        relay_message_template = "**FYI from {creator} at {creation_time}:**\n{content}"
        guild_localized_timestamp = timestamp.astimezone(tz)
        relay_message = relay_message_template.format(
            creator=creator.mention,
            creation_time=guild_localized_timestamp.strftime("%I:%M%p on %Y %b %d"),
            content=message_content
        )
        return relay_message

    @staticmethod
    def build_interested_users_list_string(interested):
        """
        Build a string representation of the interested users.
        :param interested: a dictionary mapping member -> [reactions used by the user]
        :return:
        """
        sorted_interested = sorted(interested.keys(), key=attrgetter("display_name"))
        user_entries = []
        for person in sorted_interested:
            person_reaction_strings = []
            for emoji in interested[person]:
                if isinstance(emoji, str):
                    person_reaction_strings.append(emoji)
                else:  # this is a custom emoji
                    person_reaction_strings.append(f"<:{emoji.name}:{emoji.id}>")
            user_entries.append(f"{person.mention} ({', '.join(person_reaction_strings)})")

        interested_str = "\n".join(user_entries)
        return interested_str

    def strip_fyi_message_content(self, message):
        """
        Strip the message contents of role mentions, member mentions, and the command prefix
        :param message:
        :return:
        """
        cleaned_content = message.clean_content
        strip_command_regex = re.compile(
            "(?:^.?fyi +)?(.+)",
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
        return stripped_content

    FYI_ALIASES = ["FYI", "Fyi"]

    @command(
        help="Post an FYI to the corresponding FYI channel.",
        rest_is_raw=True,
        aliases=FYI_ALIASES
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

        stripped_content = self.strip_fyi_message_content(ctx.message)
        if stripped_content is None:
            return

        timestamp = datetime.now(timezone.utc)
        relay_channel = fyi_info["channel_mappings"][ctx.channel]
        relay_message_text = self.build_relay_message_text(
            ctx.author,
            timestamp,
            fyi_info["timezone"],
            stripped_content
        )
        relay_message = await relay_channel.send(relay_message_text)

        chat_relay_message_id = None
        chat_relay_message = None
        if fyi_info["relay_to_chat"]:
            chat_relay_message = await ctx.channel.send(relay_message_text)
            chat_relay_message_id = chat_relay_message.id

        self.db.add_fyi(
            ctx.guild,
            creator=ctx.author,
            fyi_text=ctx.message.content,
            timestamp=timestamp,
            chat_channel=ctx.channel,
            command_message_id=ctx.message.id,
            relay_channel=relay_channel,
            relay_message_id=relay_message.id,
            chat_relay_message_id=chat_relay_message_id
        )

        await ctx.message.add_reaction(fyi_info["fyi_emoji"])
        if fyi_info["enhanced"]:
            await ctx.message.add_reaction(fyi_info["rsvp_emoji"])
            await relay_message.add_reaction(fyi_info["rsvp_emoji"])
            if fyi_info["relay_to_chat"]:
                await chat_relay_message.add_reaction(fyi_info["rsvp_emoji"])

    async def get_all_reactors(self, messages):
        """
        Compile a dictionary of all users/members who reacted to the specified messages.
        :param messages: a list of messages
        :return:
        """
        reactors = defaultdict(set)
        for message in messages:
            for reaction in message.reactions:
                async for user in reaction.users():
                    if user == self.bot.user:
                        continue
                    reactors[user].add(reaction.emoji)
        return reactors

    RELAY_MESSAGE_TEMPLATE = "{relay_message_text}\n**Interested:**\n{interested_users_str}"

    async def update_fyi_helper(self, guild, fyi_info, tz):
        """
        Helper that updates an FYI when anything changes.

        :param guild:
        :param fyi_info: a dictionary as returned by RaidFYIDB.get_fyi
        :param tz: a Python timezone object as returned by pytz.timezone
        :return:
        """
        try:
            command_message = await fyi_info["chat_channel"].fetch_message(fyi_info["command_message_id"])
        except discord.errors.NotFound:
            return

        try:
            relay_message = await fyi_info["relay_channel"].fetch_message(fyi_info["relay_message_id"])
        except discord.errors.NotFound:
            return

        chat_relay_message = None
        if fyi_info.get("chat_relay_message_id") is not None:
            try:
                chat_relay_message = await fyi_info["chat_channel"].fetch_message(fyi_info["chat_relay_message_id"])
            except discord.errors.NotFound:
                return

        relay_message_text = self.build_relay_message_text(
            fyi_info["creator"],
            fyi_info["timestamp"],
            tz,
            self.strip_fyi_message_content(command_message)
        )
        full_message_text = relay_message_text
        fyi_messages = [command_message, relay_message]
        if chat_relay_message is not None:
            fyi_messages.append(chat_relay_message)
        reactors = await self.get_all_reactors(fyi_messages)
        if len(reactors) > 0:
            interested_users_str = self.build_interested_users_list_string(reactors)
            full_message_text = self.RELAY_MESSAGE_TEMPLATE.format(
                relay_message_text=relay_message_text,
                interested_users_str=interested_users_str
            )

        self.db.update_fyi(
            guild,
            command_message.channel,
            command_message.id,
            command_message.content,
            [x.id for x in reactors]
        )
        await relay_message.edit(content=full_message_text)
        if chat_relay_message is not None:
            await chat_relay_message.edit(content=full_message_text)

        return relay_message_text, reactors

    async def update_fyi_interested(self, payload):
        """
        Updates an FYI when a reaction is clicked.

        :param payload:
        :return:
        """
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        guild_fyi_info = self.db.get_fyi_info(guild)
        fyi_info = self.db.get_fyi(guild, guild.get_channel(payload.channel_id), payload.message_id)
        # Do nothing if this isn't an active FYI.
        if guild_fyi_info is None or not guild_fyi_info["enhanced"] or fyi_info is None:
            return
        await self.update_fyi_helper(guild, fyi_info, guild_fyi_info["timezone"])

    async def update_fyi_edited(self, payload):
        """
        Updates an FYI when the original is edited.

        :param payload:
        :return:
        """
        # The payload has a message_id and a channel_id, but not necessarily a guild ID!
        # Note: the payload won't have a channel_id until we move to v1.3.0 of discord.py.
        # edited_message_channel = self.bot.get_channel(payload.channel_id)
        edited_message_channel = self.bot.get_channel(int(payload.data["channel_id"]))
        if edited_message_channel is None:
            return
        guild = edited_message_channel.guild
        if guild is None:
            return
        guild_fyi_info = self.db.get_fyi_info(guild)
        fyi_info = self.db.get_fyi(guild, edited_message_channel, payload.message_id)
        # Do nothing if this isn't an active FYI, or if this is the relay message.
        if guild_fyi_info is None or fyi_info is None:
            return

        # Do nothing if this is a relay message (as this is edited by the bot).
        if (edited_message_channel == fyi_info["relay_channel"] or
                edited_message_channel == fyi_info["chat_channel"] and
                payload.message_id == fyi_info["chat_relay_message_id"]):
            return

        relay_message_text, reactors = await self.update_fyi_helper(guild, fyi_info, guild_fyi_info["timezone"])

        if guild_fyi_info["enhanced"]:
            # Ping all interested.
            audience = [x for x in reactors if x != fyi_info["creator"]]
            if len(audience) != 0:
                audience_str = " ".join([x.mention for x in audience])
                # Inset the relay message text.
                inset_relay_message_text = "> " + relay_message_text.replace("\n", "\n> ")
                reactor_ping = (f"{audience_str} the FYI you were interested in has been updated "
                                f"by {fyi_info['creator'].mention}:\n"
                                f"{inset_relay_message_text}")
                await fyi_info["chat_channel"].send(reactor_ping)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.update_fyi_interested(payload)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.update_fyi_interested(payload)

    @Cog.listener()
    async def on_raw_message_edit(self, payload):
        await self.update_fyi_edited(payload)

    async def delete_fyi(self, payload):
        """
        Delete an FYI (this removes it from the database also).

        :param payload:
        :return:
        """
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        guild_fyi_info = self.db.get_fyi_info(guild)
        fyi_info = self.db.get_fyi(guild, channel, payload.message_id)
        if fyi_info is None:
            return

        try:
            command_message = await fyi_info["chat_channel"].fetch_message(fyi_info["command_message_id"])
        except discord.errors.NotFound:
            command_message = None

        try:
            relay_message = await fyi_info["relay_channel"].fetch_message(fyi_info["relay_message_id"])
        except discord.errors.NotFound:
            relay_message = None

        chat_relay_message = None
        if fyi_info["chat_relay_message_id"] is not None:
            try:
                chat_relay_message = await fyi_info["chat_channel"].fetch_message(fyi_info["chat_relay_message_id"])
            except discord.errors.NotFound:
                chat_relay_message = None

        # Strike out any relay messages that are remaining.
        for relay_message in [x for x in [relay_message, chat_relay_message] if x is not None]:
            prior_content = relay_message.content
            await relay_message.edit(content="~~{}~~".format(prior_content))

        # Add the guild's "cancelled" emoji to any messages that are remaining.
        for fyi_message in [x for x in [command_message, relay_message, chat_relay_message] if x is not None]:
            await fyi_message.add_reaction(guild_fyi_info["cancelled_emoji"])

        # Send a ping to all who were interested.
        audience = set(fyi_info["interested"] + [fyi_info["creator"]])
        if len(audience) != 0:
            audience_str = " ".join([x.mention for x in audience])
            inset_fyi_text = "> " + fyi_info["edit_history"][-1].replace("\n", "\n> ")
            deletion_ping = (f"{audience_str} the FYI you were interested in has been removed:\n"
                             f"{inset_fyi_text}")
            await fyi_info["chat_channel"].send(deletion_ping)

        self.db.delete_fyi(guild, fyi_info["chat_channel"], fyi_info["command_message_id"])

    @Cog.listener()
    async def on_raw_message_delete(self, payload):
        await self.delete_fyi(payload)

    # TOMORROW: what do we do about timing out messages?
