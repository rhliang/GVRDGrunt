import discord
import asyncio
from discord.ext.commands import command, has_permissions, Cog

__author__ = 'Richard Liang'


class PurgeChannelsCog(Cog):
    """
    Purge channels and/or categories.
    """
    def __init__(self, bot):
        self.bot = bot
        self.timeout = 30
        self.confirmation_time = 5

    @command()
    @has_permissions(manage_messages=True)
    async def set_purge_timeout(self, ctx, timeout: int):
        """
        Set the number of seconds that the bot waits for confirmation before purging channels.

        :param ctx:
        :param timeout:
        :return:
        """
        if timeout <= 0:
            raise ValueError("Timeout must be a positive integer.")
        self.timeout = timeout
        async with ctx.channel.typing():
            await ctx.channel.send(f"{ctx.author.mention} Purge will wait {self.timeout} seconds for confirmation.")

    @command()
    @has_permissions(manage_messages=True)
    async def set_purge_confirmation_time(self, ctx, confirmation_time: int):
        """
        Set the number of seconds that the bot displays the post-purge confirmation message in a purged channel.

        :param ctx:
        :param confirmation_time:
        :return:
        """
        if confirmation_time <= 0:
            raise ValueError("Confirmation time must be a positive integer.")
        self.confirmation_time = confirmation_time
        async with ctx.channel.typing():
            await ctx.channel.send(
                f"{ctx.author.mention} Purge will display {self.confirmation_time} seconds for confirmation.")

    async def purge_channel_helper(self, channel: discord.TextChannel, num_messages=None):
        """
        Purge the specified channel.  If a number of messages is specified, limit it to that many.

        :param channel:
        :param num_messages:
        :return:
        """
        messages_to_purge = await channel.history(limit=num_messages).flatten()
        num_messages = len(messages_to_purge)

        # First, clear the pins.
        num_pins_cleared = 0
        messages_to_purge_ids = [x.id for x in messages_to_purge]
        for pinned_message in await channel.pins():
            if pinned_message.id in messages_to_purge_ids:
                await pinned_message.unpin()
                num_pins_cleared += 1
        await channel.purge(limit=num_messages)
        return num_messages, num_pins_cleared

    @command()
    @has_permissions(manage_messages=True)
    async def purgecategory(self, ctx, category: discord.CategoryChannel):
        """
        Purge the entire specified category.

        The bot must have Manage Messages permissions on all the channels in this category.
        :param ctx:
        :param category:
        :return:
        """
        if len(category.channels) == 0:
            async with ctx.channel.typing():
                await ctx.channel.send(f"Category {category} has no channels to purge.")
            return

        confirmation_message = "Purging the following channels:\n"
        for channel in category.channels:
            confirmation_message += f" - {channel}\n"
        confirmation_message += f"Do you wish to continue (y/n)?  Will cancel in {self.timeout} seconds."

        def check(m):
            if m.author != ctx.author:
                return False
            elif m.content.lower() in ("y", "n", "yes", "no"):
                return True

        async with ctx.channel.typing():
            await ctx.channel.send(confirmation_message)
        cancel_purge = False
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=self.timeout)
            if msg.content.lower() not in ("y", "yes"):
                cancel_purge = True
        except asyncio.TimeoutError:
            cancel_purge = True

        if cancel_purge:
            async with ctx.channel.typing():
                await ctx.channel.send(f"{ctx.author.mention} Category purge cancelled.")
            return

        # Having reached here, we know we want to purge the channels.
        async with ctx.channel.typing():
            for channel in category.channels:
                # Purge this channel.
                await ctx.channel.send(f"Purging channel {channel}...")
                messages_deleted, pins_cleared = await self.purge_channel_helper(channel)
                await ctx.channel.send(f"Deleted {messages_deleted} messages; cleared {pins_cleared} pins.")

    @command()
    @has_permissions(manage_messages=True)
    async def purgechannel(self, ctx, *num_to_purge):
        """
        Purge the current channel.

        The bot must have Manage Messages permissions on this channel.
        :param ctx:
        :param num_to_purge:
        :return:
        """
        async with ctx.channel.typing():
            messages_to_purge = None
            if len(num_to_purge) > 0:
                messages_to_purge = int(num_to_purge[0])
            messages_deleted, pins_cleared = await self.purge_channel_helper(
                ctx.channel,
                num_messages=messages_to_purge
            )
            confirmation_message = await ctx.channel.send(
                f"Deleted {messages_deleted} messages; cleared {pins_cleared} pins."
            )

        await asyncio.sleep(self.confirmation_time)
        await confirmation_message.delete()
