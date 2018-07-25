import pyparsing as pp
from discord.ext.commands import command, has_permissions
import asyncio

from bot.convert_using_guild import role_converter_from_name

__author__ = 'Richard Liang'


class RoleSetOperationsCog():
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
            parser = self.get_guild_role_parser(ctx.guild)
            result = parser.parseString(role_statement)
            result = sorted(result[0], key=lambda member: str(member.display_name).lower())
            num_members = len(result)

            member_count_str = f"{ctx.author.mention}: {num_members} members"
            await ctx.message.channel.send(member_count_str)
            if num_members == 0:
                return

        # Having reached here, we know we have at least 1 member.
        member_list = list(result)
        member_list_str = f"- {member_list[0].display_name} ({member_list[0]})"
        for member in member_list[1:]:
            member_list_str += f"\n- {member.display_name} ({member})"

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
            async with ctx.message.channel.typing():
                await ctx.message.channel.send(message_text)
                if i + 1 < len(messages_to_send):
                    await ctx.message.channel.send(f"Show more members (y/n)?  Will cancel in {self.timeout} seconds.")

                    def check(m):
                        if m.author != ctx.author:
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
                        async with ctx.message.channel.typing():
                            await ctx.message.channel.send(f"Cancelled.")
                        return
