import discord
from discord.ext.commands import command, has_permissions, CheckFailure

__author__ = 'Richard Liang'


class CannotRunCommand(CheckFailure):
    pass


class BotPermsChecker(object):
    """
    Underlying code that performs permission checks on commands.
    """
    def __init__(self, bot, permissions_db):
        self.bot = bot
        self.db = permissions_db  # a BotPermsDB or workalike

    def can_run_bot(self, ctx):
        """
        True if the calling member has bot perms for this guild; False otherwise.

        :param ctx:
        :return:
        """
        caller_permissions = ctx.channel.permissions_in(ctx.channel)
        if caller_permissions.administrator:
            return True

        result = self.db.get_bot_perms(ctx.guild)
        if result is None:
            return False

        return len(set(ctx.author.roles).intersection(result["can_configure_bot"])) > 0

    def can_run_bot_validator(self, ctx):
        if not self.can_run_bot(ctx):
            raise CannotRunCommand("You do not have permissions to run this command.")


class BotPermsCog(BotPermsChecker):
    """
    A cog that handles configuration of who can run what commands.
    """
    def __init__(self, bot, db):
        super(BotPermsCog, self).__init__(bot, db)

    @command(help="Show bot permissions", aliases=["bot_perms"])
    async def bot_permissions(self, ctx):
        """
        Show this guild's bot permissions.

        :param ctx:
        :return:
        """
        if not self.can_run_bot(ctx):
            return

        bot_perms = self.db.get_bot_perms(ctx.guild)
        perms_str = "(None)"
        if bot_perms is not None and len(bot_perms["can_configure_bot"]) > 0:
            perms_str = "- " + "\n- ".join(bot_perms["can_configure_bot"])

        summary_message = f"{ctx.author.mention} Members with the following roles can configure the bot:\n{perms_str}"
        await ctx.channel.send(summary_message)

    @command(
        help="Add bot permissions to a role",
        aliases=["make_bot_admin"]
    )
    @has_permissions(administrator=True)
    async def add_bot_permissions(
            self,
            ctx,
            role: discord.Role
    ):
        """
        Grant bot permissions to the specified role.

        :param ctx:
        :param role:
        :return:
        """
        self.db.add_bot_permissions_to_role(ctx.guild, role)
        summary_message = f"{ctx.author.mention} Members with role {role} can now configure the bot."
        await ctx.channel.send(summary_message)

    @command(
        help="Remove bot permissions from a role",
        aliases=["revoke_bot_admin"]
    )
    @has_permissions(administrator=True)
    async def remove_bot_permissions(
            self,
            ctx,
            role: discord.Role
    ):
        """
        Remove bot permissions from the specified role.

        :param ctx:
        :param role:
        :return:
        """
        self.db.remove_bot_permissions_from_role(ctx.guild, role)
        summary_message = f"{ctx.author.mention} Members with role {role} cannot configure the bot."
        await ctx.channel.send(summary_message)

    @command(
        help="Remove bot permissions from a role",
        aliases=["revoke_bot_admin"]
    )
    @has_permissions(administrator=True)
    async def remove_bot_permissions(
            self,
            ctx,
            role: discord.Role
    ):
        """
        Remove bot permissions from the specified role.

        :param ctx:
        :param role:
        :return:
        """
        self.db.remove_bot_permissions_from_role(ctx.guild, role)
        summary_message = f"{ctx.author.mention} Members with role {role} cannot configure the bot."
        await ctx.channel.send(summary_message)

    @command(
        help="Reset all bot permissions for this guild",
        aliases=["reset_bot_perms"]
    )
    @has_permissions(administrator=True)
    async def reset_bot_permissions(
            self,
            ctx
    ):
        """
        Reset bot permissions for this guild.

        :param ctx:
        :return:
        """
        self.db.reset_bot_permissions(ctx.guild)
        summary_message = f"{ctx.author.mention} All roles have had their bot configuration privileges revoked."
        await ctx.channel.send(summary_message)

