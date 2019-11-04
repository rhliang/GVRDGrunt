#! /usr/bin/env python

import json
import sqlite3


def get_all_fyi_configuration(conn):
    """
    Return all raid FYI configuration in a dictionary.

    :param conn:
    :return:
    """
    all_configuration = []
    with conn:
        guild_info_cursor = conn.execute(
            """
            select
                guild_id, 
                fyi_emoji,
                fyi_emoji_type
            from raid_fyi;
            """
        )

        for guild_id, fyi_emoji, fyi_emoji_type in guild_info_cursor:
            guild_config = {
                "guild_id": guild_id,
                "config_channel_message": "config",
                "fyi_emoji": fyi_emoji,
                "fyi_emoji_type": fyi_emoji_type,
                "enhanced": False,
                "rsvp_emoji": None,
                "rsvp_emoji_type": None,
                "timezone": "America/Vancouver"
            }

            # Retrieve all channel mappings for this guild.
            guild_channel_mappings = []
            channel_mapping_cursor = conn.execute(
                """
                select
                    chat_channel_id,
                    fyi_channel_id
                from raid_fyi_channel_mapping
                where guild_id = ?;
                """,
                (guild_id,)
            )

            for chat_channel_id, fyi_channel_id in channel_mapping_cursor:
                channel_mapping_config = {
                    "guild_id": guild_id,
                    "config_channel_message": "chatchannel{}".format(chat_channel_id),
                    "relay_channel": fyi_channel_id
                }
                guild_channel_mappings.append(channel_mapping_config)

            all_configuration.append(guild_config)
            all_configuration.extend(guild_channel_mappings)

    return all_configuration

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract all FYI configuration from a GruntBot DB as JSON.")
    parser.add_argument("db", help="Path to the SQLite DB to extract from.")
    parser.add_argument("--output", default="out.json", help="")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    with open(args.output, "w") as f:
        json.dump(get_all_fyi_configuration(conn), f, indent=4)


if __name__ == "__main__":
    main()
