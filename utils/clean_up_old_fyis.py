#! /usr/bin/env python

import json
import argparse
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from dataclasses import dataclass

import boto3
from boto3.dynamodb.conditions import Key, Attr


def get_guilds(table) -> List[int]:
    """
    Retrieve a list of all guilds from the specified RaidFYIDB table.
    :param table_name:
    :return:
    """
    last_evaluated_key = None
    results = []
    while True:
        scan_args = {
            "ProjectionExpression": "guild_id",
            "FilterExpression": Attr("config_channel_message").eq("config"),
        }
        if last_evaluated_key is not None:
            scan_args["ExclusiveStartKey"] = last_evaluated_key
        response = table.scan(**scan_args)
        results.extend(response["Items"])

        last_evaluated_key = response.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            break
    return [int(guild_info["guild_id"]) for guild_info in results]


@dataclass
class FYIToDelete:
    guild_id: int
    chat_channel_id: int
    command_message_id: int
    relay_channel_id: int
    relay_message_id: int
    chat_relay_message_id: Optional[int]


def get_expired_fyis(table, guild_id: int, expired_by: datetime) -> List[FYIToDelete]:
    """
    Retrieve data on all FYIs expired prior to the specified timestamp, exclusive.

    :param guild_id:
    :param expired_by: a Python datetime object **in UTC**
    :return:
    """
    channel_message_pattern = "channel([0-9]+)#message([0-9]+)"

    last_evaluated_key = None
    results = []
    while True:
        query_args = {
            "IndexName": "FYIsByExpiry",
            "KeyConditionExpression": Key("guild_id").eq(guild_id) & Key("expiry").lt(expired_by.isoformat())
        }
        if last_evaluated_key is not None:
            query_args["ExclusiveStartKey"] = last_evaluated_key
        response = table.query(**query_args)
        results.extend(response["Items"])
        last_evaluated_key = response.get("LastEvaluatedKey")
        if last_evaluated_key is None:
            break

    expired_fyis: List[FYIToDelete] = []
    for fyi_info in results:
        chat_relay_message_id = None
        if fyi_info["chat_relay_message_id"] is not None:
            chat_relay_message_id = int(fyi_info["chat_relay_message_id"])
        expired_fyis.append(
            FYIToDelete(
                guild_id=guild_id,
                chat_channel_id=int(
                    re.match(
                        channel_message_pattern,
                        fyi_info["config_channel_message"],
                    ).group(1)
                ),
                command_message_id=int(
                    re.match(
                        channel_message_pattern,
                        fyi_info["config_channel_message"],
                    ).group(2)
                ),
                relay_channel_id=int(fyi_info["relay_channel_id"]),
                relay_message_id=int(fyi_info["relay_message_id"]),
                chat_relay_message_id=chat_relay_message_id,
            )
        )
    return expired_fyis


def delete_fyi(
        table,
        fyi: FYIToDelete,
):
    """
    Delete the FYI based on the given channel and message ID.

    :return:
    """
    channel_message_template = "channel{}#message{}"
    with table.batch_writer() as batch:
        channels_and_messages: List[Tuple[int, int]] = [
            (fyi.chat_channel_id, fyi.command_message_id),
            (fyi.relay_channel_id, fyi.relay_message_id),
        ]
        if fyi.chat_relay_message_id is not None:
            channels_and_messages.append(
                (fyi.chat_channel_id, fyi.chat_relay_message_id)
            )

        for channel_id, message_id in channels_and_messages:
            batch.delete_item(
                Key={
                    "guild_id": fyi.guild_id,
                    "config_channel_message": channel_message_template.format(
                        channel_id, message_id
                    ),
                }
            )


def main():
    parser = argparse.ArgumentParser(
        """Clean up expired FYIs."""
    )
    parser.add_argument(
        "--config",
        help="JSON file containing the required configuration",
        default="./gvrd_grunt_config.json",
    )
    parser.add_argument(
        "--update",
        help="Print a status message after each batch of this "
             "many FYIs has been deleted",
        default=100,
    )
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

    guilds: List[int] = get_guilds(table)

    expired_by = datetime.now(timezone.utc)

    for guild_id in guilds:
        print(f"Cleaning up FYIs for guild {guild_id}.")
        expired_fyis: List[FYIToDelete] = get_expired_fyis(table, guild_id, expired_by)
        print(f"Removing {len(expired_fyis)} FYIs for this guild:")

        for i, fyi in enumerate(expired_fyis, start=1):
            delete_fyi(table, fyi)
            if i % args.update == 0:
                print(f"{i} removed.")

        print("Done.\n")


if __name__ == "__main__":
    main()
