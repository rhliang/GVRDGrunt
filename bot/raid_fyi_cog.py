from operator import attrgetter
from collections import defaultdict
import re
import io
import json
from datetime import datetime, timezone, timedelta

import discord
from discord.ext.commands import command, BadArgument, EmojiConverter, Cog
from discord.ext import tasks
from botocore.exceptions import BotoCoreError

from bot.bot_perms_cog import BotPermsChecker
from bot.utils import break_up_long_message

__author__ = 'Richard Liang'


class RaidFYICog(BotPermsChecker, Cog):
    """
    A cog that handles raid FYI functionality in the GVRD guilds.

    When the .fyi command is issued in a chat channel, the remainder of the message is relayed to
    a corresponding RSVP channel.
    """
    def __init__(
            self,
            bot,
            db,
            clean_up_hours,
            clean_up_minutes,
            clean_up_seconds,
            bot_permissions_db,
            logging_cog=None
    ):
        super(RaidFYICog, self).__init__(bot, bot_permissions_db)  # a BotPermsDB or workalike
        self.db = db  # a RaidFYIDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike
        self.clean_up_fyis_loop.change_interval(
            hours=clean_up_hours,
            minutes=clean_up_minutes,
            seconds=clean_up_seconds
        )
        self.clean_up_fyis_loop.start()

    def cog_unload(self):
        self.clean_up_fyis_loop.cancel()

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
        self.db.deactivate_guild_fyi(ctx.guild)
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
            fyi_channel: discord.TextChannel,
            timeout_in_hours: int
    ):
        """
        Helper that maps a chat channel to an FYI channel.
        :param guild:
        :param commander:
        :param command_channel:
        :param chat_channel:
        :param fyi_channel:
        :param timeout_in_hours:
        :return:
        """
        self.db.register_fyi_channel_mapping(guild, chat_channel, fyi_channel, timeout_in_hours)
        await command_channel.send(
            f"{commander.mention} FYIs from {chat_channel} will be posted in {fyi_channel} "
            f"and time out after {timeout_in_hours} hours."
        )

    @command(help="Map a chat channel to an FYI channel.", aliases=["mapchattofyi"])
    async def map_chat_to_fyi(
            self,
            ctx,
            chat_channel: discord.TextChannel,
            fyi_channel: discord.TextChannel,
            timeout_in_hours: int
    ):
        """
        Create a mapping from a chat channel to an FYI channel.

        :param ctx:
        :param chat_channel:
        :param fyi_channel:
        :param timeout_in_hours:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        await self.map_chat_to_fyi_helper(
            ctx.guild,
            ctx.author,
            ctx.channel,
            chat_channel,
            fyi_channel,
            timeout_in_hours
        )

    @command(help="Map a category to an FYI channel.", aliases=["mapcategorytofyi"])
    async def map_category_to_fyi(
            self,
            ctx,
            category: discord.CategoryChannel,
            fyi_channel: discord.TextChannel,
            timeout_in_hours: int
    ):
        """
        Create a mapping from a category to an FYI channel.

        :param ctx:
        :param category:
        :param fyi_channel:
        :param timeout_in_hours:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        await ctx.channel.send(f"{ctx.author.mention} FYIs in all channels in {category} "
                               f"will be posted in {fyi_channel} and time out after {timeout_in_hours} hours.")
        self.db.register_fyi_category_mapping(ctx.guild, category, fyi_channel, timeout_in_hours)
        for channel in category.channels:
            await self.map_chat_to_fyi_helper(
                ctx.guild,
                ctx.author,
                ctx.channel,
                channel,
                fyi_channel,
                timeout_in_hours
            )

    @Cog.listener()
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
        self.db.register_fyi_channel_mapping(
            channel.guild,
            channel,
            category_mapping_info["relay_channel"],
            category_mapping_info["timeout_in_hours"]
        )
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

    @command(help="De-register FYI functionality for the specified chat channel")
    async def deregister_fyi_category_mapping(self, ctx, category: discord.CategoryChannel):
        """
        Deregister the FYI mapping from a category channel.

        :param ctx:
        :param category:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        self.db.deregister_fyi_category_mapping(ctx.guild, category)
        await ctx.channel.send(
            f"{ctx.author.mention} New channels created in {category} will no longer "
            f"be automatically configured for FYIs.")

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
            channel_entry_strings = []
            for chat in chats_sorted:
                mapping = channel_mappings[chat]
                duration_str = "(no FYI duration specified)"
                if mapping["timeout_in_hours"] is not None:
                    duration_str = f"(FYI duration {mapping['timeout_in_hours']}h)"
                channel_entry_strings.append(f"- {chat} -> {channel_mappings[chat]['relay_channel']} {duration_str}")
            mapping_list_str = "\n".join(channel_entry_strings)

        category_mapping_str = "(none)"
        category_mappings = fyi_info["category_mappings"]
        if len(category_mappings) > 0:
            categories_sorted = sorted(category_mappings.keys(), key=lambda category: category.name)
            category_entry_strings = []
            for category in categories_sorted:
                mapping = category_mappings[category]
                duration_str = "(no FYI duration specified)"
                if mapping["timeout_in_hours"] is not None:
                    duration_str = f"(FYI duration {mapping['timeout_in_hours']}h)"
                category_entry_strings.append(f"- {category} -> {mapping['relay_channel']} {duration_str}")
            category_mapping_str = "\n".join(category_entry_strings)

        summary_message = f"""\
{ctx.author.mention}
FYI emoji: {fyi_info["fyi_emoji"]}
Timezone: {fyi_info["timezone"]}
Enhanced FYI functionality: {fyi_info["enhanced"]}
Relay to chat: {fyi_info["relay_to_chat"]}
RSVP emoji: {fyi_info["rsvp_emoji"] if fyi_info["enhanced"] else "(None)"}
Cancelled emoji: {fyi_info["cancelled_emoji"] if fyi_info["enhanced"] else "(None)"}
"""
        channel_mappings_chunks = break_up_long_message(f"Channel mappings:\n{mapping_list_str}")
        category_mappings_chunks = break_up_long_message(f"Category mappings:\n{category_mapping_str}")

        for summary_chunk in [summary_message] + channel_mappings_chunks + category_mappings_chunks:
            await ctx.channel.send(summary_chunk)

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
        relay_message_template = "**FYI from {creator}** ({creation_time}):\n{content}"
        guild_localized_timestamp = timestamp.astimezone(tz)
        relay_message = relay_message_template.format(
            creator=creator.mention,
            creation_time=guild_localized_timestamp.strftime("%I:%M%p %Y/%m/%d"),
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

    RELAY_MESSAGE_TEMPLATE = "{relay_message_text}\n**Interested (add a {rsvp_emoji} if so):**\n{interested_users_str}"
    RELAY_MESSAGE_NONE_INTERESTED_YET = "(none so far)"

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
        mapping_info = fyi_info["channel_mappings"][ctx.channel]

        stripped_content = self.strip_fyi_message_content(ctx.message)
        if stripped_content is None:
            return

        timestamp = datetime.now(timezone.utc)
        relay_channel = mapping_info["relay_channel"]
        relay_message_text = self.build_relay_message_text(
            ctx.author,
            timestamp,
            fyi_info["timezone"],
            stripped_content
        )

        full_message_text = relay_message_text
        if fyi_info["enhanced"]:
            rsvp_emoji = fyi_info["rsvp_emoji"]
            rsvp_emoji_rendered = rsvp_emoji
            if not isinstance(rsvp_emoji, str):
                rsvp_emoji_rendered = f"<:{rsvp_emoji.name}:{rsvp_emoji.id}>"
            full_message_text = self.RELAY_MESSAGE_TEMPLATE.format(
                relay_message_text=relay_message_text,
                rsvp_emoji=rsvp_emoji_rendered,
                interested_users_str=self.RELAY_MESSAGE_NONE_INTERESTED_YET
            )

        relay_message = await relay_channel.send(full_message_text)
        chat_relay_message_id = None
        chat_relay_message = None
        if fyi_info["relay_to_chat"]:
            chat_relay_message = await ctx.channel.send(full_message_text)
            chat_relay_message_id = chat_relay_message.id

        expiry = None
        if mapping_info["timeout_in_hours"] is not None:
            expiry = timestamp + timedelta(hours=int(mapping_info["timeout_in_hours"]))
        self.db.add_fyi(
            ctx.guild,
            creator=ctx.author,
            fyi_text=ctx.message.content,
            timestamp=timestamp,
            expiry=expiry,
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

    async def update_fyi_helper(self, guild, fyi_info, tz, rsvp_emoji=None):
        """
        Helper that updates an FYI when anything changes.

        :param guild:
        :param fyi_info: a dictionary as returned by RaidFYIDB.get_fyi
        :param tz: a Python timezone object as returned by pytz.timezone
        :param rsvp_emoji: the guild's RSVP emoji, or None (if the guild does not have enhanced FYI on)
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
        reactors = []
        if rsvp_emoji is not None:
            fyi_messages = [command_message, relay_message]
            if chat_relay_message is not None:
                fyi_messages.append(chat_relay_message)
            reactors = await self.get_all_reactors(fyi_messages)

            rsvp_emoji_rendered = rsvp_emoji
            if not isinstance(rsvp_emoji, str):
                rsvp_emoji_rendered = f"<:{rsvp_emoji.name}:{rsvp_emoji.id}>"

            interested_users_str = self.RELAY_MESSAGE_NONE_INTERESTED_YET
            if len(reactors) > 0:
                interested_users_str = self.build_interested_users_list_string(reactors)
            full_message_text = self.RELAY_MESSAGE_TEMPLATE.format(
                relay_message_text=relay_message_text,
                rsvp_emoji=rsvp_emoji_rendered,
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
        if guild_fyi_info is None or not guild_fyi_info["enhanced"] or fyi_info is None or not fyi_info["active"]:
            return
        await self.update_fyi_helper(
            guild,
            fyi_info,
            guild_fyi_info["timezone"],
            guild_fyi_info["rsvp_emoji"]
        )

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
        if guild_fyi_info is None or fyi_info is None or not fyi_info["active"]:
            return

        # Do nothing if this is a relay message (as this is edited by the bot).
        if (edited_message_channel == fyi_info["relay_channel"] or
                edited_message_channel == fyi_info["chat_channel"] and
                payload.message_id == fyi_info["chat_relay_message_id"]):
            return

        relay_message_text, reactors = await self.update_fyi_helper(
            guild,
            fyi_info,
            guild_fyi_info["timezone"],
            guild_fyi_info["rsvp_emoji"]
        )

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

    async def deactivate_fyi(
            self,
            guild: discord.Guild,
            channel: discord.TextChannel,
            message_id,
            cancellation=False
    ):
        """
        Deactivate an FYI.

        This does not remove it from the database, it only marks it as inactive.

        :param guild:
        :param channel:
        :param message_id:
        :param cancellation: True if this is because the FYI was cancelled; False otherwise (i.e. it expired)
        :return:
        """
        guild_fyi_info = self.db.get_fyi_info(guild)
        fyi_info = self.db.get_fyi(guild, channel, message_id)
        if guild_fyi_info is None or fyi_info is None or not fyi_info["active"]:
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

        if cancellation:
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

        self.db.deactivate_fyi(guild, fyi_info["chat_channel"], fyi_info["command_message_id"])

    @Cog.listener()
    async def on_raw_message_delete(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        await self.deactivate_fyi(guild, channel, payload.message_id, cancellation=True)

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        matching_fyis = self.db.look_for_fyis(guild, channel, payload.message_ids)
        for fyi_info in matching_fyis:
            await self.deactivate_fyi(guild, channel, fyi_info["command_message_id"], cancellation=False)

    @staticmethod
    def serialize_fyi_info(fyi_info, human_readable=False):
        """
        Convert a dictionary summarizing an FYI (as returned by RaidFYIDB.get_fyi) into something JSON-serializable.
        :param fyi_info:
        :param human_readable:
        :return:
        """
        fyi = {}

        for key in fyi_info:
            fyi[key] = fyi_info[key]

        fyi["command_message_id"] = int(fyi["command_message_id"])
        fyi["relay_message_id"] = int(fyi["relay_message_id"])
        fyi["chat_relay_message_id"] = (int(fyi["chat_relay_message_id"])
                                        if fyi["chat_relay_message_id"] is not None else None)
        fyi["timestamp"] = fyi["timestamp"].isoformat()
        fyi["expiry"] = fyi["expiry"].isoformat()

        if human_readable:
            fyi["chat_channel"] = fyi["chat_channel"].name
            fyi["relay_channel"] = fyi["relay_channel"].name
            fyi["interested"] = [x.display_name for x in fyi["interested"]]
            fyi["creator"] = fyi["creator"].display_name
        else:
            fyi["chat_channel"] = fyi["chat_channel"].id
            fyi["relay_channel"] = fyi["relay_channel"].id
            fyi["interested"] = [x.id for x in fyi["interested"]]
            fyi["creator"] = fyi["creator"].id

        return fyi

    @staticmethod
    def make_discord_file_from_json(fileify_me, filename):
        """
        Helper that takes a serializable Python object and converts it into a JSON discord.File object.

        :param fileify_me:
        :param filename:
        :return:
        """
        return discord.File(
            io.BytesIO(json.dumps(fileify_me, indent=4).encode("utf8")),
            filename=filename
        )

    @command(help="Show expired FYIs")
    async def get_inactive_fyis(self, ctx):
        """
        Show all of this guild's inactive FYIs.
        :param ctx:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        inactive_fyis = self.db.get_inactive_fyis(ctx.guild)

        human_readable = []
        machine_readable = []
        for fyi in inactive_fyis:
            human_readable.append(self.serialize_fyi_info(fyi, True))
            machine_readable.append(self.serialize_fyi_info(fyi, False))

        reply = f"{ctx.author.mention} This guild has no inactive FYIs."
        jsons = None
        if len(inactive_fyis) > 0:
            reply = f"{ctx.author.mention} All of this guild's inactive FYIs:"
            jsons = [
                self.make_discord_file_from_json(
                    human_readable,
                    "inactive_human_readable.json"
                ),
                self.make_discord_file_from_json(
                    machine_readable,
                    "inactive.json"
                )
            ]
        async with ctx.channel.typing():
            await ctx.channel.send(reply, files=jsons)

    def get_expired_fyis_helper(self, guild: discord.Guild):
        """
        Helper to get all expired FYIs for this guild.
        :param guild:
        :return:
        """
        expired_by = datetime.now(timezone.utc)
        expired_fyis = self.db.get_expired_fyis(guild, expired_by)
        human_readable = [self.serialize_fyi_info(x, True) for x in expired_fyis]
        machine_readable = [self.serialize_fyi_info(x, False) for x in expired_fyis]

        message_text = "There are no expired FYIs to clean up."
        jsons = None
        if len(expired_fyis) > 0:
            message_text = "The following FYIs are expired:"
            jsons = [
                self.make_discord_file_from_json(
                    human_readable,
                    f"expired_{expired_by.isoformat()}_human_readable.json"
                ),
                self.make_discord_file_from_json(
                    machine_readable,
                    f"expired_{expired_by.isoformat()}.json"
                )
            ]
        return message_text, jsons, expired_fyis, expired_by

    @command(help="Show expired FYIs")
    async def get_expired_fyis(self, ctx):
        """
        Show all of this guild's expired FYIs.
        :param ctx:
        :return:
        """
        self.can_configure_bot_validator(ctx)
        message_text, jsons, _, _ = self.get_expired_fyis_helper(ctx.guild)
        reply = f"{ctx.author.mention} {message_text}"
        async with ctx.channel.typing():
            await ctx.channel.send(reply, files=jsons)

    async def clean_up_fyis_helper(self, guild, message_coro, caller=None):
        """
        Helper for cleaning up FYIs.
        :param guild:
        :param message_coro:
        :param caller: a discord.Member or None
        :return:
        """
        message_text, jsons, expired_fyis, _ = self.get_expired_fyis_helper(guild)
        message_to_send = message_text if caller is None else f"{caller.mention} {message_text}"
        if message_coro is not None:
            await message_coro(message_to_send, files=jsons)

        if len(expired_fyis) > 0:
            if message_coro is not None:
                await message_coro("Cleaning up...")
            # Now actually clean up the FYIs.
            try:
                for fyi_info in expired_fyis:
                    self.db.delete_fyi(guild, fyi_info["chat_channel"], fyi_info["command_message_id"])
                if message_coro is not None:
                    await message_coro("... done.")
            except BotoCoreError as e:
                if message_coro is not None:
                    await message_coro(f"There was a database error while deleting these FYIs:\n{str(e)}")
                raise

    @command(help="Clean up expired and inactive FYIs.")
    async def clean_up_fyis(self, ctx):
        """
        Clean up all expired and inactive FYIs for this guild.
        :return:
        """
        self.can_configure_bot_validator(ctx)
        await self.clean_up_fyis_helper(ctx.guild, ctx.channel.send, caller=ctx.author)

    @tasks.loop()  # set a proper loop interval at initialization
    async def clean_up_fyis_loop(self):
        """
        Background task that cleans up all expired and inactive FYIs.
        :return:
        """
        for guild in self.bot.guilds:
            guild_logging_coro = None
            if self.logging_cog is not None:
                async def guild_logging_coro(*args, **kwargs):
                    await self.logging_cog.log_to_channel(guild, *args, **kwargs)
            await self.clean_up_fyis_helper(guild, guild_logging_coro, caller=None)

    @clean_up_fyis_loop.before_loop
    async def before_clean_up_fyis(self):
        await self.bot.wait_until_ready()
