from operator import attrgetter
from collections import defaultdict
import discord
import re
from discord.ext.commands import command, has_permissions, BadArgument, EmojiConverter
from datetime import datetime, timezone

__author__ = 'Richard Liang'


class RaidFYICog():
    """
    A cog that handles raid FYI functionality in the GVRD guilds.

    When the .fyi command is issued in a chat channel, the remainder of the message is relayed to
    a corresponding RSVP channel.
    """
    def __init__(self, bot, db, logging_cog=None):
        self.bot = bot
        self.db = db  # a RaidFYIDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike

    @command(
        help="Configure raid FYI functionality.",
        aliases=["activate_fyi", "enable_fyi"]
    )
    @has_permissions(administrator=True)
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
    @has_permissions(administrator=True)
    async def disable_fyi(self, ctx):
        """
        Disable raid FYI functionality for this guild.

        :param ctx:
        :return:
        """
        self.db.deactivate_fyi(ctx.guild)
        await ctx.channel.send(f"{ctx.author.mention} Raid FYI functionality is now disabled.")

    @command(
        help="Configure raid FYI functionality.",
        aliases=["activate_enhanced_fyi", "enable_enhanced_fyi"]
    )
    @has_permissions(administrator=True)
    async def configure_enhanced_fyi(
            self,
            ctx,
            rsvp_emoji
    ):
        """
        Configure the raid FYI functionality for this guild.

        :param ctx:
        :param rsvp_emoji:
        :return:
        """
        emoji_converter = EmojiConverter()
        try:
            actual_emoji = await emoji_converter.convert(ctx, rsvp_emoji)
        except BadArgument:
            actual_emoji = rsvp_emoji

        self.db.activate_enhanced_fyi(ctx.guild, actual_emoji)
        await ctx.channel.send(f"{ctx.author.mention} Enhanced FYI functionality is now enabled.")

    @command(
        help="Deactivate raid FYI functionality.",
        aliases=["deactivate_enhanced_fyi"]
    )
    @has_permissions(administrator=True)
    async def disable_enhanced_fyi(self, ctx):
        """
        Disable raid FYI functionality for this guild.

        :param ctx:
        :return:
        """
        self.db.deactivate_enhanced_fyi(ctx.guild)
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
Timezone: {fyi_info["timezone"]}
Enhanced FYI functionality: {fyi_info["enhanced"]}
RSVP emoji: {fyi_info["rsvp_emoji"] if fyi_info["enhanced"] else "(None)"}
Channel mappings:
{mapping_list_str}
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

    @staticmethod
    def strip_fyi_message_content(message):
        """
        Strip the message contents of role mentions, member mentions, and the command prefix
        :param message:
        :return:
        """
        cleaned_content = message.clean_content
        strip_command_regex = re.compile(
            ".*?fyi +(.+)",
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

    @command(
        help="Post an FYI to the corresponding FYI channel.",
        rest_is_raw=True,
        aliases=["FYI", "Fyi", " FYI", " Fyi", " fyi"]
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

        self.db.add_fyi(
            ctx.guild,
            creator=ctx.author,
            timestamp=timestamp,
            chat_channel=ctx.channel,
            command_message_id=ctx.message.id,
            relay_channel=relay_channel,
            relay_message_id=relay_message.id
        )

        await ctx.message.add_reaction(fyi_info["fyi_emoji"])
        if fyi_info["enhanced"]:
            await ctx.message.add_reaction(fyi_info["rsvp_emoji"])
            await relay_message.add_reaction(fyi_info["rsvp_emoji"])

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

        # Unpack fyi_info.
        chat_channel, command_message_id, relay_channel, relay_message_id, timestamp, creator = fyi_info
        command_message = await chat_channel.get_message(command_message_id)
        relay_message = await relay_channel.get_message(relay_message_id)

        relay_message_text = self.build_relay_message_text(
            creator,
            timestamp,
            guild_fyi_info["timezone"],
            self.strip_fyi_message_content(command_message)
        )
        full_message_text = relay_message_text
        reactors = await self.get_all_reactors([command_message, relay_message])
        if len(reactors) > 0:
            interested_users_str = self.build_interested_users_list_string(reactors)
            full_message_text = self.RELAY_MESSAGE_TEMPLATE.format(
                relay_message_text=relay_message_text,
                interested_users_str=interested_users_str
            )
        await relay_message.edit(content=full_message_text)

    async def on_raw_reaction_add(self, payload):
        await self.update_fyi_interested(payload)

    async def on_raw_reaction_remove(self, payload):
        await self.update_fyi_interested(payload)

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

        # Unpack fyi_info.
        chat_channel, command_message_id, relay_channel, relay_message_id, timestamp, creator = fyi_info
        # Do nothing if this is the relay message (as this is edited by the bot).
        if edited_message_channel == relay_channel:
            return

        command_message = await chat_channel.get_message(command_message_id)
        relay_message = await relay_channel.get_message(relay_message_id)

        relay_message_text = self.build_relay_message_text(
            creator,
            timestamp,
            guild_fyi_info["timezone"],
            self.strip_fyi_message_content(command_message)
        )
        full_message_text = relay_message_text
        reactors = []
        if guild_fyi_info["enhanced"]:
            reactors = await self.get_all_reactors([command_message, relay_message])
        if len(reactors) > 0:
            interested_users_str = self.build_interested_users_list_string(reactors)
            full_message_text = self.RELAY_MESSAGE_TEMPLATE.format(
                relay_message_text=relay_message_text,
                interested_users_str=interested_users_str
            )
        await relay_message.edit(content=full_message_text)

        if guild_fyi_info["enhanced"]:
            # Ping all interested.
            audience = [x for x in reactors if x != creator]
            if len(audience) != 0:
                audience_str = " ".join([x.mention for x in audience])
                # Inset the relay message text.
                inset_relay_message_text = "> " + relay_message_text.replace("\n", "\n> ")
                reactor_ping = (f"{audience_str} the FYI you were interested in has been updated "
                                f"by {creator.mention}:\n"
                                f"{inset_relay_message_text}")
                await command_message.channel.send(reactor_ping)

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
        fyi_info = self.db.get_fyi(guild, channel, payload.message_id)
        if fyi_info is None:
            return

        # Unpack fyi_info.
        chat_channel, command_message_id, relay_channel, relay_message_id, timestamp, creator = fyi_info

        if chat_channel == channel and payload.message_id == command_message_id:
            relay_message = await relay_channel.get_message(relay_message_id)
            await relay_message.delete()

        self.db.delete_fyi(guild, chat_channel, command_message_id)

    async def on_raw_message_delete(self, payload):
        await self.delete_fyi(payload)

    # TOMORROW: what do we do about timing out messages?
