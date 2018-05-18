import textwrap
import asyncio
import csv
from io import StringIO
import discord
from discord.ext.commands import command, has_permissions, TextChannelConverter

from bot.convert_using_guild import role_converter_from_name

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
            instruction_message,
            wait_time: float):
        """
        Activate no-command subscription for this guild.

        :param ctx:
        :param subscription_channel:
        :param instruction_message:
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

        self.db.activate_no_command_subscription(
            ctx.guild,
            subscription_channel,
            instruction_message,
            wait_time
        )
        await subscription_channel.send(instruction_message)

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription for this guild has been '
            f'configured with {self.get_bot_member(ctx.guild).name}.'
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
    @has_permissions(administrator=True)
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
        csv_contents = StringIO()
        await csv_attachment.save(csv_contents)

        roles_to_register = []
        roles_csv = csv.DictReader(csv_contents)
        for row in roles_csv:
            role = role_converter_from_name(row["role_name"])
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
            f'registered with {self.get_bot_member(ctx.guild).name}:\n\n'
            f'{roles_str}'
        )

    @command()
    @has_permissions(administrator=True)
    async def register_role(self, ctx, role: discord.Role, *channels):
        """
        Activate no-command subscription for the specified role.

        If any channels are specified after the role, they're registered as channels that
        this role enables you to see.

        :param ctx:
        :return:
        """
        channel_converter = TextChannelConverter()
        channel_list = [channel_converter.convert(ctx, raw_channel) for raw_channel in channels]

        self.db.register_role(ctx.guild, role, channel_list)

        channel_str = ""
        if len(channel_list) > 0:
            channel_str = "  This role is associated with channels:\n"
            for channel in channel_list:
                channel_str += f"\n - {channel}"

        reply = (f'{ctx.author.mention} No-command subscription for role {role} has been '
                 f'configured with {self.get_bot_member(ctx.guild).name}.')
        reply += channel_str

        await ctx.message.channel.send(reply)

    @command()
    @has_permissions(administrator=True)
    async def deregister_role(self, ctx, role: discord.Role):
        """
        De-register this role for no-command subscription.

        :param ctx:
        :return:
        """
        self.db.deregister_role(ctx.guild, role)

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription for role {role} has been '
            f'deregistered with {self.get_bot_member(ctx.guild).name}.'
        )

    @command()
    @has_permissions(administrator=True)
    async def deregister_all_roles(self, ctx):
        """
        De-register all roles for no-command subscription.

        :param ctx:
        :return:
        """
        self.db.deregister_all_roles(ctx.guild)

        await ctx.message.channel.send(
            f'{ctx.author.mention} No-command subscription for all roles has been '
            f'deregistered with {self.get_bot_member(ctx.guild).name}.'
        )

    settings_template = textwrap.dedent(
        """\
        Subscription channel: {}
        Wait time: {}
        Instruction message:
        ----
        {}
        ----
        Roles registered for no-command subscription:
        {}
        """
    )

    @command()
    @has_permissions(administrator=True)
    async def show_no_command_settings(self, ctx):
        """
        Show all no-command subscription settings.

        :param ctx:
        :return:
        """
        # This returns a dictionary.
        guild_settings = self.db.get_no_command_subscription_settings(ctx.guild)

        roles_str = "(none)"
        if len(guild_settings["roles"]) > 0:
            roles_str = ""
            for role, channels in guild_settings["roles"].iteritems():
                roles_str += f' - {role}'
                if len(channels) > 0:
                    roles_str = f' ({", ".join(channels)})'
                roles_str += "\n"

        await ctx.message.channel.send(
            self.settings_template.format(
                guild_settings["subscription_channel"],
                guild_settings["wait_time"],
                guild_settings["instruction_message"],
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
            reason=f"Granted the {role} role by {self.get_bot_member(member.guild).name} via no-command subscription"
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
            reason=f"Removed the {role} role using {self.get_bot_member(member.guild).name} via no-command subscription"
        )

        if self.logging_cog is not None:
            await self.logging_cog.log_to_channel(
                member.guild,
                f"Role {role} was removed from {member} via no-command subscription"
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
        role = role_converter_from_name(message.content)
        if role is None or role not in guild_settings["roles"]:
            reply_str = f'{message.author.mention} sorry, I couldn\'t find any subscriptions by that name!'

        elif role in message.author.roles:  # remove the role from the member
            await self.remove_role(message.author, role)
            reply_str = f'{message.author.mention} You have unsubscribed from "{role}".'
            if role.mentionable:
                reply_str += f'  You will no longer receive notifications when `@{role}` is used.'
            if len(guild_settings["roles"][role]) > 0:
                reply_str += f'  You have unsubscribed from channels {" ,".join(guild_settings["roles"][role])}.'

        else:  # add the role to the member
            await self.assign_role(message.author, role)
            reply_str = f'{message.author.mention} You have subscribed to "{role}".'
            if role.mentionable:
                reply_str += f'  You will now receive notifications when `@{role}` is used.'
            if len(guild_settings["roles"][role]) > 0:
                reply_str += f'  You have subscribed to channels {" ,".join(guild_settings["roles"][role])}.'

        reply = await message.channel.send(reply_str)

        await asyncio.sleep(guild_settings["wait_time"])
        await message.delete()
        await reply.delete()
