from discord.ext.commands import command
import discord
import asyncio

__author__ = 'Richard Liang'


class SpamCog(command.Cog):
    """
    Spam a channel for stress-testing purposes.  DO NOT LET THIS ANYWHERE NEAR A PRODUCTION BOT!
    """
    def __init__(self):
        self.counter = 0
        self.pause = 1.0
        self.channel = None

    @command.Cog.listener()
    async def on_ready(self):
        """
        Continually check whether spamming is on, and spam the channel if so.

        :return:
        """
        while True:
            if self.channel is not None:
                self.counter += 1
                await self.channel.send(f"Message {self.counter}")
                await asyncio.sleep(self.pause)
            else:
                await asyncio.sleep(1.0)

    @command()
    async def spam_away(self, ctx, channel: discord.TextChannel, pause: float):
        """
        Activate spamming on the specified channel.

        :param ctx:
        :param channel:
        :param pause:
        :return:
        """
        async with ctx.message.channel.typing():
            if self.channel is not None:
                await ctx.message.channel.send(
                    f"{ctx.author.mention} Channel {self.channel} is already being spammed."
                )
                return

            self.pause = pause
            self.channel = channel
            await ctx.message.channel.send(f"{ctx.author.mention} Spamming channel {channel} at an interval of "
                                           f"{pause} seconds.")

    @command()
    async def stop_spamming(self, ctx):
        """
        Stop spamming.

        :param ctx:
        :return:
        """
        async with ctx.message.channel.typing():
            if self.channel is None:
                await ctx.message.channel.send(
                    f"{ctx.author.mention} No channel is currently being spammed."
                )
            spam_channel = self.channel
            self.channel = None
            self.counter = 0
            await ctx.message.channel.send(f"{ctx.author.mention} Channel {spam_channel} is no longer being spammed.")
