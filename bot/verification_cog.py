import textwrap
import discord
from discord.ext.commands import command, has_permissions, BadArgument, EmojiConverter, Cog

from bot.convert_using_guild import role_converter_from_name

__author__ = 'Richard Liang'


class VerificationNotRegistered(Exception):
    pass


class VerificationNotConfigured(Exception):
    pass


class VerificationCog(Cog):
    """
    A cog that handles verification of users in the GVRD guilds.
    """
    access_granted_message_template = textwrap.dedent(
        """\
        {} You have been granted access to the following:
        {}
        """
    )

    # Emoji that will be attached to screenshots.
    deny = "❌"
    approved = "👍"
    denied = "👎"

    def __init__(self, bot, db):
        self.bot = bot
        self.db = db  # a GuildInfoDB object or workalike
        self.member_to_screenshot = {}  # maps member -|-> the member's most recent unverified screenshot
        self.screenshot_to_member = {}  # the converse mapping

    def get_bot_member(self, guild):
        """
        Helper that gets the bot's guild Member.

        :param guild:
        :return:
        """
        return guild.get_member(self.bot.user.id)

    @command()
    @has_permissions(administrator=True)
    async def register_guild(self, ctx):
        """
        Register this guild with the bot.
        :param ctx:
        :return:
        """
        self.db.register_guild(ctx.guild)
        await ctx.message.channel.send(
            f'{ctx.author.mention} This guild has been registered with {self.get_bot_member(ctx.guild).name} '
            f'and may now be configured.'
        )

    def is_guild_registered(self, guild):
        """
        Return True if guild is registered in the database; False otherwise.

        :param guild:
        :return:
        """
        guild_info = self.db.get_verification_info(guild)
        return guild_info is not None

    def guild_registered_validator(self, guild):
        """
        Raises a VerificationNotRegistered exception if the guild is not registered in the database.
        :param guild:
        :return:
        """
        if not self.is_guild_registered(guild):
            raise VerificationNotRegistered("The guild must first be registered with the bot.")

    @command()
    @has_permissions(administrator=True)
    async def configure_channel(self, ctx, channel_type, channel: discord.TextChannel):
        """
        Helper that performs guild channel configuration for the screenshot and help channels.
        :param ctx:
        :param channel_type:
        :param channel:
        :return:
        """
        self.guild_registered_validator(ctx.guild)

        # First, check that the client can write to this channel.
        channel_perms = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if not channel_perms.send_messages:
            await ctx.message.channel.send(
                f'{ctx.author.mention} {self.get_bot_member(ctx.guild).name} cannot write to channel {channel}.'
            )
            return

        self.db.set_channel(ctx.guild, channel, channel_type)  # this may raise BadArgument
        await ctx.message.channel.send(f'{ctx.author.mention} {channel_type} channel set to {channel}.')

    @command()
    @has_permissions(administrator=True)
    async def configure_welcome_role(self, ctx, role: discord.Role):
        """
        Set this guild's welcome role.

        :param ctx:
        :param team:
        :param role:
        :return:
        """
        self.guild_registered_validator(ctx.guild)

        self.db.set_welcome_role(ctx.guild, role)
        await ctx.message.channel.send(f"{ctx.author.mention} This guild's welcome role has been set to: {role.id}")

    @command()
    @has_permissions(administrator=True)
    async def configure_team_emoji(self, ctx, team, emoji):
        """
        Update the guild information in the database with the given team's emoji.

        :param ctx:
        :param team:
        :param emoji:
        :return:
        """
        self.guild_registered_validator(ctx.guild)

        emoji_converter = EmojiConverter()
        try:
            actual_emoji = await emoji_converter.convert(ctx, emoji)
        except BadArgument:
            actual_emoji = emoji

        self.db.set_team_emoji(ctx.guild, team, actual_emoji)
        await ctx.message.channel.send(
            f'{ctx.author.mention} Guild information has been updated: {team.lower()} emoji is {emoji}.'
        )

    @command()
    @has_permissions(administrator=True)
    async def configure_team_role(self, ctx, team, role: discord.Role):
        """
        Update the guild information in the database with the given team's snowflake.

        :param ctx:
        :param team:
        :param role:
        :return:
        """
        self.guild_registered_validator(ctx.guild)

        self.db.set_team_role(ctx.guild, team, role)
        await ctx.message.channel.send(
            f'{ctx.author.mention} Guild information has been updated: {team.lower()} role is {role.id}.'
        )

    @command()
    @has_permissions(administrator=True)
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
        self.guild_registered_validator(ctx.guild)

        # First, check that the client can write to this channel.
        channel_perms = welcome_channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if not channel_perms.send_messages:
            await ctx.message.channel.send(
                f'{ctx.author.mention} {self.get_bot_member(ctx.guild).name} cannot write to channel {welcome_channel}.'
            )
            return

        self.db.set_welcome(ctx.guild, welcome_message, welcome_channel)
        await ctx.message.channel.send(
            f'{ctx.author.mention} New users will be welcomed in channel '
            f'{welcome_channel} with the message "{welcome_message}".'
        )

    @command()
    @has_permissions(administrator=True)
    async def configure_denied_message(self, ctx, denied_message):
        """
        Configure how this guild messages members whose verification failed.

        The denied message will be sent with a ping in the guild's help channel.
        It should be a Python template string with a single {} where we will insert the
        ping.

        :param ctx:
        :param welcome_channel:
        :param welcome_message:
        :return:
        """
        self.guild_registered_validator(ctx.guild)

        self.db.set_denied_message(ctx.guild, denied_message)
        await ctx.message.channel.send(
            f'{ctx.author.mention} Members whose verification was denied will be pinged '
            f'with the message "{denied_message}".'
        )

    def guild_fully_configured(self, guild):
        """
        Confirms that the guild in question is ready to go.

        This checks that the logging channel is set up, and all three team roles have also
        been set up.

        :param ctx:
        :return:
        """
        if not self.is_guild_registered(guild):
            return False

        guild_info = self.db.get_verification_info(guild)
        if guild_info is None:
            raise RuntimeError("Guild information has been corrupted in the database")

        must_be_set = [field_name for field_name, _ in self.db.all_fields]
        if any([guild_info[x] is None for x in must_be_set]):
            return False
        return True

    def guild_fully_configured_validator(self, guild):
        """
        Raises a VerificationNotConfigured exception if the guild is not fully configured.

        :param guild:
        :return:
        """
        if not self.guild_fully_configured(guild):
            raise VerificationNotConfigured("Basic guild configuration must be finished first.")

    @command()
    @has_permissions(administrator=True)
    async def add_mandatory_role(self, ctx, role: discord.Role):
        """
        Add a role to the list of roles that *must* be given to a user on verification.

        :param ctx:
        :param role:
        :return:
        """
        self.guild_fully_configured_validator(ctx.guild)

        self.db.add_standard_role(ctx.guild, role, mandatory=True)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role {role} has been added to this guild's mandatory roles"
        )

    @command()
    @has_permissions(administrator=True)
    async def add_standard_role(self, ctx, role: discord.Role):
        """
        Add a role to the list of roles given to a user on a standard verification.

        :param ctx:
        :param role:
        :return:
        """
        self.guild_fully_configured_validator(ctx.guild)

        self.db.add_standard_role(ctx.guild, role, mandatory=False)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role {role} has been added to this guild's standard roles"
        )

    @command()
    @has_permissions(administrator=True)
    async def clear_roles(self, ctx):
        """
        Clear the list of roles given to a user on a standard verification.

        This removes both the standard roles and the mandatory roles.

        :param ctx:
        :return:
        """
        self.guild_fully_configured_validator(ctx.guild)

        self.db.clear_roles(ctx.guild)
        await ctx.message.channel.send(
            f"{ctx.author.mention} All standard and mandatory roles given on verification have been cleared."
        )

    summary_str_template = textwrap.dedent(
        """\
        Screenshot channel: {}
        Help channel: {}
        Welcome role: {}
        Team roles: {} | {} | {}
        Team emoji: {} | {} | {}
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

    @command(help="Display the guild configuration.")
    @has_permissions(manage_roles=True)
    async def showsettings(self, ctx):
        """
        Check the stored guild configuration.

        :param ctx:
        :return:
        """
        self.guild_registered_validator(ctx.guild)

        guild_info = self.db.get_verification_info(ctx.guild)

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
            self.summary_str_template.format(
                guild_info["screenshot_channel"],
                guild_info["help_channel"],
                guild_info["welcome_role"],
                guild_info["instinct_role"],
                guild_info["mystic_role"],
                guild_info["valor_role"],
                guild_info["instinct_emoji"],
                guild_info["mystic_emoji"],
                guild_info["valor_emoji"],
                guild_info["welcome_channel"],
                role_list_strings["standard"],
                role_list_strings["mandatory"],
                welcome_message,
                denied_message
            ),
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
                users=False
            )
        )

    async def send_welcome_message(self, guild, new_member: discord.Member):
        """
        Send the guild's configured welcome message to the new user.

        :param guild:
        :param new_member:
        :return:
        """
        guild_info = self.db.get_verification_info(guild)
        if guild_info is None:
            raise RuntimeError("Guild information has been corrupted in the database")
        welcome_channel = guild_info["welcome_channel"]
        await welcome_channel.send(guild_info["welcome_message"].format(new_member.mention))

    async def verify_helper(self, guild, verifier, reply_channel, member: discord.Member,
                            in_game_name, team, roles_to_apply):
        """
        Helper function that performs the work of both verify and nickverify.

        :param guild:
        :param verifier: a Discord member who is doing the verification
        :param reply_channel: channel to respond to the verifier in
        :param member: a Discord member
        :param in_game_name: the IGN for the user (may be None, in which case don't set it)
        :param team: one of "instinct|mystic|valor|i|m|v|blue|yellow|red|b|y|r", case-insensitive
        :param roles_to_apply: a list of role names that should be applied
        :return:
        """
        self.guild_fully_configured_validator(guild)

        async with reply_channel.typing():
            guild_info = self.db.get_verification_info(guild)
            if guild_info["welcome_role"] not in member.roles:
                await reply_channel.send(
                    f"{verifier.mention} The specified member is not in the Welcome role."
                )
                return

            # Having reached here, we know this member is in the Welcome role.
            instinct_strings = ["instinct", "i", "yellow", "y"]
            mystic_strings = ["mystic", "m", "blue", "b"]
            valor_strings = ["valor", "v", "red", "r"]
            team = team.lower()
            if team in instinct_strings:
                team = "instinct"
                team_role = guild_info["instinct_role"]
            elif team in mystic_strings:
                team = "mystic"
                team_role = guild_info["mystic_role"]
            elif team in valor_strings:
                team = "valor"
                team_role = guild_info["valor_role"]
            else:
                raise BadArgument(
                    f"Team must be one of the following (case-insensitive): " 
                    f"{'|'.join(instinct_strings + mystic_strings + valor_strings)}"
                )

            # If any roles are specified in roles_to_apply, apply those; otherwise,
            # apply the standard battery of roles.
            if len(roles_to_apply) == 0:
                roles_to_add = guild_info["standard_roles"]
            else:
                roles_to_add = [role_converter_from_name(guild, str(role)) for role in roles_to_apply]

            other_roles_to_add = list(set(guild_info["mandatory_roles"] + roles_to_add))

            current_nick = member.nick
            nick_str = "no nickname"
            if in_game_name is not None:
                await member.edit(
                    roles=[team_role] + other_roles_to_add,
                    nick=in_game_name,
                    reason=f"Verified by {verifier.name} using {self.get_bot_member(guild).name}"
                )
                nick_str = f"nick {in_game_name}"
            else:
                await member.edit(
                    roles=[team_role] + other_roles_to_add,
                    reason=f"Verified by {verifier.name} using {self.get_bot_member(guild).name}"
                )
                if current_nick is not None:
                    nick_str = f"nick {current_nick} (self-assigned)"

            roles_added_str = "(none)"
            if len(other_roles_to_add) > 0:
                roles_added_str = f" - {other_roles_to_add[0]}"
                for role in other_roles_to_add[1:]:
                    roles_added_str += f"\n - {role}"

            await self.member_approved(member, team)
            await reply_channel.send(
                f"{verifier.mention} Member {member} has been verified with {nick_str}, team {team_role}, " 
                f"and roles:\n{roles_added_str}"
            )

        await self.send_welcome_message(guild, member)

    @command(
        help="Verify the specified member.",
        aliases=["v"],
        usage="verify [member] [team role] [optional: the member's requested roles]"
    )
    @has_permissions(manage_roles=True)
    async def verify(self, ctx, member: discord.Member, team, *regions):
        """
        Verify the specified user.

        This involves stripping them of the Welcome role, assigning them to the appropriate team,
        and then if there are other region roles then add them to those roles too.

        :param ctx: context that includes the message
        :param member: a Discord member
        :param team:
        :param regions: zero, one, or several region roles
        :return:
        """
        await self.verify_helper(ctx.guild, ctx.message.author, ctx.message.channel, member, None, team, regions)

    @command(
        help="Verify the specified member and set their guild nick.",
        aliases=["nickv", "nv", "n"],
        usage='nickverify [member] [IGN] [team role] [optional region roles or "all"]'
    )
    @has_permissions(manage_roles=True)
    @has_permissions(manage_nicknames=True)
    async def nickverify(self, ctx, member: discord.Member, nick, team, *regions):
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
        await self.verify_helper(ctx.guild, ctx.message.author, ctx.message.channel, member, nick, team, regions)

    @command(help="Grant the calling member all region roles.")
    async def standard(self, ctx):
        """
        Grant the calling member all standard roles.

        :param ctx: context that includes the message
        :param member: a Discord member
        :return:
        """
        self.guild_fully_configured_validator(ctx.guild)

        guild_info = self.db.get_verification_info(ctx.guild)
        await ctx.author.edit(
            roles=list(set(ctx.author.roles + guild_info["standard_roles"]))
        )

        role_str = "(none)"
        if len(guild_info["standard_roles"]) > 0:
            role_str = f" - {guild_info['standard_roles'][0]}"
            for role in guild_info["standard_roles"][1:]:
                role_str += f"\n - {role}"

        await ctx.message.channel.send(self.access_granted_message_template.format(ctx.author.mention, role_str))

    @command(help="Reset the specified member.")
    @has_permissions(manage_roles=True)
    @has_permissions(manage_nicknames=True)
    async def reset(self, ctx, member: discord.Member):
        """
        Reset the member for testing.

        This will strip the member of all roles and their nickname, and adding them to the Welcome role.

        :param ctx: context that includes the message
        :param member: a Discord member
        :return:
        """
        self.guild_fully_configured_validator(ctx.guild)

        async with ctx.message.channel.typing():
            guild_info = self.db.get_verification_info(ctx.guild)
            await member.edit(
                roles=[guild_info["welcome_role"]],
                nick=None,
                reason=f"Reset by {ctx.message.author.name} using {self.get_bot_member(ctx.guild).name}"
            )
            await ctx.message.channel.send(
                f"{ctx.message.author.mention} Member {member} has been reset to the Welcome role."
            )

    def is_welcome_member_screenshot(self, message):
        """
        True if this is a screenshot in the appropriate channel from a Welcome member, False otherwise.

        :param message:
        :return:
        """
        guild_info = self.db.get_verification_info(message.guild)
        if message.channel != guild_info["screenshot_channel"]:
            return False
        if guild_info["welcome_role"] not in message.author.roles:
            return False
        if len(message.attachments) == 0:
            return False
        return True

    async def welcome_member_screenshot_received(self, screenshot_message):
        """
        On receipt of a Welcome member's screenshot, track this message and its reactions.

        If this member has no previous messages being tracked, start tracking their messages.
        If there is a previous message, forget the old one and start tracking this one.
        Add reactions that can be used to mark as accepted or denied.

        PRE: guild is fully configured.

        :param screenshot_message:
        :return:
        """
        self.guild_fully_configured_validator(screenshot_message.guild)

        # Having reached here, we know that this message is in the appropriate channel,
        # sent by someone with the Welcome role, and contains an attachment (presumably a screenshot).
        verification_info = self.db.get_verification_info(screenshot_message.guild)

        await screenshot_message.clear_reactions()
        await screenshot_message.add_reaction(verification_info["instinct_emoji"])
        await screenshot_message.add_reaction(verification_info["mystic_emoji"])
        await screenshot_message.add_reaction(verification_info["valor_emoji"])
        await screenshot_message.add_reaction(self.deny)

        original_screenshot = self.member_to_screenshot.get(screenshot_message.author, None)
        if original_screenshot is not None:
            await original_screenshot.clear_reactions()
            del self.screenshot_to_member[original_screenshot]

        self.member_to_screenshot[screenshot_message.author] = screenshot_message
        self.screenshot_to_member[screenshot_message] = screenshot_message.author

    @Cog.listener()
    async def on_message(self, message):
        """
        If this is a Welcome member's screenshot in the right channel, add reactions and start tracking it.

        :param message:
        :return:
        """
        # If this is a DM, do nothing.
        if message.guild is None:
            return

        # Do nothing if the guild isn't fully configured yet.
        if not self.guild_fully_configured(message.guild):
            return

        if self.is_welcome_member_screenshot(message):
            await self.welcome_member_screenshot_received(message)

    async def member_approved(self, member, team):
        """
        This member has been approved, so remove them and their screenshot from tracking.

        Call this when the member is either manually or automatedly verified.

        :param member:
        :return:
        """
        verification_info = self.db.get_verification_info(member.guild)

        screenshot_message = self.member_to_screenshot.get(member, None)
        if screenshot_message is None:
            return
        if screenshot_message in self.screenshot_to_member:
            del self.screenshot_to_member[screenshot_message]

        await screenshot_message.clear_reactions()
        await screenshot_message.add_reaction(self.approved)
        await screenshot_message.add_reaction(verification_info[f"{team}_emoji"])
        del self.member_to_screenshot[member]

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """
        Mark as verified or denied when a moderator adds a reaction to a screenshot message.

        :param reaction:
        :param user:
        :return:
        """
        guild_info = self.db.get_verification_info(reaction.message.guild)
        # Do nothing if the guild isn't fully configured yet.
        if guild_info is None:
            return

        if reaction.message.channel != guild_info["screenshot_channel"]:
            return
        reacting_member = reaction.message.guild.get_member(user.id)
        if reacting_member == reaction.message.guild.get_member(self.bot.user.id):
            return
        reactor_permissions = reacting_member.permissions_in(reaction.message.channel)
        if not reactor_permissions.manage_roles or not reactor_permissions.manage_nicknames:
            return
        if reaction.message not in self.screenshot_to_member:
            return

        # Convert the stored emoji data into an actual emoji (either string or discord.Emoji object).
        team_emoji = {}
        for team in ("instinct", "mystic", "valor"):
            team_emoji[team] = guild_info[f"{team}_emoji"]

        if reaction.emoji not in team_emoji.values() and reaction.emoji != self.deny:
            return

        # Having reached this point, we know that this reaction was added to a Welcome screenshot
        # by a moderator.
        member_to_verify = self.screenshot_to_member[reaction.message]

        if reaction.emoji == self.deny:
            await self.deny_member(member_to_verify)
        else:
            for team in ("instinct", "mystic", "valor"):
                if reaction.emoji == team_emoji[team]:
                    await self.verify_helper(
                        reaction.message.guild,
                        reacting_member,
                        reaction.message.channel,
                        member_to_verify,
                        None,
                        team,
                        []
                    )

    async def deny_member(self, member):
        """
        Mark this member as having been denied entry and ping them with a message in the help channel.

        :param member:
        :return:
        """
        screenshot_message = self.member_to_screenshot.get(member, None)
        if screenshot_message is not None:
            await screenshot_message.clear_reactions()
            await screenshot_message.add_reaction(self.denied)
            del self.member_to_screenshot[member]
            del self.screenshot_to_member[screenshot_message]

        guild_info = self.db.get_verification_info(member.guild)
        await guild_info["help_channel"].send(guild_info["denied_message"].format(member.mention))
