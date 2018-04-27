import textwrap
import asyncio
import discord
from discord.ext.commands import command, has_permissions, BadArgument, RoleConverter

__author__ = 'Richard Liang'


class EXGateCog():
    """
    A cog that handles EX gating in the GVRD guilds.

    This takes the form of watching a disclaimer message in a disclaimer channel.
    When a reaction is added, the adding user gets the EX role added.  Or, if
    an affirmative message is typed in the disclaimer channel, the same thing happens.
    (All messages other than the disclaimer message get removed after 5 seconds.)
    """
    summary_str_template = textwrap.dedent(
        """\
        Disclaimer channel: {}
        Disclaimer message: {}
        EX role: {}
        """
    )

    # Emoji used to indicate agreement to the disclaimer.
    approve = "✅"

    def __init__(self, bot, db, logging_cog=None):
        self.bot = bot
        self.db = db  # a EXGateDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike

    @command()
    @has_permissions(administrator=True)
    async def activate_ex_gating(self, ctx, disclaimer_channel: discord.TextChannel,
                                 disclaimer_message: discord.Message,
                                 ex_role: discord.Role):
        """
        Activate EX gating by adding this guild to the database.

        :param ctx:
        :return:
        """
        self.db.register_guild(ctx.guild, disclaimer_channel, disclaimer_message, ex_role)
        await ctx.message.channel.send(
            f'{ctx.author.mention} EX gating for this guild has been configured with {self.bot.user.name}.'
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

        await ctx.message.channel.send(
            self.summary_str_template.format(
                ex_gate_info["disclaimer_channel_id"],
                ex_gate_info["disclaimer_message_id"],
                ex_gate_info["ex_role_id"]
            )
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

        ex_role = None
        for guild_role in member.guild.roles:
            if guild_role.id == ex_gate_info["ex_role_id"]:
                ex_role = guild_role

        await member.edit(
            roles=list(set([ex_role] + member.roles)),
            reason=f"Granted the {ex_role} role by {self.bot.user.name}"
        )

        if self.logging_cog is not None:
            self.logging_cog.log_to_channel(
                member.guild,
                f"{member} was assigned the {ex_role} role"
            )

    # Now build some listeners.
    async def on_reaction_add(self, reaction, user):
        """
        Monitor for a reaction on the guild's disclaimer message.

        :param reaction:
        :param user:
        :return:
        """
        ex_gate_info = self.db.get_ex_gate_info(reaction.message.guild)
        # Do nothing if the guild doesn't have EX gating active.
        if ex_gate_info is None:
            return

        # Do nothing if the message is not the disclaimer message.
        if reaction.message.id != ex_gate_info["disclaimer_message_id"]:
            return

        # Do nothing if the reaction is not the appropriate reaction.
        await self.assign_ex_role(reaction.message.guild.get_member(user.id))

    async def on_message(self, message):
        """
        Monitor for an affirmative message in the disclaimer channel; delete all messages after 5 seconds.

        :return:
        """
        ex_gate_info = self.db.get_ex_gate_info(message.guild)
        # Do nothing if the guild doesn't have EX gating active.
        if ex_gate_info is None:
            return

        # Do nothing if the message is not in the disclaimer channel.
        if message.channel.id != ex_gate_info["disclaimer_channel"]:
            return

        # Do nothing if the message is from the bot itself.
        if message.author == message.guild.get_member(self.bot.user.id):
            return

        # Having reached here, we're confident the message is from a proper member of the guild.
        reply = None
        if message.content.lower() in ("yes", "y"):
            await self.assign_ex_role(message.author)
            reply = await message.channel.send(f"{message.author.mention} done!")

        await asyncio.sleep(5.0)
        await message.delete()
        if reply is not None:
            await reply.delete()
