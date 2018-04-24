"""1
A script that initializes the guild info DB.  This should only be run once!
"""

from bot import settings
from bot import guild_info_db


def main():
    guild_db = guild_info_db.GuildInfoDB(settings.sqlite_db)
    guild_db.initialize()


if __name__ == "__main__":
    main()
