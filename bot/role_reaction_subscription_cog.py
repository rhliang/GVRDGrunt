import textwrap
import discord
from discord.ext.commands import command, has_permissions, BadArgument, EmojiConverter

__author__ = 'Richard Liang'


class RoleReactionSubscriptionCog():
    """
    A cog that handles role assignment in the GVRD guilds.

    This takes the form of watching a subscription message.
    When a particular reaction is added, the adding user gets a specified role added/removed.
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

    def get_bot_member(self, guild):
        """
        Helper that gets the bot's guild Member.

        :param guild:
        :return:
        """
        return guild.get_member(self.bot.user.id)

    @command(
        help="Configure role reaction subscription for the specified role.",
        aliases=["start_react_sub"]
    )
    @has_permissions(administrator=True)
    async def activate_role_reaction_subscription(
            self,
            ctx,
            role: discord.Role,
            channel: discord.TextChannel,
            subscription_message_id,
            toggle_emoji
    ):
        """
        Activate reaction-based role subscription.

        :param ctx:
        :param role:
        :param channel:
        :param subscription_message_id:
        :param toggle_emoji:
        :return:
        """
        emoji_converter = EmojiConverter()
        try:
            actual_emoji = await emoji_converter.convert(ctx, toggle_emoji)
        except BadArgument:
            actual_emoji = toggle_emoji

        self.db.configure_role_reaction_subscription(ctx.guild, channel, subscription_message_id, actual_emoji, role)
        message = await channel.get_message(subscription_message_id)
        try:
            await message.add_reaction(actual_emoji)
        except discord.Forbidden:
            await ctx.message.channel.send(
                f"{ctx.author.mention} Bot {ctx.guild.get_member(self.bot.user.id)} does not"
                f"have the appropriate permissions to add a reaction."
            )

        await ctx.message.channel.send(
            f"{ctx.author.mention} Reaction role subscription for this guild's {role} role has been "
            f"configured with {self.get_bot_member(ctx.guild).name}."
        )

    @command(help="Display the role reaction subscription configuration for the given role.")
    @has_permissions(manage_roles=True)
    @has_permissions(manage_nicknames=True)
    async def show_role_reaction_subscription(self, ctx, role: discord.Role):
        """
        Display the role reaction subscription configuration.

        :param ctx:
        :param role:
        :return:
        """
        subscription_info = self.db.get_subscription_info(ctx.guild, role)
        if subscription_info is None:
            await ctx.message.channel.send(f'{ctx.author.mention} Reaction subscription for {role} is not configured.')
            return

        await ctx.message.channel.send(
            self.summary_str_template.format(
                subscription_info["channel"],
                subscription_info["subscription_message_id"],
                subscription_info["toggle_emoji"],
                subscription_info["role"]
            )
        )

    @command(
        help="Display all of the role reaction subscription configuration for this guild.",
        aliases=["show_react_sub"]
    )
    @has_permissions(manage_roles=True)
    @has_permissions(manage_nicknames=True)
    async def show_all_role_reaction_subscriptions(self, ctx):
        """
        Display *all* role reaction subscription configuration for this guild.

        :param ctx:
        :param role:
        :return:
        """
        subscription_info_list = self.db.get_guild_subscription_info(ctx.guild)
        if len(subscription_info_list) == 0:
            await ctx.message.channel.send(f'{ctx.author.mention} No role subscription is configured.')
            return

        summaries = []
        for subscription_info in subscription_info_list:
            summaries.append(
                self.summary_str_template.format(
                    subscription_info["channel"],
                    subscription_info["subscription_message_id"],
                    subscription_info["toggle_emoji"],
                    subscription_info["role"]
                )
            )
        await ctx.message.channel.send("--------\n".join(summaries))

    @command(
        help="Clear the role reaction subscription configuration for the specified role.",
        aliases=["stop_react_sub"]
    )
    @has_permissions(administrator=True)
    async def disable_role_reaction_subscription(self, ctx, role: discord.Role):
        """
        Disable the role reaction subscription functionality for this guild and this role.

        :param ctx:
        :param role:
        :return:
        """
        subscription_info = self.db.get_subscription_info(ctx.guild, role)
        if subscription_info is None:
            await ctx.message.channel.send(f'{ctx.author.mention} Reaction subscription for {role} is not configured.')
            return

        self.db.remove_subscription_data(ctx.guild, role)
        message = await subscription_info["channel"].get_message(subscription_info["subscription_message_id"])
        try:
            await message.remove_reaction(subscription_info["toggle_emoji"], ctx.guild.get_member(self.bot.user.id))
        except discord.NotFound:
            pass
        await ctx.message.channel.send(
            f"{ctx.author.mention} Reaction role assignment functionality "
            f"for the {role} role is disabled for this guild."
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
            reason=f"Granted the {role} role by {self.get_bot_member(member.guild).name} via reaction"
        )

        if self.logging_cog is not None:
            await self.logging_cog.log_to_channel(
                member.guild,
                f"{member} was assigned the {role} role via reaction"
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
            reason=f"Removed the {role} role using {self.get_bot_member(member.guild).name} via reaction"
        )

        if self.logging_cog is not None:
            await self.logging_cog.log_to_channel(
                member.guild,
                f"Role {role} was removed from {member} via reaction"
            )

    async def toggle_role(self, member: discord.Member, role: discord.Role):
        """
        Remove the member from the given role.

        :param member:
        :param role:
        :return:
        """
        if role in member.roles:
            await self.remove_role(member, role)
        else:
            await self.assign_role(member, role)

    # Now build some listeners.
    async def reaction_clicked(self, payload):
        """
        Assigns the role to the user if a subscription message reaction is clicked.

        :param payload:
        :return:
        """
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        subscription_info = self.db.get_subscription_info_by_message_id(guild, payload.message_id)
        # Do nothing if the guild doesn't have subscription for this role configured.
        if subscription_info is None:
            return

        # Do nothing if the reaction is not the appropriate reaction.
        if isinstance(subscription_info["toggle_emoji"], discord.Emoji):
            if not payload.emoji.is_custom_emoji():
                return
            elif payload.emoji.id != subscription_info["toggle_emoji"].id:
                return
        else:
            if payload.emoji.is_custom_emoji():
                return
            elif str(payload.emoji) != subscription_info["toggle_emoji"]:
                return

        adding_member = guild.get_member(payload.user_id)
        await self.toggle_role(adding_member, subscription_info["role"])

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
