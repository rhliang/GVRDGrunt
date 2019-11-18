import pyparsing as pp
from discord.ext.commands import command, has_permissions, Cog
import discord
import asyncio
from datetime import datetime

from bot.convert_using_guild import role_converter_from_name

__author__ = 'Richard Liang'


class RoleSetOperationsCog(Cog):
    """
    Perform set operations on guild roles.
    """
    INTERSECT_TOKEN = "and"
    UNION_TOKEN = "or"
    COMPLEMENT_TOKEN = "not"
    LEFT_PAREN_TOKEN = "("
    RIGHT_PAREN_TOKEN = ")"

    def __init__(self, bot):
        self.bot = bot
        self.timeout = 30

    @command()
    @has_permissions(manage_messages=True)
    async def set_member_list_timeout(self, ctx, timeout: int):
        """
        Set the number of seconds that the bot waits for confirmation between chunks of the member list.

        :param ctx:
        :param timeout:
        :return:
        """
        if timeout <= 0:
            raise ValueError("Timeout must be a positive integer.")
        self.timeout = timeout
        async with ctx.channel.typing():
            await ctx.channel.send(f"{ctx.author.mention} The `members` command will wait "
                                   f"{self.timeout} seconds for confirmation.")

    def get_guild_factor_action(self, guild):
        """
        Factory method that produces a parse action for factor statements.

        :param guild:
        :return:
        """
        def guild_factor_action(toks):
            if len(toks) == 1:
                # This is just a role name.
                role = role_converter_from_name(guild, toks[0])
                if role is None:
                    raise pp.ParseException("Did not find a role with that name")
                return [set(role.members)]
            elif toks[0] == self.COMPLEMENT_TOKEN:
                return [set(guild.members).difference(toks[1])]
            else:  # this is an expression in parentheses
                return [toks[1]]
        return guild_factor_action

    @staticmethod
    def get_guild_term_action():
        """
        Factory method that produces a parse action for term statements.

        :return:
        """
        def guild_term_action(toks):
            if len(toks) == 1:
                # This is just a factor.
                return None
            else:
                # This is an intersection, and both toks[0] and toks[2] will have already been converted to sets.
                return [toks[0].intersection(toks[2])]
        return guild_term_action

    @staticmethod
    def expression_action(toks):
        """
        Parse action for expressions.

        :param toks:
        :return:
        """
        if len(toks) == 1:
            # This is simply a term so toks[0] is already what we need.
            return None
        # Having reached here, we know this is a union.
        return [toks[0].union(toks[2])]

    def get_guild_role_parser(self, guild):
        """
        Create a role parser for the specified guild.

        :param guild:
        :return:
        """
        intersect = pp.CaselessKeyword(self.INTERSECT_TOKEN)
        union = pp.CaselessKeyword(self.UNION_TOKEN)
        complement = pp.CaselessKeyword(self.COMPLEMENT_TOKEN)
        left_paren = pp.Literal(self.LEFT_PAREN_TOKEN)
        right_paren = pp.Literal(self.RIGHT_PAREN_TOKEN)
        role = pp.Word(pp.alphanums) | pp.QuotedString("'", escChar="\\")

        expression = pp.Forward()
        term = pp.Forward()
        factor = pp.Forward()
        factor <<= left_paren + expression + pp.FollowedBy(right_paren) + right_paren | complement + factor | role
        term <<= factor + intersect + term | factor
        expression <<= term + union + expression | term

        factor.setParseAction(self.get_guild_factor_action(guild))
        term.setParseAction(self.get_guild_term_action())
        expression.setParseAction(self.expression_action)

        role_statement = pp.StringStart() + expression + pp.StringEnd()

        return role_statement

    def evaluate_role_statement(self, guild, role_statement, start_datetime_str=None, end_datetime_str=None):
        """
        Evaluate the role statement and return a sorted list of members.

        :param guild:
        :param role_statement:
        :param start_datetime_str: if this and end_datetime_str are specified, filter to members
        that joined between these datetimes
        :param end_datetime_str:
        :return:
        """
        parser = self.get_guild_role_parser(guild)
        result = parser.parseString(role_statement)

        if start_datetime_str is not None and end_datetime_str is not None:
            start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%dT%H:%M:%S")
            end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%dT%H:%M:%S")
            members_list = [x for x in result[0] if start_datetime <= x.joined_at <= end_datetime]
        else:
            members_list = result[0]

        return sorted(members_list, key=lambda member: str(member.display_name).lower())

    @command()
    @has_permissions(manage_roles=True)
    async def members(self, ctx, *role_statement_tokens):
        """
        Given a set expression with role names, evaluate the set expression.

        The expression respects unions ("or"), intersections ("and"), negations ("not"), and parentheses.
        Role names with non-alphanumeric characters must be surrounded by single quotes.

        :param ctx:
        :param role_statement_tokens:
        :return:
        """
        async with ctx.message.channel.typing():
            role_statement = " ".join(role_statement_tokens)
            result = self.evaluate_role_statement(ctx.guild, role_statement)
        await self.report_members(list(result), ctx.channel, ctx.author)

    @command()
    @has_permissions(manage_roles=True)
    async def members_mention(self, ctx, *role_statement_tokens):
        """
        Similar to `members` but lists members by mentions.

        :param ctx:
        :param role_statement_tokens:
        :return:
        """
        async with ctx.message.channel.typing():
            role_statement = " ".join(role_statement_tokens)
            result = self.evaluate_role_statement(ctx.guild, role_statement)
        await self.report_members(list(result), ctx.channel, ctx.author, mentions=True)

    @command()
    @has_permissions(manage_roles=True)
    async def members_joined_between_dates(self, ctx, role_statement, start_datetime_str: str, end_datetime_str: str):
        """
        Evaluate the set expression and restrict to members who joined between the specified dates.

        Note that the role statement must be quoted if it contains more than one word.

        :param ctx:
        :param role_statement:
        :param start_datetime_str: a string in the format YYYY-MM-DDTHH:MM:SS
        :param end_datetime_str: same
        :return:
        """
        async with ctx.message.channel.typing():
            members_filtered_by_date = self.evaluate_role_statement(
                ctx.guild,
                role_statement,
                start_datetime_str,
                end_datetime_str
            )
        await self.report_members(members_filtered_by_date, ctx.channel, ctx.author)

    @command()
    @has_permissions(manage_roles=True)
    async def members_joined_between_dates_mention(self, ctx, role_statement,
                                                   start_datetime_str: str, end_datetime_str: str):
        """
        Similar to `members_joined_between_dates` but lists members by mention.

        :param ctx:
        :param role_statement:
        :param start_datetime_str: a string in the format YYYY-MM-DDTHH:MM:SS
        :param end_datetime_str: same
        :return:
        """
        async with ctx.message.channel.typing():
            members_filtered_by_date = self.evaluate_role_statement(
                ctx.guild,
                role_statement,
                start_datetime_str,
                end_datetime_str
            )
        await self.report_members(members_filtered_by_date, ctx.channel, ctx.author, mentions=True)

    @staticmethod
    def member_list_entry(member, mentions=False):
        """
        Helper that creates a single list entry for a member.
        :param member:
        :param mentions: if True, the entry mentions the member; if False, it shows the display name and username.
        :return:
        """
        if not mentions:
            return f"- {member.display_name} ({member})"
        return f"- {member.mention}"

    async def report_members(self, member_list, channel: discord.TextChannel, caller: discord.Member,
                             mentions=False):
        """
        Helper function that takes a member list and reports it back to a member in a specified channel.
        :param member_list:
        :param channel:
        :param caller:
        :param mentions: if False, show the display name and username; if True, list mentions.
        :return:
        """
        num_members = len(member_list)

        member_count_str = f"{caller.mention}: {num_members} members"
        await channel.send(member_count_str)
        if num_members == 0:
            return

        member_list_str = self.member_list_entry(member_list[0], mentions=mentions)
        for member in member_list[1:]:
            member_list_str += "\n" + self.member_list_entry(member, mentions=mentions)

        message_length = 2000
        messages_to_send = []
        if len(member_list_str) <= message_length:
            messages_to_send = [member_list_str]
        else:
            curr_message = ""
            for line in member_list_str.splitlines(keepends=True):
                if len(curr_message) + len(line) > message_length:
                    messages_to_send.append(curr_message)
                    curr_message = line
                else:
                    curr_message += line
            messages_to_send.append(curr_message)

        for i, message_text in enumerate(messages_to_send):
            async with channel.typing():
                await channel.send(message_text)
                if i + 1 < len(messages_to_send):
                    await channel.send(f"Show more members (y/n)?  Will cancel in {self.timeout} seconds.")

                    def check(m):
                        if m.author != caller:
                            return False
                        elif m.content.lower() in ("y", "n", "yes", "no"):
                            return True

                    cancel_listing = False
                    try:
                        msg = await self.bot.wait_for("message", check=check, timeout=self.timeout)
                        if msg.content.lower() not in ("y", "yes"):
                            cancel_listing = True
                    except asyncio.TimeoutError:
                        cancel_listing = True

                    if cancel_listing:
                        async with channel.typing():
                            await channel.send(f"Cancelled.")
                        return
