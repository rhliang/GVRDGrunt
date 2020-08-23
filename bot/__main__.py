import argparse
import asyncio
import json
import logging

from discord.ext import commands

from bot.baconpatroll_cog import BaconpaTrollCog
from bot.ex_gate_cog import EXGateCog
from bot.ex_gate_db import EXGateDB
from bot.no_command_subscription_cog import NoCommandSubscriptionCog
from bot.no_command_subscription_db import NoCommandSubscriptionDB
# from bot.spam_cog import SpamCog
from bot.purge_channels_cog import PurgeChannelsCog
from bot.role_reaction_subscription_cog import RoleReactionSubscriptionCog
from bot.role_reaction_subscription_db import RoleReactionSubscriptionDB
from bot.role_reminder_cog import RoleReminderCog
from bot.role_reminder_db import RoleReminderDB
from bot.role_set_operations_cog import RoleSetOperationsCog

from bot.raid_fyi_db import RaidFYIDB
from bot.raid_fyi_cog import RaidFYICog
from bot.bot_perms_db import BotPermsDB
from bot.bot_perms_cog import BotPermsCog
from bot.verification_db import VerificationDB
from bot.verification_cog import VerificationCog
from bot.guild_logging_db import GuildLoggingDB
from bot.guild_logging_cog import GuildLoggingCog

__author__ = "Richard Liang"


class BadBot(commands.Bot):
    """
    A subclass of Bot that allows other bots to run its commands.

    This was probably rightfully disabled by discord.py but for now we need it.
    We'll eliminate it in the future when we implement some more elegant
    way for another bot to communicate with this bot.
    """
    async def process_commands(self, message):
        """
        This override of the subclass method allows another bot to run commands.
        :param message:
        :return:
        """
        ctx = await self.get_context(message)
        await self.invoke(ctx)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--config", help="JSON file containing the required configuration",
                        default="./gvrd_grunt_config.json")
    args = parser.parse_args()

    with open(args.config, "rb") as f:
        settings = json.load(f)

    loop = asyncio.get_event_loop()

    gvrd_grunt = BadBot(
        command_prefix=commands.when_mentioned_or(settings["command_prefix"]),
        description="A grunt worker for the GVRD servers' needs",
        loop=loop
    )

    logging_db = GuildLoggingDB(settings["sqlite_db"])
    ex_db = EXGateDB(settings["sqlite_db"])
    role_reaction_subscription_db = RoleReactionSubscriptionDB(settings["sqlite_db"])
    no_command_subscription_db = NoCommandSubscriptionDB(settings["sqlite_db"])
    role_reminder_db = RoleReminderDB(settings["sqlite_db"])

    # These databases are on DynamoDB.
    raid_fyi_db = RaidFYIDB(
        table_name=settings["fyi_table"],
        endpoint_url=settings["endpoint_url"],
        region_name=settings["region_name"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"]
    )
    bot_perms_db = BotPermsDB(
        table_name=settings["bot_perms_table"],
        endpoint_url=settings["endpoint_url"],
        region_name=settings["region_name"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"]
    )
    verification_db = VerificationDB(
        table_name=settings["verification_table"],
        endpoint_url=settings["endpoint_url"],
        region_name=settings["region_name"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"]
    )
    logging_db = GuildLoggingDB(
        table_name=settings["guild_logging_table"],
        endpoint_url=settings["endpoint_url"],
        region_name=settings["region_name"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"]
    )

    # These have been converted to check bot perms under the new scheme.
    logging_cog = GuildLoggingCog(gvrd_grunt, logging_db, bot_perms_db)
    gvrd_grunt.add_cog(logging_cog)
    gvrd_grunt.add_cog(BotPermsCog(gvrd_grunt, bot_perms_db))
    gvrd_grunt.add_cog(
        RaidFYICog(
            gvrd_grunt,
            raid_fyi_db,
            settings["fyi_clean_up_hours"],
            settings["fyi_clean_up_minutes"],
            settings["fyi_clean_up_seconds"],
            bot_perms_db,
            logging_cog=logging_cog
        )
    )
    gvrd_grunt.add_cog(VerificationCog(gvrd_grunt, verification_db, bot_perms_db))

    # These are the old-style cogs.
    gvrd_grunt.add_cog(EXGateCog(gvrd_grunt, ex_db, logging_cog=logging_cog))
    gvrd_grunt.add_cog(RoleReactionSubscriptionCog(gvrd_grunt, role_reaction_subscription_db, logging_cog=logging_cog))
    gvrd_grunt.add_cog(BaconpaTrollCog(gvrd_grunt))
    gvrd_grunt.add_cog(NoCommandSubscriptionCog(gvrd_grunt, no_command_subscription_db, logging_cog=logging_cog))
    gvrd_grunt.add_cog(RoleSetOperationsCog(gvrd_grunt))
    gvrd_grunt.add_cog(PurgeChannelsCog(gvrd_grunt))
    gvrd_grunt.add_cog(RoleReminderCog(gvrd_grunt, role_reminder_db, logging_cog=logging_cog))


    # For testing only -- *do not install on a production bot!*
    # gvrd_grunt.add_cog(SpamCog())

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

    gvrd_grunt.run(settings["token"], bot=True)


if __name__ == "__main__":
    main()
