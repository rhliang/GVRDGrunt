import boto3
from boto3.dynamodb.conditions import Key
import discord
import re
import dateutil
import pytz

from bot.convert_using_guild import emoji_converter


# The schema of the database:
#
# (guild[guild id], config):
# - fyi_emoji (string or emoji ID)
# - fyi_emoji_type ("normal" or "custom")
# - enhanced (Boolean)
# - rsvp_emoji (string or emoji ID)
# - rsvp_emoji_type ("normal" or "custom")
# - timezone (in a form that pytz recognizes, e.g. "America/Vancouver"
#
# (guild[guild id], chatchannel[channel id]):
# - relay_channel (channel ID)
#
# (guild[guild id], channel[channel id]#message[message id])
# If this message is the original:
# - timestamp
# - creator
# - relay_messages (a list of (channel ID, message ID) pair pointing at the relay messages -- only on original)
# - time (datetime of the command -- only on original)
# If this message is a relay:
# - command_message (a (channel ID, message ID) pair pointing to the original command message -- only on relays)

chat_channel_pattern = "chatchannel(.+)"
channel_message_template = "channel{}#message{}"
channel_message_pattern = "channel([0-9]+)#message([0-9]+)"


class RaidFYIDB(object):
    """
    A class representing the database we use to store our information.
    """
    def __init__(self, *args, **kwargs):
        # The database can be initialized with raid_fyi_initialization.json
        self.db = boto3.resource("dynamodb", *args, **kwargs)
        self.table = self.db.Table("RaidFYI")

    def get_fyi_info(self, guild: discord.Guild):
        """
        Return this guild's raid FYI configuration.

        :param guild:
        :return:
        """
        # Get the base guild configuration.
        response = self.table.get_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": "config"
            }
        )
        result = response.get("Item")
        if result is None:
            return

        result["timezone"] = pytz.timezone(result["timezone"])

        if result["fyi_emoji_type"] == "custom":
            result["fyi_emoji"] = emoji_converter(guild, result["fyi_emoji"])
        del result["fyi_emoji_type"]

        if result["enhanced"]:
            if result["rsvp_emoji_type"] == "custom":
                result["rsvp_emoji"] = emoji_converter(guild, result["rsvp_emoji"])
            del result["rsvp_emoji_type"]

        # Get all channel mappings.
        response = self.table.query(
            KeyConditionExpression=(Key("guild_id").eq(guild.id) &
                                    Key("config_channel_message").begins_with("chatchannel"))
        )
        raw_channel_mappings = response["Items"]  # this is a list

        channel_mappings = {}
        for chat_channel_config in raw_channel_mappings:
            chat_channel_id = int(re.match(chat_channel_pattern, chat_channel_config["config_channel_message"]))
            chat_channel = guild.get_channel(chat_channel_id)
            relay_channel = guild.get_channel(chat_channel_config["relay_channel"])
            channel_mappings[chat_channel] = relay_channel

        result["channel_mappings"] = channel_mappings
        return result

    def configure_fyi(
            self,
            guild: discord.Guild,
            fyi_emoji,
            tz_string
    ):
        """
        Configure the guild's FYI functionality.

        :param guild:
        :param fyi_emoji:
        :param tz_string:
        :raises:
        :return:
        """
        emoji_type = "normal"
        emoji_stored_value = fyi_emoji
        if isinstance(fyi_emoji, discord.Emoji):
            emoji_type = "custom"
            emoji_stored_value = fyi_emoji.id

        # Sanity check: convert the timezone string to an actual timezone.
        # We don't catch the exception; we'll let it go upward.
        pytz.timezone(tz_string)

        self.table.put_item(
            Item={
                "guild_id": guild.id,
                "config_channel_message": "config",
                "fyi_emoji": emoji_stored_value,
                "fyi_emoji_type": emoji_type,
                "enhanced": False,
                "rsvp_emoji": None,
                "rsvp_emoji_type": None,
                "timezone": tz_string
            }
        )

    def deactivate_fyi(self, guild: discord.Guild):
        """
        Disable the guild's FYI functionality by removing its configuration from the database.

        :param guild:
        :return:
        """
        self.table.delete_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": "config"
            }
        )

    def activate_enhanced_fyi(self, guild: discord.Guild, rsvp_emoji):
        """
        Enable enhanced FYI functionality for the guild.

        :param guild:
        :param rsvp_emoji:
        :return:
        """
        emoji_type = "normal"
        emoji_stored_value = rsvp_emoji
        if isinstance(rsvp_emoji, discord.Emoji):
            emoji_type = "custom"
            emoji_stored_value = rsvp_emoji.id

        self.table.update_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": "config"
            },
            UpdateExpression="SET enhanced = :enhanced, rsvp_emoji = :rsvp_emoji, rsvp_emoji_type = :rsvp_emoji_type",
            ExpressionAttributeValues={
                ":enhanced": True,
                ":rsvp_emoji": emoji_stored_value,
                ":rsvp_emoji_type": emoji_type
            }
        )

    def deactivate_enhanced_fyi(self, guild: discord.Guild):
        """
        Disable the guild's enhanced FYI functionality.

        :param guild:
        :return:
        """
        self.table.update_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": "config"
            },
            UpdateExpression="SET enhanced = :enhanced, rsvp_emoji = :rsvp_emoji, rsvp_emoji_type = :rsvp_emoji_type",
            ExpressionAttributeValues={
                ":enhanced": False,
                ":rsvp_emoji": None,
                ":rsvp_emoji_type": None
            }
        )

    def register_fyi_channel_mapping(
            self,
            guild: discord.Guild,
            chat_channel: discord.TextChannel,
            fyi_channel: discord.TextChannel
    ):
        """
        Register a chat-channel-to-FYI-channel mapping.

        :param guild:
        :param chat_channel:
        :param fyi_channel:
        :return:
        """
        self.table.put_item(
            Item={
                "guild_id": guild.id,
                "config_channel_message": "chatchannel{}".format(chat_channel.id),
                "relay_channel": fyi_channel.id
            }
        )

    def deregister_fyi_channel_mapping(self, guild: discord.Guild, chat_channel: discord.TextChannel):
        """
        Deregister the specified FYI channel mapping.

        :param guild:
        :param chat_channel:
        :return:
        """
        self.table.delete_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": "chatchannel{}".format(chat_channel.id)
            }
        )

    def deregister_all_fyi_channel_mappings(self, guild: discord.Guild):
        """
        Deregister all FYI channel mappings for the specified guild.

        :param guild:
        :return:
        """
        response = self.table.query(
            KeyConditionExpression=(Key("guild_id").eq(guild.id) &
                                    Key("config_channel_message").begins_with("chatchannel"))
        )
        raw_channel_mappings = response["Items"]  # this is a list

        for raw_channel_mapping in raw_channel_mappings:
            self.table.delete_item(
                Key={
                    "guild_id": guild.id,
                    "config_channel_message": raw_channel_mapping["config_channel_message"]
                }
            )

    def add_fyi(
            self,
            guild: discord.Guild,
            creator: discord.Member,
            timestamp,
            chat_channel: discord.TextChannel,
            command_message_id,
            relay_channel: discord.TextChannel,
            relay_message_id
    ):
        """
        Create records for an FYI.

        :param guild:
        :param creator:
        :param timestamp: a Python datetime object showing the creation time **in UTC**
        :param chat_channel:
        :param command_message_id:
        :param relay_channel:
        :param relay_message_id:
        :return:
        """
        with self.table.batch_writer() as batch:
            batch.put_item(
                Item={
                    "guild_id": guild.id,
                    "config_channel_message": channel_message_template.format(chat_channel.id, command_message_id),
                    "creator_id": creator.id,
                    "timestamp": timestamp.isoformat(),
                    "relay_channel_id": relay_channel.id,
                    "relay_message_id": relay_message_id
                }
            )
            batch.put_item(
                Item={
                    "guild_id": guild.id,
                    "config_channel_message": channel_message_template.format(relay_channel.id, relay_message_id),
                    "chat_channel_id": chat_channel.id,
                    "command_message_id": command_message_id
                }
            )

    def get_fyi(
            self,
            guild: discord.Guild,
            channel: discord.TextChannel,
            message_id
    ):
        """
        Retrieve the information about this FYI based on the given channel and message ID.

        These may be either the original command message or the relay message.

        :param guild:
        :param channel:
        :param message_id:
        :return:
        """
        response = self.table.get_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": channel_message_template.format(channel.id, message_id)
            }
        )
        result = response.get("Item")
        if result is None:
            return

        # Check if this is the command or the relay.
        if "creator_id" in result:
            chat_channel = channel
            command_message_id = message_id
            relay_channel = guild.get_channel(result["relay_channel_id"])
            relay_message_id = result["relay_message_id"]
            command_message_result = result
        else:
            relay_channel = channel
            relay_message_id = message_id
            chat_channel = guild.get_channel(result["chat_channel_id"])
            command_message_id = result["command_message_id"]
            # Get the record for the command message.
            response = self.table.get_item(
                Key={
                    "guild_id": guild.id,
                    "config_channel_message": channel_message_template.format(chat_channel.id, command_message_id)
                }
            )
            command_message_result = response.get("Item")

        timestamp = dateutil.parser.parse(command_message_result["timestamp"])
        creator = guild.get_member(command_message_result["creator_id"])

        # command_message = await chat_channel.get_message(command_message_id)
        # relay_message = await relay_channel.get_message(relay_message_id)
        # return command_message, relay_message, timestamp, creator
        return chat_channel, command_message_id, relay_channel, relay_message_id, timestamp, creator

    def delete_fyi(
            self,
            guild: discord.Guild,
            channel: discord.TextChannel,
            message_id
    ):
        """
        Delete the FYI based on the given channel and message ID.

        These may be either the original command message or the relay message.

        :param guild:
        :param channel:
        :param message_id:
        :return:
        """
        response = self.table.get_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": channel_message_template.format(channel.id, message_id)
            }
        )
        result = response.get("Item")
        if result is None:
            return

        # Check if this is the command or the relay.
        if "creator_id" in result:
            chat_channel = channel
            command_message_id = message_id
            relay_channel = guild.get_channel(result["relay_channel_id"])
            relay_message_id = result["relay_message_id"]
        else:
            relay_channel = channel
            relay_message_id = message_id
            chat_channel = guild.get_channel(result["chat_channel_id"])
            command_message_id = result["command_message_id"]

        with self.table.batch_writer() as batch:
            batch.delete_item(
                Key={
                    "guild_id": guild.id,
                    "config_channel_message": channel_message_template.format(chat_channel.id, command_message_id)
                }
            )
            batch.delete_item(
                Key={
                    "guild_id": guild.id,
                    "config_channel_message": channel_message_template.format(relay_channel.id, relay_message_id)
                }
            )

    def delete_fyis_older_than(self, guild: discord.Guild, timestamp):
        """
        Retrieve data on all FYIs prior to the specified timestamp, inclusive.

        :param guild:
        :param timestamp: a Python datetime object **in UTC**
        :return:
        """
        response = self.table.query(
            IndexName="FYIsByTime",
            KeyConditionExpression=Key("guild_id").eq(guild.id) & Key("timestamp").lt(timestamp.isoformat())
        )

        with self.table.batch_writer() as batch:
            for command_message_record in response["Items"]:
                channel_message_match = re.match(channel_message_pattern,
                                                 command_message_record["config_channel_message"])
                chat_channel_id = int(channel_message_match.group(1))
                command_message_id = int(channel_message_match.group(2))

                relay_channel_id = command_message_record["relay_channel_id"]
                relay_message_id = command_message_record["relay_message_id"]

                batch.delete_item(
                    Key={
                        "guild_id": guild.id,
                        "config_channel_message": channel_message_template.format(chat_channel_id, command_message_id)
                    }
                )
                batch.delete_item(
                    Key={
                        "guild_id": guild.id,
                        "config_channel_message": channel_message_template.format(relay_channel_id, relay_message_id)
                    }
                )

