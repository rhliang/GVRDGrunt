import textwrap
import discord
from discord.ext.commands import command, has_permissions
from datetime import datetime, timedelta

__author__ = 'Richard Liang'


class RoleReminderNotConfigured(Exception):
    pass


class RoleReminderCog():
    """
    A cog that handles reminding users to subscribe to a suggested role the GVRD guilds.
    """
    summary_str_template = textwrap.dedent(
        """\
        Reminder channel: {}
        Reminder message: {}
        Wait time: {} 
        Reminded role: {}
        Verified roles:
        {}
        Suggested roles:
        {}
        """
    )

    def __init__(self, bot, db, logging_cog=None):
        self.bot = bot
        self.db = db  # a RoleReminderDB or workalike
        self.logging_cog = logging_cog  # a GuildLoggingCog or workalike

    @staticmethod
    def role_list_helper(role_list):
        """
        Helper that makes a list string of the specified roles.
        :param role_list:
        :return:
        """
        if len(role_list) == 0:
            return "(none)"
        role_list_str = f"- {role_list[0]}"
        for role in role_list[1:]:
            role_list_str += f"\n- {role}"
        return role_list_str

    @command(
        help="Show role reminder configuration.",
        aliases=["show_role_reminder_settings"]
    )
    @has_permissions(manage_roles=True)
    async def show_role_reminder_config(self, ctx):
        """
        Show role reminder configuration.

        :param ctx:
        :return:
        """
        role_reminder_info = self.db.get_role_reminder_info(ctx.guild)
        if role_reminder_info is None:
            raise RoleReminderNotConfigured("Role reminders are not configured.")

        summary_str = self.summary_str_template.format(
            role_reminder_info["reminder_channel"],
            role_reminder_info["reminder_message"],
            role_reminder_info["wait_time"],
            role_reminder_info["reminded_role"],
            self.role_list_helper(role_reminder_info["verified_roles"]),
            self.role_list_helper(role_reminder_info["suggested_roles"])
        )
        await ctx.channel.send(f"{ctx.author.mention}:\n\n{summary_str}")

    @command(help="Configure role reminder functionality.")
    @has_permissions(manage_roles=True)
    async def activate_role_reminders(
            self,
            ctx,
            reminder_channel: discord.TextChannel,
            reminder_message,
            wait_time: int,
            reminded_role: discord.Role
    ):
        """
        Activate role reminders for this guild.

        :param ctx:
        :param reminder_channel:
        :param reminder_message:
        :param wait_time: the number of hours to wait before the reminder
        :param reminded_role:
        :return:
        """
        self.db.configure_role_reminder(ctx.guild, reminder_channel, reminder_message, wait_time, reminded_role)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role reminders for this guild are now configured."
        )

    @command(help="Add a verified role.")
    @has_permissions(manage_roles=True)
    async def add_verified_role(
            self,
            ctx,
            verified_role: discord.Role
    ):
        """
        Add a verified role for this guild.

        :param ctx:
        :param verified_role:
        :return:
        """
        self.db.add_verified_role(ctx.guild, verified_role)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Members with role {verified_role} are now recognized as verified."
        )

    @command(help="Add a suggested role.")
    @has_permissions(manage_roles=True)
    async def add_suggested_role(
            self,
            ctx,
            suggested_role: discord.Role
    ):
        """
        Add a suggested role for this guild.

        :param ctx:
        :param suggested_role:
        :return:
        """
        self.db.add_suggested_role(ctx.guild, suggested_role)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role {suggested_role} is now understood as one suggested to users."
        )

    @command(help="Deactivate role reminder functionality.")
    @has_permissions(manage_roles=True)
    async def deactivate_role_reminders(self, ctx):
        """
        Deactivate role reminders for this guild.

        :param ctx:
        :return:
        """
        self.db.remove_role_reminder_data(ctx.guild)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role reminders for this guild are now deactivated."
        )

    @command(help="De-register a role as a verified role.")
    @has_permissions(manage_roles=True)
    async def remove_verified_role(self, ctx, verified_role: discord.Role):
        """
        De-register the specified role as a verified role.

        :param ctx:
        :param verified_role:
        :return:
        """
        self.db.remove_verified_role(ctx.guild, verified_role)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role {verified_role} is no longer recognized as a verified role."
        )

    @command(help="De-register all verified roles.")
    @has_permissions(manage_roles=True)
    async def clear_verified_roles(self, ctx):
        """
        De-register all of the verified roles.

        :param ctx:
        :return:
        """
        self.db.clear_verified_roles(ctx.guild)
        await ctx.message.channel.send(
            f"{ctx.author.mention} All of the guild's verified roles have been cleared."
        )

    @command(help="De-register a role as a suggested role.")
    @has_permissions(manage_roles=True)
    async def remove_suggested_role(self, ctx, suggested_role: discord.Role):
        """
        De-register the specified role as a suggested role.

        :param ctx:
        :param suggested_role:
        :return:
        """
        self.db.remove_suggested_role(ctx.guild, suggested_role)
        await ctx.message.channel.send(
            f"{ctx.author.mention} Role {suggested_role} is no longer recognized as a suggested role."
        )

    @command(help="De-register all suggested roles.")
    @has_permissions(manage_roles=True)
    async def clear_suggested_roles(self, ctx):
        """
        De-register all of the suggested roles.

        :param ctx:
        :return:
        """
        self.db.clear_suggested_roles(ctx.guild)
        await ctx.message.channel.send(
            f"{ctx.author.mention} All of the guild's suggested roles have been cleared."
        )

    @command(help="Remind verified users that haven't already been reminded about suggested roles.")
    @has_permissions(manage_roles=True)
    async def rolereminder(self, ctx):
        """
        Remind users to subscribe to a suggested role.

        Assign these users the guild's `reminded role`.
        :param ctx:
        :return:
        """
        role_reminder_info = self.db.get_role_reminder_info(ctx.guild)
        if role_reminder_info is None:
            raise RoleReminderNotConfigured("Role reminders are not configured.")

        # Bail out if there are no suggested roles.
        if len(role_reminder_info["suggested_roles"]) == 0:
            await ctx.channel.send(f"{ctx.author.mention} This guild has no suggested roles.")
            return

        verified_members = set()
        for verified_role in role_reminder_info["verified_roles"]:
            verified_members = verified_members.union(verified_role.members)

        # Remove members that have already been reminded.
        verified_members = verified_members.difference(role_reminder_info["reminded_role"].members)

        # Remove members that joined too recently (as per the guild's specified wait time).
        too_recent = datetime.now() - timedelta(hours=role_reminder_info["wait_time"])
        verified_members = {x for x in verified_members if x.joined_at <= too_recent}

        has_no_suggested_roles = verified_members
        for suggested_role in role_reminder_info["suggested_roles"]:
            has_no_suggested_roles = has_no_suggested_roles.difference(suggested_role.members)

        has_no_suggested_roles = sorted(has_no_suggested_roles, key=lambda x: str(x.display_name).lower())
        if len(has_no_suggested_roles) == 0:
            await ctx.channel.send(f"{ctx.author.mention} No members need a reminder.")
            return

        # Compose a string of member mentions.
        if len(has_no_suggested_roles) == 1:
            member_mention_str = has_no_suggested_roles[0].mention
        elif len(has_no_suggested_roles) == 2:
            member_mention_str = f"{has_no_suggested_roles[0].mention} and {has_no_suggested_roles[1].mention}"
        else:
            member_mention_str = ", ".join([x.mention for x in has_no_suggested_roles[:-1]])
            member_mention_str += f", and {has_no_suggested_roles[-1].mention}"

        reminder_message = role_reminder_info["reminder_message"].format(member_mention_str)
        async with role_reminder_info["reminder_channel"].typing():
            await role_reminder_info["reminder_channel"].send(reminder_message)
            for member in has_no_suggested_roles:
                new_roles = member.roles
                new_roles.append(role_reminder_info["reminded_role"])
                await member.edit(
                    roles=list(set(new_roles)),
                    reason=f"Reminded to add a suggested role by {ctx.author.name} using "
                           f"{ctx.guild.get_member(self.bot.user.id).name}"
                )

                if self.logging_cog is not None:
                    await self.logging_cog.log_to_channel(
                        member.guild,
                        f"{member} was reminded to subscribe to suggested roles"
                    )
