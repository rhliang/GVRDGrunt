# coding=utf-8
import textwrap
import discord
from bot import settings

__author__ = 'Richard Liang'


class VerificationCog():
    """
    A cog that handles verification of users in the GVRD guilds.
    """
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db  # a GuildInfoDB object or workalike

    @discord.ext.commands.command()
    @discord.ext.commands.has_permissions(administrator=True)
    async def register_guild(self, ctx):
        """
        Register this guild with the bot.
        :param ctx:
        :return:
        """
        self.db.register_guild(ctx)
        await ctx.message.channel.send(
            '{} This guild has been registered with {} and may now be configured.'.format(
                ctx.author.mention,
                self.bot.user.name
            )
        )

    async def guild_registered(self, ctx):
        """
        Confirms that the guild in question has been registered in the database.

        This will be used before every command, meaning that the first thing you do
        in a guild will have to be registering it with the bot.

        :param guild:
        :return:
        """
        guild_info = await self.db.get_guild(ctx)
        return guild_info is not None

    @discord.ext.commands.command()
    @discord.ext.commands.has_permissions(administrator=True)
    async def configure_log_channel(self, ctx, channel: discord.TextChannel):
        """
        Set the channel that we log to for the guild that this command was run in.

        :param ctx:
        :param channel:
        :return:
        """
        if not await self.guild_registered(ctx):
            await ctx.message.channel.send(
                '{} The guild must first be registered with the bot.'.format(ctx.author.mention)
            )
            return

        # First, check that the client can write to this channel.
        channel_perms = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if not channel_perms.send_messages:
            await ctx.message.channel.send(
                '{} {} cannot write to channel {}.'.format(ctx.author.mention, self.bot.user.name, channel)
            )
            return

        self.db.set_log_channel(ctx, channel)

        await ctx.message.channel.send(
            '{} {} will log to channel {}.'.format(ctx.author.mention, self.bot.user.name, channel)
        )

    @discord.ext.commands.command()
    @discord.ext.commands.has_permissions(administrator=True)
    async def configure_welcome_role(self, ctx, role: discord.Role):
        """
        Set this guild's welcome role.

        :param ctx:
        :param team:
        :param role:
        :return:
        """
        if not await self.guild_registered(ctx):
            await ctx.message.channel.send(
                '{} The guild must first be registered with the bot.'.format(ctx.author.mention)
            )
            return

        self.db.set_welcome_role(ctx, role)
        await ctx.message.channel.send(
            "{} This guild's welcome role has been set to: {}".format(
                ctx.author.mention,
                role.id
            )
        )

    @discord.ext.commands.command()
    @discord.ext.commands.has_permissions(administrator=True)
    async def configure_guild_team(self, ctx, team, role: discord.Role):
        """
        Update the guild information in the database with the given team's snowflake.

        :param ctx:
        :param team:
        :param role:
        :return:
        """
        if not await self.guild_registered(ctx):
            await ctx.message.channel.send(
                '{} The guild must first be registered with the bot.'.format(ctx.author.mention)
            )
            return

        if team.lower() not in ("instinct", "mystic", "valor"):
            await ctx.message.channel.send(
                '{} Team must be one of "instinct", "mystic", or "valor".'.format(ctx.author.mention)
            )
            return

        self.db.set_team_role(ctx, team, role)
        await ctx.message.channel.send(
            '{} Guild information has been updated: {} role is {}.'.format(
                ctx.author.mention,
                team.lower(),
                role.id
            )
        )

    @discord.ext.commands.command()
    @discord.ext.commands.has_permissions(administrator=True)
    async def configure_guild_welcome(self, ctx, welcome_channel: discord.TextChannel, welcome_message):
        """
        Configure how this guild welcomes newly verified members.

        The welcome message will be sent with a ping in the specified channel.
        It should be a Python template string with a single {} where we will insert the
        ping.

        :param ctx:
        :param welcome_channel:
        :param welcome_message:
        :return:
        """
        if not await self.guild_registered(ctx):
            await ctx.message.channel.send(
                '{} The guild must first be registered with the bot.'.format(ctx.author.mention)
            )
            return

        # First, check that the client can write to this channel.
        channel_perms = welcome_channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if not channel_perms.send_messages:
            await ctx.message.channel.send(
                '{} {} cannot write to channel {}.'.format(ctx.author.mention, self.bot.user.name, welcome_channel)
            )
            return

        self.db.set_welcome(ctx, welcome_message, welcome_channel)
        await ctx.message.channel.send(
            '{} New users will be welcomed in channel {} with the message "{}".'.format(
                ctx.author.mention,
                welcome_channel,
                welcome_message
            )
        )

    async def guild_fully_configured(self, ctx):
        """
        Confirms that the guild in question is ready to go.

        This checks that the logging channel is set up, and all three team roles have also
        been set up.

        :param ctx:
        :return:
        """
        if not await self.guild_registered(ctx):
            return False

        guild_info = await self.db.get_guild(ctx)
        assert guild_info is not None, "Guild information has been corrupted in the database"
        if (guild_info["welcome_role"] is None or
                guild_info["instinct_role"] is None or
                guild_info["mystic_role"] is None or
                guild_info["valor_role"] is None or
                guild_info["welcome_message"] is None or
                guild_info["welcome_channel"] is None):
            return False
        return True

    @discord.ext.commands.command()
    @discord.ext.commands.has_permissions(administrator=True)
    async def add_mandatory_role(self, ctx, role: discord.Role):
        """
        Add a role to the list of roles that *must* be given to a user on verification.

        :param ctx:
        :param role:
        :return:
        """
        if not await self.guild_fully_configured(ctx):
            await ctx.message.channel.send(
                '{} Basic guild configuration must be finished before adding mandatory roles.'.format(
                    ctx.author.mention
                )
            )
            return

        self.db.add_standard_role(ctx, role, mandatory=True)
        await ctx.message.channel.send(
            "{} Role {} has been added to this guild's mandatory roles".format(
                ctx.author.mention,
                role
            )
        )

    @discord.ext.commands.command()
    @discord.ext.commands.has_permissions(administrator=True)
    async def add_standard_role(self, ctx, role: discord.Role):
        """
        Add a role to the list of roles given to a user on a standard verification.

        :param ctx:
        :param role:
        :return:
        """
        if not await self.guild_fully_configured(ctx):
            await ctx.message.channel.send(
                '{} Basic guild configuration must be finished before adding standard roles.'.format(
                    ctx.author.mention
                )
            )
            return

        self.db.add_standard_role(ctx, role, mandatory=False)
        await ctx.message.channel.send(
            "{} Role {} has been added to this guild's standard roles".format(
                ctx.author.mention,
                role
            )
        )

    @discord.ext.commands.command(
        help="Display the guild configuration."
    )
    @discord.ext.commands.has_permissions(manage_roles=True)
    async def showsettings(self, ctx):
        """
        Check the stored guild configuration.

        :param ctx:
        :return:
        """
        if not await self.guild_registered(ctx):
            await ctx.message.channel.send(
                '{} This guild must be registetered with {} first.'.format(
                    ctx.author.mention,
                    self.bot.user.name
                )
            )
            return

        guild_info = await self.db.get_guild(ctx)
        summary_str_template = textwrap.dedent(
            """\
            Log channel: {}
            Welcome role: {}
            Team roles: {} | {} | {}
            Welcome channel: {}
            Roles given on a standard verification:
            {}
            Welcome message:
            ----
            {}
            ----
            """
        )

        standard_role_str = "(none)"
        if len(guild_info["standard_roles"]) > 0:
            standard_role_str = " - {}".format(guild_info["standard_roles"][0])
            for standard_role in guild_info["standard_roles"][1:]:
                standard_role_str += "\n - {}".format(standard_role)

        welcome_message_str = guild_info["welcome_message"] if guild_info["welcome_message"] is not None else "(none)"

        await ctx.message.channel.send(
            summary_str_template.format(
                guild_info["log_channel"],
                guild_info["welcome_role"],
                guild_info["instinct_role"],
                guild_info["mystic_role"],
                guild_info["valor_role"],
                guild_info["welcome_channel"],
                standard_role_str,
                welcome_message_str
            )
        )

    async def send_welcome_message(self, ctx, new_member: discord.Member):
        """
        Send the guild's configured welcome message to the new user.

        :param ctx:
        :param new_user:
        :return:
        """
        guild_info = await self.db.get_guild(ctx)
        assert guild_info is not None, "Guild information has been corrupted in the database"
        channel_converter = discord.ext.commands.TextChannelConverter()
        welcome_channel = await channel_converter.convert(ctx, str(guild_info["welcome_channel"]))

        await welcome_channel.send(guild_info["welcome_message"].format(new_member.mention))

    async def verify_helper(self, ctx, member: discord.Member, in_game_name, team, roles_to_apply):
        """
        Helper function that performs the work of both verify and nickverify.

        :param ctx: context that includes the message
        :param member: a Discord member
        :param in_game_name: the IGN for the user (may be None, in which case don't set it)
        :param team: one of "instinct|mystic|valor|i|m|v|blue|yellow|red|b|y|r", case-insensitive
        :param roles_to_apply: a list representing roles that should be applied
        :return:
        """
        if not await self.guild_fully_configured(ctx):
            await ctx.message.channel.send(
                '{} This guild is not fully set up yet.'.format(ctx.author.mention)
            )
            return

        message = ctx.message
        async with message.channel.typing():
            guild_info = await self.db.get_guild(ctx)
            if guild_info["welcome_role"] not in member.roles:
                await message.channel.send(
                    "{} The specified member is not in the Welcome role.".format(
                        message.author.mention
                    )
                )
                return

            # Having reached here, we know this member is in the Welcome role.
            instinct_strings = ["instinct", "i", "yellow", "y"]
            mystic_strings = ["mystic", "m", "blue", "b"]
            valor_strings = ["valor", "v", "red", "r"]
            team_role = None
            team = team.lower()
            if team in instinct_strings:
                team_role = guild_info["instinct_role"]
            elif team in mystic_strings:
                team_role = guild_info["mystic_role"]
            elif team in valor_strings:
                team_role = guild_info["valor_role"]
            else:
                "Team must be one of the following (case-insensitive): {}".format(
                    "|".join(instinct_strings + mystic_strings + valor_strings)
                )

            # If any roles are specified in roles_to_apply, apply those; otherwise,
            # apply the standard battery of roles.
            if len(roles_to_apply) == 0:
                roles_to_add = guild_info["standard_roles"]
            else:
                role_converter = discord.ext.commands.RoleConverter()
                roles_to_add = [await role_converter.convert(ctx, str(role)) for role in roles_to_apply]

            final_roles_to_add = list(set([team_role] + guild_info["mandatory_roles"] + roles_to_add))

            if in_game_name is not None:
                await member.edit(
                    roles=final_roles_to_add,
                    nick=in_game_name,
                    reason="Verified by {} using {}".format(message.author.mention, self.bot.user.name)
                )
            else:
                await member.edit(
                    roles=final_roles_to_add,
                    reason="Verified by {} using {}".format(message.author.mention, self.bot.user.name)
                )

            await message.channel.send(
                "{} Member {} has been verified with team {} and roles {}.".format(
                    message.author.mention,
                    member,
                    team_role,
                    "|".join(list(set(roles_to_add + guild_info["mandatory_roles"])))
                )
            )

        await self.send_welcome_message(ctx, member)

    @discord.ext.commands.command(
        help="Verify the specified member.",
        aliases=["v"],
        usage="verify [member] [team role] [optional: the member's requested roles]"
    )
    @discord.ext.commands.has_permissions(manage_roles=True)
    async def verify(self, ctx, member: discord.Member, team: discord.Role, *regions):
        """
        Verify the specified user.

        This involves stripping them of the Welcome role, assigning them to the appropriate team,
        and then if there are other region roles then add them to those roles too.

        :param ctx: context that includes the message
        :param member: a Discord member
        :param team: the Discord role representing their team
        :param regions: zero, one, or several region roles
        :return:
        """
        await self.verify_helper(ctx, member, None, team, regions)

    @discord.ext.commands.command(
        help="Verify the specified member and set their guild nick.",
        aliases=["nickv", "nv", "n"],
        usage='nickverify [member] [IGN] [team role] [optional region roles or "all"]'
    )
    @discord.ext.commands.has_permissions(manage_roles=True)
    @discord.ext.commands.has_permissions(manage_nicknames=True)
    async def nickverify(self, ctx, member: discord.Member, nick, team: discord.Role, *regions):
        """
        Verify the specified user and set their guild nick.

        This is a special version of verify.

        :param ctx:
        :param member:
        :param nick:
        :param team:
        :param regions:
        :return:
        """
        await self.verify_helper(ctx, member, nick, team, regions)

    @discord.ext.commands.command(
        help="Grant the calling member all region roles.",
    )
    async def standard(self, ctx):
        """
        Grant the calling member all standard roles.

        :param ctx: context that includes the message
        :param member: a Discord member
        :return:
        """
        guild_info = await self.db.get_guild(ctx)
        await ctx.author.edit(
            roles=list(set(ctx.author.roles + guild_info["standard_roles"]))
        )

        access_granted_message_template = textwrap.dedent(
            """\
            {} You have been granted access to the following:
            {}
            """
        )

        role_str = "(none)"
        if len(guild_info["standard_roles"]) > 0:
            role_str = " - {}".format(guild_info["standard_roles"][0])
            for role in guild_info["standard_roles"][1:]:
                role_str += "\n - {}".format(role)

        await ctx.message.channel.send(
            access_granted_message_template.format(ctx.author.mention, role_str)
        )

    @discord.ext.commands.command(
        help="Reset the specified member.",
        enabled=not settings.production  # only available when testing
    )
    @discord.ext.commands.has_permissions(manage_roles=True)
    @discord.ext.commands.has_permissions(manage_nicknames=True)
    async def reset(self, ctx, member: discord.Member):
        """
        Reset the member for testing.

        This will strip the member of all roles and their nickname, and adding them to the Welcome role.

        :param ctx: context that includes the message
        :param member: a Discord member
        :return:
        """
        if not await self.guild_fully_configured(ctx):
            await ctx.message.channel.send(
                '{} This guild is not fully set up yet.'.format(ctx.author.mention)
            )
            return

        async with ctx.message.channel.typing():
            guild_info = await self.db.get_guild(ctx)
            await member.edit(
                roles=[guild_info["welcome_role"]],
                nick=None,
                reason="Reset by {} using {}".format(ctx.message.author.mention, self.bot.user.name)
            )
