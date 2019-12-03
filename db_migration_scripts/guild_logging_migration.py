#! /usr/bin/env python

import json
import sqlite3


def get_all_guild_logging_configuration(conn, new_table_name="GuildLogging"):
    """
    Return all guild logging configuration in a dictionary.

    :param conn:
    :param new_table_name:
    :return:
    """
    all_configuration = []
    with conn:
        guild_info_cursor = conn.execute("select * from guild_logging;")
        for row in guild_info_cursor:
            guild_config = {
                "guild_id": {"N": str(row[0])},
                "log_channel": {"N": str(row[1])}
            }
            all_configuration.append(guild_config)

    return {new_table_name: [{"PutRequest": {"Item": x}} for x in all_configuration]}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract all guild logging configuration from a GruntBot DB as JSON.")
    parser.add_argument("db", help="Path to the SQLite DB to extract from.")
    parser.add_argument(
        "--new_table_name",
        help="Name of the new DynamoDB table that records will go into",
        default="GuildLogging"
    )
    parser.add_argument("--output", default="out.json", help="")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    with open(args.output, "w") as f:
        json.dump(get_all_guild_logging_configuration(conn, new_table_name=args.new_table_name), f, indent=4)


if __name__ == "__main__":
    main()
