#! /usr/bin/env python

import json
import sqlite3


def get_all_verification_configuration(conn, new_table_name="GuildVerification"):
    """
    Return all raid FYI configuration in a dictionary.

    :param conn:
    :param new_table_name:
    :return:
    """
    all_configuration = []
    with conn:
        guild_info_cursor = conn.execute("select * from verification_info;")
        for row in guild_info_cursor:
            guild_config = {
                "guild_id": {"N": str(row[0])},
                "screenshot_channel": {"N": str(row[1])},
                "help_channel": {"N": str(row[2])},
                "denied_message": {"S": row[3]},
                "welcome_role": {"N": str(row[4])},
                "instinct_role": {"N": str(row[5])},
                "mystic_role": {"N": str(row[6])},
                "valor_role": {"N": str(row[7])},
                "instinct_emoji": {"N": str(row[8])},
                "instinct_emoji_type": {"S": row[9]},
                "mystic_emoji": {"N": str(row[10])},
                "mystic_emoji_type": {"S": row[11]},
                "valor_emoji": {"N": str(row[12])},
                "valor_emoji_type": {"S": row[13]},
                "welcome_message": {"S": row[14]},
                "welcome_channel": {"N": str(row[15])}
            }

            # Retrieve all standard roles for this guild.
            channel_mapping_cursor = conn.execute(
                """
                select
                    role_id,
                    mandatory
                from guild_standard_roles
                where guild_id = ?;
                """,
                (row[0],)
            )
            channel_mappings = list(channel_mapping_cursor)
            guild_config["standard_roles"] = {
                "L": [{"N": str(role_id)} for role_id, mandatory in channel_mappings if not mandatory]
            }
            guild_config["mandatory_roles"] = {
                "L": [{"N": str(role_id)} for role_id, mandatory in channel_mappings if mandatory]
            }
            all_configuration.append(guild_config)

    return {new_table_name: [{"PutRequest": {"Item": x}} for x in all_configuration]}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract all FYI configuration from a GruntBot DB as JSON.")
    parser.add_argument("db", help="Path to the SQLite DB to extract from.")
    parser.add_argument(
        "--new_table_name",
        help="Name of the new DynamoDB table that records will go into",
        default="GuildVerification"
    )
    parser.add_argument("--output", default="out.json", help="")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    with open(args.output, "w") as f:
        json.dump(get_all_verification_configuration(conn, new_table_name=args.new_table_name), f, indent=4)


if __name__ == "__main__":
    main()
