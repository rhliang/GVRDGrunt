#! /usr/bin/env python

import json

from sqlite_modules import raid_fyi_db as db


def convert_to_dict(fyi_db):
    """
    Convert a RaidFYIDB object's contents to a dictionary.
    :param fyi_db:
    :return:
    """
    # Get all guild IDs in the database.
    all_guild_configurations = []
    with fyi_db.conn:
        guild_info_cursor = fyi_db.conn.execute(
            """
            select 
                guild_id
            from raid_fyi;
            """
        )

        for guild_id in guild_info_cursor:
            guild_fyi_config = fyi_db.get_fyi_info(guild_id)
            guild_fyi_config["guild_id"] = guild_id
            all_guild_configurations.append(guild_fyi_config)

    return all_guild_configurations


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract all FYI configuration from a GruntBot DB as JSON.")
    parser.add_argument("db", help="Path to the SQLite DB to extract from.")
    parser.add_argument("--output", default="out.json", help="")

    args = parser.parse_args()

    fyi_db = db.RaidFYIDB(args.db)
    with open(args.output, "w") as f:
        f.write(json.dumps(convert_to_dict(fyi_db)))


if __name__ == "__main__":
    main()
