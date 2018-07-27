import logging
import asyncio
import argparse
import json

from discord.ext import commands

# from bot.verification_cog import VerificationCog
# from bot.verification_db import VerificationDB
# from bot.guild_logging_cog import GuildLoggingCog
# from bot.guild_logging_db import GuildLoggingDB
# from bot.ex_gate_cog import EXGateCog
# from bot.ex_gate_db import EXGateDB
# from bot.role_reaction_subscription_cog import RoleReactionSubscriptionCog
# from bot.role_reaction_subscription_db import RoleReactionSubscriptionDB
# from bot.baconpatroll_cog import BaconpaTrollCog
# from bot.no_command_subscription_cog import NoCommandSubscriptionCog
# from bot.no_command_subscription_db import NoCommandSubscriptionDB
# from bot.role_set_operations_cog import RoleSetOperationsCog
# from bot.purge_channels_cog import PurgeChannelsCog

from bot.spam_cog import SpamCog

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
        command_prefix=commands.when_mentioned(),
        description="Spams a channel."
    )
    # verification_db = VerificationDB(settings["sqlite_db"])
    # logging_db = GuildLoggingDB(settings["sqlite_db"])
    # ex_db = EXGateDB(settings["sqlite_db"])
    # role_reaction_subscription_db = RoleReactionSubscriptionDB(settings["sqlite_db"])
    # no_command_subscription_db = NoCommandSubscriptionDB(settings["sqlite_db"])

    # logging_cog = GuildLoggingCog(gvrd_grunt, logging_db)
    # gvrd_grunt.add_cog(VerificationCog(gvrd_grunt, verification_db))
    # gvrd_grunt.add_cog(logging_cog)
    # gvrd_grunt.add_cog(EXGateCog(gvrd_grunt, ex_db, logging_cog=logging_cog))
    # gvrd_grunt.add_cog(RoleReactionSubscriptionCog(gvrd_grunt, role_reaction_subscription_db, logging_cog=logging_cog))
    # gvrd_grunt.add_cog(BaconpaTrollCog(gvrd_grunt))
    # gvrd_grunt.add_cog(NoCommandSubscriptionCog(gvrd_grunt, no_command_subscription_db, logging_cog=logging_cog))
    # gvrd_grunt.add_cog(RoleSetOperationsCog(gvrd_grunt))
    # gvrd_grunt.add_cog(PurgeChannelsCog(gvrd_grunt))

    # For testing only -- *do not install on a production bot!*
    gvrd_grunt.add_cog(SpamCog())

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
