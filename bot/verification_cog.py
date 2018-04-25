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
        self.member_to_screenshot = {}  # maps member -|-> the member's most recent unverified screenshot
        self.screenshot_to_member = {}  # the converse mapping

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
            f'{ctx.author.mention} This guild has been registered '
            f'with {self.bot.user.name} and may now be configured.'
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
    async def configure_channel(self, ctx, channel_type, channel: discord.TextChannel):
        """
        Helper that performs guild channel configuration for the screenshot, help, and log channels.
        :param ctx:
        :param channel_type:
        :param channel:
        :return:
        """
        if not await self.guild_registered(ctx):
            await ctx.message.channel.send(f'{ctx.author.mention} The guild must first be registered with the bot.')
            return

        if channel_type not in ("screenshot", "help", "log"):
            raise discord.ext.commands.BadArgument("Channel type must be one of screenshot, help, or log.")

        # First, check that the client can write to this channel.
        channel_perms = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if not channel_perms.send_messages:
            await ctx.message.channel.send(
                f'{ctx.author.mention} {self.bot.user.name} cannot write to channel {channel}.'
            )
            return

        self.db.set_channel(ctx, channel, channel_type)
        await ctx.message.channel.send(
            f'{ctx.author.mention} {channel_type} channel set to {channel}.'
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
                f'{ctx.author.mention} The guild must first be registered with the bot.'
            )
            return

        self.db.set_welcome_role(ctx, role)
        await ctx.message.channel.send(
            f"{ctx.author.mention} This guild's welcome role has been set to: {role.id}"
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
                f'{ctx.author.mention} The guild must first be registered with the bot.'
            )
            return

        self.db.set_team_role(ctx, team, role)
        await ctx.message.channel.send(
            f'{ctx.author.mention} Guild information has been updated: {team.lower()} role is {role.id}.'
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
                f'{ctx.author.mention} The guild must first be registered with the bot.'
            )
            return

        # First, check that the client can write to this channel.
        channel_perms = welcome_channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if not channel_perms.send_messages:
            await ctx.message.channel.send(
                f'{ctx.author.mention} {self.bot.user.name} cannot write to channel {welcome_channel}.'
            )
            return

        self.db.set_welcome(ctx, welcome_message, welcome_channel)
        await ctx.message.channel.send(
            f'{ctx.author.mention} New users will be welcomed in channel '
            f'{welcome_channel} with the message "{welcome_message}".'
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
        if guild_info is None:
            raise RuntimeError("Guild information has been corrupted in the database")
        if (guild_info["log_channel"] is None or
                guild_info["screenshot_channel"] is None or
                guild_info["help_channel"] is None or
                guild_info["welcome_role"] is None or
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
                f'{ctx.author.mention} Basic guild configuration must be finished before adding mandatory roles.'
            )
            return

        self.db.add_standard_role(ctx, role, mandatory=True)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role {role} has been added to this guild's mandatory roles"
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
                f'{ctx.author.mention} Basic guild configuration must be finished before adding standard roles.'
            )
            return

        self.db.add_standard_role(ctx, role, mandatory=False)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role {role} has been added to this guild's standard roles"
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
                f'{ctx.author.mention} This guild must be registetered with {self.bot.user.name} first.'
            )
            return

        guild_info = await self.db.get_guild(ctx)
        summary_str_template = textwrap.dedent(
            """\
            Log channel: {}
            Screenshot channel: {}
            Help channel: {}
            Welcome role: {}
            Team roles: {} | {} | {}
            Welcome channel: {}
            Roles given on a standard verification:
            {}
            Roles that must be given during verification:
            {}
            Welcome message:
            ----
            {}
            ----
            Message sent when requesting a new screenshot:
            ----
            {}
            ----
            """
        )

        role_list_strings = {}
        for role_type in ("standard", "mandatory"):
            role_list_strings[role_type] = "(none)"
            curr_type_roles = guild_info[f"{role_type}_roles"]
            if len(curr_type_roles) > 0:
                role_list_strings[role_type] = f" - {curr_type_roles[0]}"
                for curr_type_role in curr_type_roles[1:]:
                    role_list_strings[role_type] += f"\n - {curr_type_role}"

        welcome_message = guild_info["welcome_message"] if guild_info["welcome_message"] is not None else "(none)"
        denied_message = guild_info["denied_message"] if guild_info["denied_message"] is not None else "(none)"

        await ctx.message.channel.send(
            summary_str_template.format(
                guild_info["log_channel"],
                guild_info["screenshot_channel"],
                guild_info["help_channel"],
                guild_info["welcome_role"],
                guild_info["instinct_role"],
                guild_info["mystic_role"],
                guild_info["valor_role"],
                guild_info["welcome_channel"],
                role_list_strings["standard"],
                role_list_strings["mandatory"],
                welcome_message,
                denied_message
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
        if guild_info is None:
            raise RuntimeError("Guild information has been corrupted in the database")
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
                f'{ctx.author.mention} This guild is not fully set up yet.'
            )
            return

        message = ctx.message
        async with message.channel.typing():
            guild_info = await self.db.get_guild(ctx)
            if guild_info["welcome_role"] not in member.roles:
                await message.channel.send(
                    f"{message.author.mention} The specified member is not in the Welcome role."
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
                raise discord.ext.commands.BadArgument(
                    f"Team must be one of the following (case-insensitive): " 
                    f"{'|'.join(instinct_strings + mystic_strings + valor_strings)}"
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
                    reason=f"Verified by {message.author.mention} using {self.bot.user.name}"
                )
            else:
                await member.edit(
                    roles=final_roles_to_add,
                    reason=f"Verified by {message.author.mention} using {self.bot.user.name}"
                )

            self.member_approved(member)
            await message.channel.send(
                f"{message.author.mention} Member {member} has been verified with team {team_role} " 
                f"and roles {'|'.join(list(set(roles_to_add + guild_info['mandatory_roles'])))}."
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
            role_str = f" - {guild_info['standard_roles'][0]}"
            for role in guild_info["standard_roles"][1:]:
                role_str += f"\n - {role}"

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
                f'{ctx.author.mention} This guild is not fully set up yet.'
            )
            return

        async with ctx.message.channel.typing():
            guild_info = await self.db.get_guild(ctx)
            await member.edit(
                roles=[guild_info["welcome_role"]],
                nick=None,
                reason=f"Reset by {ctx.message.author.mention} using {self.bot.user.name}"
            )

    def is_welcome_member_screenshot(self, message):
        """
        True if this is a screenshot in the appropriate channel from a Welcome member, False otherwise.

        :param message:
        :return:
        """
        guild_screenshot_raw_info = self.db.get_screenshot_handling_info(message.guild)
        if message.channel.id != guild_screenshot_raw_info["screenshot_channel_id"]:
            return False
        if guild_screenshot_raw_info["welcome_role_id"] not in [x.id for x in message.author.roles]:
            return False
        if len(message.attachments) == 0:
            return False
        return True

    async def welcome_member_screenshot_received(self, screenshot_message):
        """
        On receipt of a Welcome member's screenshot, track this message and its reactions.

        If this member has no previous messages being tracked, start tracking their messages.
        If there is a previous message, forget the old one and start tracking this one.
        Add a :white_check_mark: reaction and an :x: reaction.

        :return:
        """
        # Having reached here, we know that this message is in the appropriate channel,
        # sent by someone with the Welcome role, and contains an attachment (presumably a screenshot).
        await screenshot_message.clear_reactions()
        screenshot_message.add_reaction("white_check_mark")
        screenshot_message.add_reaction("x")

        original_screenshot = self.member_to_screenshot.get(screenshot_message.author, None)
        if original_screenshot is not None:
            original_screenshot.clear_reactions()
            del self.screenshot_to_member[original_screenshot]

        self.member_to_screenshot[screenshot_message.author] = screenshot_message
        self.screenshot_to_member[screenshot_message] = screenshot_message.author

    async def on_message(self, message):
        """
        If this is a Welcome member's screenshot in the right channel, add reactions and start tracking it.

        :param message:
        :return:
        """
        if self.is_welcome_member_screenshot(message):
            await self.welcome_member_screenshot_received(message)

    def member_approved(self, member):
        """
        This member has been approved, so remove them and their screenshot from tracking.

        Call this when the member is either manually or automatedly verified.

        :param member:
        :return:
        """
        screenshot_message = self.member_to_screenshot.get(member, None)
        if screenshot_message is None:
            return
        if screenshot_message in self.screenshot_to_member:
            del self.screenshot_to_member[screenshot_message]

        screenshot_message.clear_reactions()
        screenshot_message.add_reaction("thumbsup")
        del self.member_to_screenshot[member]

    async def on_reaction_add(self, reaction, user):
        """
        Mark as verified or denied when a moderator adds a reaction to a screenshot message.

        :param reaction:
        :param user:
        :return:
        """
        guild_screenshot_raw_info = self.db.get_screenshot_handling_info(reaction.message.guild)
        if reaction.message.channel.id != guild_screenshot_raw_info["screenshot_channel_id"]:
            return
        reacting_member = reaction.message.guild.get_member(user.id)
        if not reacting_member.manage_roles or not reacting_member.manage_nicknames:
            return

        if reaction.message not in self.screenshot_to_member:
            return

        if str(reaction) not in ("white_check_mark", "x"):
            return

        # Having reached this point, we know that this reaction was added to a Welcome screenshot
        # by a moderator.
        member_to_verify = self.screenshot_to_member[reaction.message]
        if str(reaction) == "white_check_mark":
            self.member_approved(member_to_verify)
        else:
            self.deny_member(member_to_verify)

    async def deny_member(self, member):
        """
        Mark this member as having been denied entry and ping them with a message in the help channel.

        :param member:
        :return:
        """
        screenshot_message = self.member_to_screenshot.get(member, None)
        if screenshot_message is not None:
            screenshot_message.clear_reactions()
            screenshot_message.add_reaction("thumbsdown")
            del self.member_to_screenshot[member]
            del self.screenshot_to_member[screenshot_message]

        guild_screenshot_raw_info = self.db.get_screenshot_handling_info(member.guild)
        help_channel = member.guild.get_channel(guild_screenshot_raw_info["help_channel_id"])

        await help_channel.send(guild_screenshot_raw_info["denied_message"].format(member.mention))
