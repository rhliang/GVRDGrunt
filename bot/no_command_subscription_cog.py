import textwrap
import asyncio
import csv
from io import BytesIO, StringIO
import discord
from discord.ext.commands import command, has_permissions, TextChannelConverter

from bot.convert_using_guild import role_converter_from_name, get_matching_roles_case_insensitive

__author__ = 'Richard Liang'


class NoCommandSubscriptionCog():
    """
    A cog that handles role subscription in the GVRD guilds.

    This takes the form of watching for messages in a subscription channel.
    When a message is sent, the message is parsed to see if it matches one of the
    roles that can be subscribed to (this is defined by administrators).  If it does,
    the sending member is added to that role; if not, a reply is sent saying that it
    didn't work.

    All messages other than the initial message get removed after 5 seconds.
    """

    def __init__(self, bot, db, logging_cog=None):
        self.bot = bot
        self.db = db  # a NoCommandSubscriptionDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike

    @command()
    @has_permissions(administrator=True)
    async def activate_no_command_subscription(
            self,
            ctx,
            subscription_channel: discord.TextChannel,
            instruction_message_text,
            wait_time: float
    ):
        """
        Activate no-command subscription for this guild.

        :param ctx:
        :param subscription_channel:
        :param instruction_message_text:
        :param wait_time:
        :return:
        """
        # First, check that the client can write to this channel and manage messages.
        channel_perms = subscription_channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if not channel_perms.send_messages:
            await ctx.message.channel.send(
                f'{ctx.author.mention} {ctx.guild.get_member(self.bot.user.id)} '
                f'cannot write to channel {subscription_channel}.'
            )
            return
        elif not channel_perms.manage_messages:
            await ctx.message.channel.send(
                f'{ctx.author.mention} {ctx.guild.get_member(self.bot.user.id)} needs Manage Messages '
                f'permissions on channel {subscription_channel}.'
            )
            return

        instruction_message = await subscription_channel.send(instruction_message_text)
        self.db.activate_no_command_subscription(
            ctx.guild,
            subscription_channel,
            instruction_message_text,
            instruction_message.id,
            wait_time
        )

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription for this guild has been '
            f'configured with {ctx.guild.get_member(self.bot.user.id).name}.'
        )

    @command()
    @has_permissions(administrator=True)
    async def change_no_command_subscription_instructions(
            self,
            ctx,
            new_instructions: str
    ):
        """
        Change the instruction message text.

        :param ctx:
        :param new_instructions:
        :return:
        """
        config = self.db.get_no_command_subscription_settings(ctx.guild)
        if config is None:
            await ctx.message.channel.send(f'{ctx.author.mention} No-command subscription is not configured.')
            return

        instruction_message = await config["subscription_channel"].get_message(config["instruction_message_id"])
        try:
            await instruction_message.edit(content=new_instructions)
        except discord.HTTPException:
            raise
        self.db.change_instruction_message(ctx.guild, new_instructions)

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription instruction message now reads "{new_instructions}".'
        )

    @command()
    @has_permissions(administrator=True)
    async def change_no_command_subscription_wait(
            self,
            ctx,
            new_wait_time: float
    ):
        """
        Change the wait time the bot uses before deleting messages.

        :param ctx:
        :param new_wait_time:
        :return:
        """
        config = self.db.get_no_command_subscription_settings(ctx.guild)
        if config is None:
            await ctx.message.channel.send(f'{ctx.author.mention} No-command subscription is not configured.')
            return

        self.db.change_wait_time(ctx.guild, new_wait_time)
        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription now waits {new_wait_time} seconds before deleting messages.'
        )

    @command()
    @has_permissions(administrator=True)
    async def disable_no_command_subscription(self, ctx):
        """
        Disable no-command subscription for this guild.

        :param ctx:
        :return:
        """
        guild_settings = self.db.get_no_command_subscription_settings(ctx.guild)
        if guild_settings is None:
            await ctx.message.channel.send(f'{ctx.author.mention} No-command subscription is not configured.')
            return

        self.db.disable_no_command_subscription(ctx.guild)

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription for this guild has been disabled.'
        )

    @command()
    @has_permissions(manage_roles=True)
    async def register_roles_csv(self, ctx):
        """
        Activate no-command subscription for roles in an attached CSV file.

        The CSV file should be a single column with header "role_name" and just strings
        matching the guild's role names exactly, case-sensitive.

        :param ctx:
        :return:
        """
        guild_settings = self.db.get_no_command_subscription_settings(ctx.guild)
        if guild_settings is None:
            await ctx.message.channel.send(f'{ctx.author.mention} No-command subscription is not configured.')
            return

        csv_attachment = ctx.message.attachments[0]  # raises an exception if it isn't there, that's fine
        csv_contents_raw = BytesIO()
        await csv_attachment.save(csv_contents_raw)
        csv_contents = StringIO(csv_contents_raw.getvalue().decode("utf-8"))

        roles_to_register = []
        roles_csv = csv.DictReader(csv_contents)
        for row in roles_csv:
            role = role_converter_from_name(ctx.guild, row["role_name"])
            if role is not None:
                roles_to_register.append(role)

        self.db.register_roles(ctx.guild, roles_to_register)
        roles_str = "(none)"
        if len(roles_to_register) > 0:
            roles_str = f" - {roles_to_register[0]}"
            for role in roles_to_register[1:]:
                roles_str += f"\n - {role}"

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription for the following roles has been '
            f'registered with {ctx.guild.get_member(self.bot.user.id).name}:\n\n'
            f'{roles_str}'
        )

    @command()
    @has_permissions(manage_roles=True)
    async def register_role(self, ctx, role: discord.Role, *channels):
        """
        Activate no-command subscription for the specified role.

        If any channels are specified after the role, they're registered as channels that
        this role enables you to see.

        :param ctx:
        :return:
        """
        guild_settings = self.db.get_no_command_subscription_settings(ctx.guild)
        if guild_settings is None:
            await ctx.message.channel.send(f'{ctx.author.mention} No-command subscription is not configured.')
            return

        channel_converter = TextChannelConverter()
        channel_list = [await channel_converter.convert(ctx, raw_channel) for raw_channel in channels]

        self.db.register_role(ctx.guild, role, channel_list)

        channel_str = ""
        if len(channel_list) > 0:
            channel_str = "  This role is associated with channels:\n"
            for channel in channel_list:
                channel_str += f"\n - {channel}"

        reply = (f'{ctx.author.mention} No-command subscription for role {role} has been '
                 f'configured with {ctx.guild.get_member(self.bot.user.id).name}.')
        reply += channel_str

        await ctx.message.channel.send(reply)

    @command()
    @has_permissions(manage_roles=True)
    async def deregister_role(self, ctx, role: discord.Role):
        """
        De-register this role for no-command subscription.

        :param ctx:
        :return:
        """
        self.db.deregister_role(ctx.guild, role)

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription for role {role} has been '
            f'deregistered with {ctx.guild.get_member(self.bot.user.id).name}.'
        )

    @command()
    @has_permissions(manage_roles=True)
    async def deregister_all_roles(self, ctx):
        """
        De-register all roles for no-command subscription.

        :param ctx:
        :return:
        """
        self.db.deregister_all_roles(ctx.guild)

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription for all roles has been '
            f'deregistered with {ctx.guild.get_member(self.bot.user.id).name}.'
        )

    settings_template = textwrap.dedent(
        """\
        Subscription channel: {}
        Wait time: {}
        Instruction message ID: {}
        Instruction message text:
        ----
        {}
        ----
        Roles registered for no-command subscription:
        {}
        """
    )

    @command()
    @has_permissions(manage_roles=True)
    async def show_no_command_settings(self, ctx):
        """
        Show all no-command subscription settings.

        :param ctx:
        :return:
        """
        guild_settings = self.db.get_no_command_subscription_settings(ctx.guild)
        if guild_settings is None:
            await ctx.message.channel.send(f'{ctx.author.mention} No-command subscription is not configured.')
            return

        # This returns a dictionary.
        guild_settings = self.db.get_no_command_subscription_settings(ctx.guild)

        roles_str = "(none)"
        if len(guild_settings["roles"]) > 0:
            roles_str = ""
            for role, channels in guild_settings["roles"].items():
                roles_str += f' - {role}'
                if len(channels) > 0:
                    roles_str += f' ({", ".join([x.name for x in channels])})'
                roles_str += "\n"

        await ctx.message.channel.send(
            self.settings_template.format(
                guild_settings["subscription_channel"],
                guild_settings["wait_time"],
                guild_settings["instruction_message_id"],
                guild_settings["instruction_message_text"],
                roles_str
            )
        )

    async def assign_role(self, member: discord.Member, role: discord.Role):
        """
        Assign the member the given role.

        :param member:
        :param role:
        :return:
        """
        await member.edit(
            roles=list(set([role] + member.roles)),
            reason=f"Granted the {role} role by {member.guild.get_member(self.bot.user.id).name} "
                   f"via no-command subscription"
        )

        if self.logging_cog is not None:
            await self.logging_cog.log_to_channel(
                member.guild,
                f"{member} was assigned the {role} role via no-command subscription"
            )

    async def remove_role(self, member: discord.Member, role: discord.Role):
        """
        Remove the member from the given role.

        :param member:
        :param role:
        :return:
        """
        new_roles = [x for x in member.roles if x != role]
        await member.edit(
            roles=new_roles,
            reason=f"Removed the {role} role using {member.guild.get_member(self.bot.user.id).name} "
                   f"via no-command subscription"
        )

        if self.logging_cog is not None:
            await self.logging_cog.log_to_channel(
                member.guild,
                f"{member} removed the {role} role via no-command subscription"
            )

    async def on_message(self, message):
        """
        Monitor for an affirmative message in the disclaimer channel; delete all messages after 5 seconds.

        :return:
        """
        guild_settings = self.db.get_no_command_subscription_settings(message.guild)

        # Do nothing if the guild doesn't have no-command subscription active.
        if guild_settings is None:
            return

        # Do nothing if the message is not in the subscription channel.
        if message.channel != guild_settings["subscription_channel"]:
            return

        # Do nothing if the message is from the bot itself.
        if message.author == message.guild.get_member(self.bot.user.id):
            return

        # Having reached here, we're confident the message is from a proper member of the guild.
        # We have to handle a few cases:
        # - if the user typed a name of a role, search for all roles with that name, case-insensitive.
        #     a) if there's only one matching name, toggle it
        #     b) if there's several and it matches one exactly, case-sensitive, toggle that role
        #     c) if there's several and it doesn't match any of them, tell them so
        # - if what the user typed does not match a role, split it into words and try all of them
        roles_to_toggle = []
        ambiguous_roles = []

        raw_role_string = message.clean_content
        whole_thing_matched = False
        matching_roles = get_matching_roles_case_insensitive(message.guild, raw_role_string)
        possible_roles = [x for x in matching_roles if x in guild_settings["roles"]]
        if len(possible_roles) == 1:  # we found an unambiguous match
            roles_to_toggle = possible_roles
            whole_thing_matched = True
        elif len(possible_roles) > 1:  # ambiguous match
            ambiguous_roles.append((raw_role_string, possible_roles))
            whole_thing_matched = True

        # Having reached here, if we haven't found any kind of a match, we start looking at the
        # words in the string.
        unmatched_raw_roles = []
        raw_role_words = raw_role_string.split()
        if not whole_thing_matched and len(raw_role_words) == 1:
            unmatched_raw_roles = [raw_role_string]

        elif not whole_thing_matched and len(raw_role_words) > 1:
            for raw_role_word in raw_role_string.split():
                matching_roles = get_matching_roles_case_insensitive(message.guild, raw_role_word)
                possible_roles = [x for x in matching_roles if x in guild_settings["roles"]]
                if len(possible_roles) == 1:
                    roles_to_toggle.append(possible_roles[0])
                elif len(possible_roles) > 1:
                    ambiguous_roles.append((raw_role_word, possible_roles))
                else:  # no possible roles
                    unmatched_raw_roles.append(raw_role_word)

        # Having reached here, we can:
        # - toggle all roles in roles_to_toggle
        # - report all roles in ambiguous_roles with all possible matches and ask the user to say which one exactly
        # - report all not-found roles and unregistered roles

        replies = []
        async with message.channel.typing():
            for role in roles_to_toggle:
                if role in message.author.roles:  # remove the role from the member
                    await self.remove_role(message.author, role)
                    reply_str = f'You have unsubscribed from "{role}".'
                    if role.mentionable:
                        reply_str += f'  You will no longer receive notifications when `@{role}` is used.'
                    if len(guild_settings["roles"][role]) > 0:
                        channel_list_str = ""
                        for channel in guild_settings["roles"][role]:
                            channel_list_str += f"\n - {channel.name}"
                        reply_str += f'  This means you will no longer see channels:{channel_list_str}'

                else:  # add the role to the member
                    await self.assign_role(message.author, role)
                    reply_str = f'You have subscribed to "{role}".'
                    if role.mentionable:
                        reply_str += f'  You will now receive notifications when `@{role}` is used.'
                    if len(guild_settings["roles"][role]) > 0:
                        channel_list_str = ""
                        for channel in guild_settings["roles"][role]:
                            channel_list_str += f"\n - {channel.name}"
                        reply_str += f'  You should now be able to see channels:{channel_list_str}'

                replies.append(reply_str)

            for raw_role_string, possible_roles in ambiguous_roles:
                possible_roles_str = f" - `{possible_roles[0].name}`"
                for possible_role in possible_roles[1:]:
                    possible_roles_str += f"\n - `{possible_role.name}`"
                replies.append(
                    f'I can\'t find a precise match for `{raw_role_string}`; ' 
                    f'possible matches are:\n{possible_roles_str}'
                )

            if len(ambiguous_roles) + len(roles_to_toggle) == 0 and len(raw_role_words) > 1:
                # Nothing matched at all, so add the whole string to the list of unmatched roles.
                unmatched_raw_roles.append(raw_role_string)
            if len(unmatched_raw_roles) > 0:
                no_match_str = f" - `{unmatched_raw_roles[0]}`"
                for unmatched_raw_role in unmatched_raw_roles[1:]:
                    no_match_str += f"\n - `{unmatched_raw_role}`"
                replies.append(f"I couldn't find any subscriptions for:\n{no_match_str}")

            all_replies_str = "\n\n".join(replies)
            reply_text = f"{message.author.mention}:\n\n{all_replies_str}"
            reply = await message.channel.send(reply_text)

        await asyncio.sleep(guild_settings["wait_time"])
        await message.delete()
        await reply.delete()
