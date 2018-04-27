import logging
import asyncio
import argparse
import json

from discord.ext import commands

from bot.verification_cog import VerificationCog
from bot.verification_db import GuildInfoDB

__author__ = "Richard Liang"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--config", help="JSON file containing the required configuration",
                        default="./gvrd_grunt_config.json")
    args = parser.parse_args()

    with open(args.config, "rb") as f:
        settings = json.load(f)

    gvrd_grunt = commands.Bot(
        command_prefix=commands.when_mentioned_or(settings["command_prefix"]),
        description="A grunt worker for the GVRD servers' needs"
    )
    db = GuildInfoDB(settings["sqlite_db"])
    gvrd_grunt.add_cog(VerificationCog(gvrd_grunt, db))

    @gvrd_grunt.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        await ctx.message.channel.send(
            "{} {}".format(ctx.message.author.mention, error)
        )

    file_handler = logging.FileHandler(filename=settings["log_file"], encoding="utf-8", mode="w")

    handlers = [file_handler, logging.StreamHandler()]

    logging.basicConfig(
        format="%(asctime)s | %(name)10s | %(levelname)8s | %(message)s",
        level=logging.DEBUG if args.debug else logging.INFO,
        handlers=handlers
    )

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("websockets.protocol").setLevel(logging.INFO)

    loop = asyncio.get_event_loop()

    gvrd_grunt.run(settings["token"], loop=loop, bot=True)


if __name__ == "__main__":
    main()
