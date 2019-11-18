import textwrap
import asyncio
import discord
from discord.ext.commands import command, has_permissions, BadArgument, EmojiConverter, Cog

__author__ = 'Richard Liang'


class EXGateCog(Cog):
    """
    A cog that handles EX gating in the GVRD guilds.

    This takes the form of watching a disclaimer message in a disclaimer channel.
    When a particular reaction is added, the adding user gets the EX role added.  Or, if
    an affirmative message is typed in the disclaimer channel, the same thing happens.
    (All messages other than the disclaimer message get removed after 5 seconds.)
    """
    summary_str_template = textwrap.dedent(
        """\
        Disclaimer channel: {}
        Disclaimer message: {}
        Approve emoji: {} 
        EX role: {}
        Wait time before deleting messages in disclaimer channel (seconds): {}
        Message sent on approval:
        ----
        {}
        ----
        Accepted user responses:
        {}
        """
    )

    def __init__(self, bot, db, logging_cog=None):
        self.bot = bot
        self.db = db  # a EXGateDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike

    def get_bot_member(self, guild):
        """
        Helper that gets the bot's guild Member.

        :param guild:
        :return:
        """
        return guild.get_member(self.bot.user.id)

    @command()
    @has_permissions(administrator=True)
    async def activate_ex_gating(self,
                                 ctx,
                                 disclaimer_channel: discord.TextChannel,
                                 disclaimer_message_id,
                                 approve_emoji,
                                 ex_role: discord.Role,
                                 wait_time: float,
                                 approval_message_template):
        """
        Activate EX gating by adding this guild to the database.

        :param ctx:
        :param disclaimer_channel:
        :param disclaimer_message_id:
        :param approve_emoji:
        :param ex_role:
        :param wait_time:
        :param approval_message_template
        :return:
        """
        # First, check that the client can write to this channel and manage messages.
        channel_perms = disclaimer_channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if not channel_perms.send_messages:
            await ctx.message.channel.send(
                f'{ctx.author.mention} {self.get_bot_member(ctx.guild).name} '
                f'cannot write to channel {disclaimer_channel}.'
            )
            return
        elif not channel_perms.manage_messages:
            await ctx.message.channel.send(
                f'{ctx.author.mention} {self.get_bot_member(ctx.guild).name} needs Manage Messages '
                f'permissions on channel {disclaimer_channel}.'
            )
            return

        emoji_converter = EmojiConverter()
        try:
            actual_emoji = await emoji_converter.convert(ctx, approve_emoji)
        except BadArgument:
            actual_emoji = approve_emoji

        self.db.configure_ex_gating(ctx.guild, disclaimer_channel, disclaimer_message_id,
                                    actual_emoji, ex_role, wait_time, approval_message_template)
        await ctx.message.channel.send(
            f'{ctx.author.mention} EX gating for this guild has been '
            f'configured with {self.get_bot_member(ctx.guild).name}.'
        )

    @command(help="Display the guild EX gating configuration.")
    @has_permissions(manage_roles=True)
    @has_permissions(manage_nicknames=True)
    async def show_ex_gating(self, ctx):
        """
        Display the EX gating configuration.

        :param ctx:
        :return:
        """
        ex_gate_info = self.db.get_ex_gate_info(ctx.guild)
        if ex_gate_info is None:
            await ctx.message.channel.send(f'{ctx.author.mention} EX gating is not configured.')
            return

        accepted_messages_str = "(none)"
        if len(ex_gate_info["accepted_messages"]) > 0:
            accepted_messages_str = f" - {ex_gate_info['accepted_messages'][0]}"
            for accepted_message in ex_gate_info["accepted_messages"][1:]:
                accepted_messages_str += f"\n - {accepted_message}"

        await ctx.message.channel.send(
            self.summary_str_template.format(
                ex_gate_info["disclaimer_channel"],
                ex_gate_info["disclaimer_message_id"],
                ex_gate_info["approve_emoji"],
                ex_gate_info["ex_role"],
                ex_gate_info["wait_time"],
                ex_gate_info["approval_message_template"],
                accepted_messages_str
            )
        )

    @command()
    @has_permissions(administrator=True)
    async def add_ex_accepted_message(self, ctx, accepted_message):
        """
        Teach the bot to accept this message from a user in the disclaimer channel.

        :param ctx:
        :param role:
        :return:
        """
        ex_gate_info = self.db.get_ex_gate_info(ctx.guild)
        if ex_gate_info is None:
            await ctx.message.channel.send(f'{ctx.author.mention} EX gating is not configured.')
            return

        self.db.add_accepted_message(ctx.guild, accepted_message)
        await ctx.message.channel.send(
            f'{ctx.author.mention} Users can now type "{accepted_message}" '
            f'in the disclaimer channel to open the EX gate.'
        )

    @command(help="Clear the guild EX gating configuration.")
    @has_permissions(administrator=True)
    async def disable_ex_gating(self, ctx):
        """
        Disable EX gating for this guild.

        :param ctx:
        :return:
        """
        self.db.remove_ex_gate_data(ctx.guild)
        await ctx.message.channel.send(
            f"{ctx.author.mention} EX gating is disabled for this guild."
        )

    async def assign_ex_role(self, member: discord.Member):
        """
        Assign the member the guild's EX role.

        :param member:
        :return:
        """
        ex_gate_info = self.db.get_ex_gate_info(member.guild)
        if ex_gate_info is None:  # this isn't configured, so do nothing
            return

        ex_role = ex_gate_info["ex_role"]
        await member.edit(
            roles=list(set([ex_role] + member.roles)),
            reason=f"Granted the {ex_role} role by {self.get_bot_member(member.guild).name}"
        )

        if self.logging_cog is not None:
            await self.logging_cog.log_to_channel(
                member.guild,
                f"{member} was assigned the {ex_role} role"
            )

    # Now build some listeners.
    async def reaction_clicked(self, payload):
        """
        Assigns the EX role to the user if the disclaimer message reaction is clicked.

        :param payload:
        :return:
        """
        guild = self.bot.get_guild(payload.guild_id)
        ex_gate_info = self.db.get_ex_gate_info(guild)
        # Do nothing if the guild doesn't have EX gating active.
        if ex_gate_info is None:
            return

        # Do nothing if the message is not the disclaimer message.
        if str(payload.message_id) != ex_gate_info["disclaimer_message_id"]:  # the DB stores the ID as string
            return

        # Do nothing if the reaction is not the appropriate reaction.
        if isinstance(ex_gate_info["approve_emoji"], discord.Emoji):
            if not payload.emoji.is_custom_emoji():
                return
            elif payload.emoji.id != ex_gate_info["approve_emoji"].id:
                return
        else:
            if payload.emoji.is_custom_emoji():
                return
            elif str(payload.emoji) != ex_gate_info["approve_emoji"]:
                return

        adding_member = guild.get_member(payload.user_id)
        await self.assign_ex_role(adding_member)

        confirm = await ex_gate_info["disclaimer_channel"].send(
            ex_gate_info["approval_message_template"].format(adding_member.mention)
        )
        await asyncio.sleep(ex_gate_info["wait_time"])
        await confirm.delete()

    async def on_raw_reaction_add(self, payload):
        """
        Monitor for a reaction added on the guild's disclaimer message.

        Ignore all other reactions.

        :param payload:
        :return:
        """
        await self.reaction_clicked(payload)

    async def on_raw_reaction_remove(self, payload):
        """
        Monitor for a reaction removed on the guild's disclaimer message.

        Ignore all other reactions.

        :param payload:
        :return:
        """
        await self.reaction_clicked(payload)

    async def on_message(self, message):
        """
        Monitor for an affirmative message in the disclaimer channel; delete all messages after 5 seconds.

        :return:
        """
        # If this is a DM, do nothing.
        if message.guild is None:
            return

        ex_gate_info = self.db.get_ex_gate_info(message.guild)
        # Do nothing if the guild doesn't have EX gating active.
        if ex_gate_info is None:
            return

        # Do nothing if the message is not in the disclaimer channel.
        if message.channel != ex_gate_info["disclaimer_channel"]:
            return

        # Do nothing if the message is from the bot itself.
        if message.author == message.guild.get_member(self.bot.user.id):
            return

        # Having reached here, we're confident the message is from a proper member of the guild.
        if message.content.lower() in ex_gate_info["accepted_messages"]:
            await self.assign_ex_role(message.author)
            reply = await message.channel.send(
                ex_gate_info["approval_message_template"].format(message.author.mention)
            )
        else:
            if len(ex_gate_info["accepted_messages"]) == 0:
                reply_str = f"{message.author.mention} sorry, I don't understand any messages!"
            else:
                reply_str = (
                    f'{message.author.mention} sorry, I only understand '
                    f'the following messages: {", ".join(ex_gate_info["accepted_messages"])}'
                )
            reply = await message.channel.send(reply_str)

        await asyncio.sleep(ex_gate_info["wait_time"])
        await message.delete()
        await reply.delete()
