import pyparsing as pp
from discord.ext.commands import command, has_permissions

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

    @staticmethod
    def get_guild_factor_action(guild):
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
            else:  # this is an expression in parentheses
                return [toks[1]]
        return guild_factor_action

    def get_guild_term_action(self, guild):
        """
        Factory method that produces a parse action for term statements.

        :param guild:
        :return:
        """
        def guild_term_action(toks):
            if len(toks) == 1:
                # This is just a factor.
                return None
            elif toks[0] == self.COMPLEMENT_TOKEN:
                return [set(guild.members).difference(toks[1])]
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
        factor = left_paren + expression + pp.FollowedBy(right_paren) + right_paren | role
        term <<= complement + term | factor + intersect + term | factor
        expression <<= term + union + expression | term

        factor.setParseAction(self.get_guild_factor_action(guild))
        term.setParseAction(self.get_guild_term_action(guild))
        expression.setParseAction(self.expression_action)

        return expression

    @command()
    @has_permissions(manage_roles=True)
    async def members(self, ctx, *role_statement_tokens):
        """
        Given a list of role names or negations thereof (![role name]), return the members in all of them.

        We'd like to support things like (role1+role2+role3)

        :param ctx:
        :param role_statement_tokens:
        :return:
        """
        role_statement = " ".join(role_statement_tokens)
        parser = self.get_guild_role_parser(ctx.guild)
        result = parser.parseString(role_statement)
        result = result[0]

        member_list_str = "(none)"
        if len(result) > 0:
            member_list = list(result)
            member_list_str = f" - {member_list[0].display_name} ({member_list[0]})"
            for member in member_list[1:]:
                member_list_str += f"\n - {member.display_name} ({member})"

        await ctx.message.channel.send(f'{ctx.author.mention}:\n\n{member_list_str}')
