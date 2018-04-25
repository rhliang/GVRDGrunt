import logging
import asyncio
import argparse

from discord.ext import commands

from bot.verification_cog import VerificationCog
from bot.guild_info_db import GuildInfoDB
from bot import settings

__author__ = "Richard Liang"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    chespin = commands.Bot(
        command_prefix=commands.when_mentioned_or("."),
        description="A grunt worker for the GVRD servers' needs"
    )
    db = GuildInfoDB(settings.sqlite_db)
    chespin.add_cog(VerificationCog(chespin, db))

    @chespin.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        await ctx.message.channel.send(
            "{} Command failed with message: {}".format(ctx.message.author.mention, error)
        )


    file_handler = logging.FileHandler(filename="output.log", encoding="utf-8", mode="w")

    handlers = [file_handler, logging.StreamHandler()]

    logging.basicConfig(
        format="%(asctime)s | %(name)10s | %(levelname)8s | %(message)s",
        level=logging.DEBUG if args.debug else logging.INFO,
        handlers=handlers
    )

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("websockets.protocol").setLevel(logging.INFO)

    loop = asyncio.get_event_loop()

    chespin.run(settings.token, loop=loop, bot=True)


if __name__ == "__main__":
    main()
