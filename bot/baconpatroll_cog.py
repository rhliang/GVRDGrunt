import discord
import textwrap
from discord.ext.commands import command, has_permissions, Cog

__author__ = 'Richard Liang'


class BaconpaTrollCog(Cog):
    """
    Let's call this one "moderator's privilege".
    """
    def __init__(self, bot):
        self.bot = bot
        self.guild_info = {}

    @command()
    @has_permissions(administrator=True)
    async def baconpatrollon(self, ctx, baconpatroller: discord.Member, channel: discord.TextChannel,
                             bacon_sez, reply):
        """
        Begin Operation Baconpatrol.

        :param ctx:
        :param baconpatroller: Tell the bot who to Baconpatroll.
        :param bacon_sez: he'll probably say "Good bot", but you know, whatever
        :param reply: what to reply to him with
        :return:
        """
        self.guild_info[ctx.guild] = {
            "baconpatroller": baconpatroller,
            "channel": channel,
            "bacon_sez": bacon_sez,
            "reply": reply,
            "troll": ctx.author,
            "controll_channel": ctx.message.channel,
            "active": True
        }
        await ctx.message.channel.send(
            f'{ctx.author.mention} Now Baconpatrolling channel {channel}, watching for the reply '
            f'"{bacon_sez}" from {baconpatroller}, and counter-replying with "{reply}".'
        )

    config_template = textwrap.dedent("""\
    Baconpatroller: {}
    Channel: {}
    Bacon sez: {}
    Reply: {}
    Troll: {}
    Controll channel: {}
    Active: {}
    """)

    @command()
    @has_permissions(administrator=True)
    async def show_baconfiguration(self, ctx):
        """
        Show Baconfiguration.

        :param ctx:
        :param saycon:
        :return:
        """
        if ctx.guild not in self.guild_info:
            await ctx.message.channel.send(f"{ctx.message.author.mention} I don't even know what that means")
            return
        baconpatrol = self.guild_info[ctx.guild]
        await ctx.message.channel.send(
            self.config_template.format(
                baconpatrol["baconpatroller"],
                baconpatrol["channel"],
                baconpatrol["bacon_sez"],
                baconpatrol["reply"],
                baconpatrol["troll"],
                baconpatrol["controll_channel"],
                baconpatrol["active"]
            )
        )

    @command()
    @has_permissions(administrator=True)
    async def sayconpatroller(self, ctx, saycon):
        """
        The bot speaketh.

        :param ctx:
        :param saycon:
        :return:
        """
        if ctx.guild not in self.guild_info:
            await ctx.message.channel.send(f"{ctx.message.author.mention} I don't even know what that means")
            return
        baconpatrol = self.guild_info[ctx.guild]
        async with baconpatrol["channel"].typing():
            await baconpatrol["channel"].send(saycon)
        await ctx.message.channel.send(f'{ctx.message.author.mention} Lolz')

    @command()
    @has_permissions(administrator=True)
    async def baconpatrolloff(self, ctx):
        """
        That's enough of that now.

        :param ctx:
        :param saycon:
        :return:
        """
        if ctx.guild not in self.guild_info:
            await ctx.message.channel.send(f"{ctx.message.author.mention} I don't even know what that means")
            return
        del self.guild_info[ctx.guild]
        await ctx.message.channel.send(f'{ctx.message.author.mention} No fun')

    @Cog.listener()
    async def on_message(self, message):
        """
        When Baconpatroller praises us, thank him.

        :param message:
        :return:
        """
        # If this is a DM, do nothing.
        if message.guild is None:
            return

        if message.guild not in self.guild_info:
            return
        baconpatrol = self.guild_info[message.guild]
        if not baconpatrol["active"]:
            return
        if message.channel != baconpatrol["channel"]:
            return
        if message.author != message.guild.get_member(self.bot.user.id):
            return

        # Having reached here, we know the bot just sent a message; wait and see if the next message is from
        # Baconpatroller.
        msg = await self.bot.wait_for("message", check=lambda message: message.channel == baconpatrol["channel"])
        if msg.author == baconpatrol["baconpatroller"] and msg.content == baconpatrol["bacon_sez"]:
            async with baconpatrol["channel"].typing():
                await baconpatrol["channel"].send(baconpatrol["reply"])

            baconpatrol["active"] = False
            await baconpatrol["controll_channel"].send(f'{baconpatrol["troll"].mention} it is done.')
