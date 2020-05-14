#! /usr/bin/env python

import json
import argparse
import boto3
from boto3.dynamodb.conditions import Attr


DEFAULT_REMOTE_EMOJI = "📡"

def get_guilds_and_enhanced_status(table):
    """
    Retrieve a list of all guilds from the specified RaidFYIDB table.
    :param table_name:
    :return:
    """
    response = table.scan(
        ProjectionExpression="guild_id,enhanced",
        FilterExpression=Attr("config_channel_message").eq("config")
    )
    status_by_guild = {}
    for guild_info in response["Items"]:
        status_by_guild[guild_info["guild_id"]] = guild_info["enhanced"]
    return status_by_guild


def add_remote_emoji_to_guild(table, guild_id, enhanced=False):
    """
    Add a "remote_emoji" and "remote_emoji_type" field to the specified guild.

    If this is an "enhanced" guild, add a default remote emoji.
    :param table:
    :param enhanced:
    :return:
    """
    expression_attribute_values = {
        ":remote_emoji": None,
        ":remote_emoji_type": None,
    }
    if enhanced:
        expression_attribute_values = {
            ":remote_emoji": DEFAULT_REMOTE_EMOJI,
            ":remote_emoji_type": "normal",
        }

    table.update_item(
        Key={
            "guild_id": guild_id,
            "config_channel_message": "config"
        },
        UpdateExpression="SET remote_emoji = :remote_emoji, "
                         "remote_emoji_type = :remote_emoji_type",
        ExpressionAttributeValues=expression_attribute_values,
    )


def main():
    parser = argparse.ArgumentParser(
        """Update FYI configuration to include a "remote" emoji."""
    )
    parser.add_argument("--config", help="JSON file containing the required configuration",
                        default="./gvrd_grunt_config.json")
    args = parser.parse_args()

    with open(args.config, "rb") as f:
        settings = json.load(f)

    db = boto3.resource(
        "dynamodb",
        endpoint_url=settings["endpoint_url"],
        region_name=settings["region_name"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"]
    )
    table = db.Table(settings["fyi_table"])

    status_by_guild = get_guilds_and_enhanced_status(table)
    for guild_id in status_by_guild:
        print(f"Updating guild {guild_id} (enhanced={status_by_guild[guild_id]})")
        add_remote_emoji_to_guild(table, guild_id, status_by_guild[guild_id])


if __name__ == "__main__":
    main()
