import boto3
from boto3.dynamodb.conditions import Key
import discord
import re
import dateutil
import pytz

from bot.utils import emoji_to_db
from bot.convert_using_guild import emoji_converter


# The schema of the database:

# (guild[guild id], config):
# - fyi_emoji (string or emoji ID)
# - fyi_emoji_type ("normal" or "custom")
# - enhanced (Boolean)
# - relay_to_chat (Boolean)
# - rsvp_emoji (string or emoji ID)
# - rsvp_emoji_type ("normal" or "custom")
# - cancelled_emoji (string or emoji ID)
# - cancelled_emoji_type ("normal" or "custom")
# - timezone (in a form that pytz recognizes, e.g. "America/Vancouver"

# (guild[guild id], category[category id]):
# - relay_channel (channel ID)

# (guild[guild id], chatchannel[channel id]):
# - relay_channel (channel ID)

# (guild[guild id], channel[channel id]#message[message id])
# If this message is the original:
# - timestamp
# - creator
# - relay_message (a (channel ID, message ID) pair pointing at the relay message in the relay channel)
# - chat_relay_message (a (channel ID, message ID) pair pointing at the relay message in the chat channel, or None)
# - time (datetime of the command -- only on original)
# - edit_history (all of the edits made to this original post)
# - interested (a list of member IDs, denoting all who are interested)

# If this message is a relay:
# - command_message (a (channel ID, message ID) pair pointing to the original command message -- only on relays)
# - chat_or_relay (either "chat" or "relay", denotes which channel this one was posted in)

chat_channel_pattern = "chatchannel(.+)"
channel_message_template = "channel{}#message{}"
channel_message_pattern = "channel([0-9]+)#message([0-9]+)"
category_pattern = "category(.+)"


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
            if result["cancelled_emoji_type"] == "custom":
                result["cancelled_emoji"] = emoji_converter(guild, result["cancelled_emoji"])
            del result["cancelled_emoji_type"]

        # Get all channel mappings.
        response = self.table.query(
            KeyConditionExpression=(Key("guild_id").eq(guild.id) &
                                    Key("config_channel_message").begins_with("chatchannel"))
        )
        raw_channel_mappings = response["Items"]  # this is a list

        channel_mappings = {}
        for chat_channel_config in raw_channel_mappings:
            chat_channel_id = int(re.match(chat_channel_pattern,
                                           chat_channel_config["config_channel_message"]).group(1))
            chat_channel = guild.get_channel(chat_channel_id)
            relay_channel = guild.get_channel(chat_channel_config["relay_channel"])
            channel_mappings[chat_channel] = relay_channel

        result["channel_mappings"] = channel_mappings

        # Get all category mappings.
        response = self.table.query(
            KeyConditionExpression=(Key("guild_id").eq(guild.id) &
                                    Key("config_channel_message").begins_with("category"))
        )
        raw_category_mappings = response["Items"]  # this is a list

        category_mappings = {}
        for category_config in raw_category_mappings:
            category_id = int(re.match(category_pattern, category_config["config_channel_message"]).group(1))
            category = guild.get_channel(category_id)
            relay_channel = guild.get_channel(category_config["relay_channel"])
            category_mappings[category] = relay_channel

        result["category_mappings"] = category_mappings
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
        emoji_type, emoji_stored_value = emoji_to_db(fyi_emoji)
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
                "relay_to_chat": None,
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

    def activate_enhanced_fyi(self, guild: discord.Guild, rsvp_emoji, cancelled_emoji, relay_to_chat: bool):
        """
        Enable enhanced FYI functionality for the guild.

        :param guild:
        :param rsvp_emoji:
        :param cancelled_emoji:
        :param relay_to_chat:
        :return:
        """
        rsvp_emoji_type, rsvp_emoji_stored_value = emoji_to_db(rsvp_emoji)
        cancelled_emoji_type, cancelled_emoji_stored_value = emoji_to_db(cancelled_emoji)
        self.table.update_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": "config"
            },
            UpdateExpression="SET enhanced = :enhanced, "
                             "rsvp_emoji = :rsvp_emoji, "
                             "rsvp_emoji_type = :rsvp_emoji_type, "
                             "cancelled_emoji = :cancelled_emoji, "
                             "cancelled_emoji_type = :cancelled_emoji_type, "
                             "relay_to_chat = :relay_to_chat",
            ExpressionAttributeValues={
                ":enhanced": True,
                ":rsvp_emoji": rsvp_emoji_stored_value,
                ":rsvp_emoji_type": rsvp_emoji_type,
                ":cancelled_emoji": cancelled_emoji_stored_value,
                ":cancelled_emoji_type": cancelled_emoji_type,
                ":relay_to_chat": relay_to_chat
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
            UpdateExpression="SET enhanced = :enhanced, "
                             "rsvp_emoji = :rsvp_emoji, "
                             "rsvp_emoji_type = :rsvp_emoji_type, "
                             "relay_to_chat = :relay_to_chat",
            ExpressionAttributeValues={
                ":enhanced": False,
                ":rsvp_emoji": None,
                ":rsvp_emoji_type": None,
                ":relay_to_chat": None
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

    def register_fyi_category_mapping(
            self,
            guild: discord.Guild,
            category: discord.CategoryChannel,
            fyi_channel: discord.TextChannel
    ):
        """
        Register a category-to-FYI-channel mapping (e.g. for EX raid channels).

        :param guild:
        :param category:
        :param fyi_channel:
        :return:
        """
        self.table.put_item(
            Item={
                "guild_id": guild.id,
                "config_channel_message": "category{}".format(category.id),
                "relay_channel": fyi_channel.id
            }
        )

    def get_fyi_category(
            self,
            category: discord.CategoryChannel
    ):
        """
        Retrieve the information about this category's FYI mapping.

        :param category:
        :return:
        """
        guild = category.guild
        response = self.table.get_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": "category{}".format(category.id)
            }
        )
        result = response.get("Item")
        if result is None:
            return
        result["relay_channel"] = guild.get_channel(result["relay_channel"])
        return result

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

    def deregister_fyi_category_mapping(self, guild: discord.Guild, category: discord.CategoryChannel):
        """
        Deregister the specified category-to-FYI-channel mapping.

        :param guild:
        :param category:
        :return:
        """
        self.table.delete_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": "category{}".format(category.id)
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
            fyi_text,
            timestamp,
            chat_channel: discord.TextChannel,
            command_message_id,
            relay_channel: discord.TextChannel,
            relay_message_id,
            chat_relay_message_id
    ):
        """
        Create records for an FYI.

        :param guild:
        :param creator:
        :param fyi_text:
        :param timestamp: a Python datetime object showing the creation time **in UTC**
        :param chat_channel:
        :param command_message_id:
        :param relay_channel:
        :param relay_message_id:
        :param chat_relay_message_id:
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
                    "relay_message_id": relay_message_id,
                    "chat_relay_message_id": chat_relay_message_id,
                    "edit_history": [fyi_text],
                    "interested": []
                }
            )
            batch.put_item(
                Item={
                    "guild_id": guild.id,
                    "config_channel_message": channel_message_template.format(relay_channel.id, relay_message_id),
                    "chat_channel_id": chat_channel.id,
                    "command_message_id": command_message_id,
                    "relay_or_chat": "relay"
                }
            )
            if chat_relay_message_id is not None:
                batch.put_item(
                    Item={
                        "guild_id": guild.id,
                        "config_channel_message": channel_message_template.format(chat_channel.id,
                                                                                  chat_relay_message_id),
                        "chat_channel_id": chat_channel.id,
                        "command_message_id": command_message_id,
                        "relay_or_chat": "chat"
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

        These may be either the original command message or (either of) the relay message(s).

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
        if "creator_id" not in result:
            response = self.table.get_item(
                Key={
                    "guild_id": guild.id,
                    "config_channel_message": channel_message_template.format(result["chat_channel_id"],
                                                                              result["command_message_id"])
                }
            )
            result = response.get("Item")

        chat_channel = guild.get_channel(
            int(
                re.match(channel_message_pattern, result["config_channel_message"]).group(1)
            )
        )
        command_message_id = int(re.match(channel_message_pattern, result["config_channel_message"]).group(2))
        relay_channel = guild.get_channel(result["relay_channel_id"])
        relay_message_id = result["relay_message_id"]

        timestamp = dateutil.parser.parse(result["timestamp"])
        creator = guild.get_member(result["creator_id"])

        return {
            "chat_channel": chat_channel,
            "command_message_id": command_message_id,
            "relay_channel": relay_channel,
            "relay_message_id": relay_message_id,
            "chat_relay_message_id": result["chat_relay_message_id"],
            "timestamp": timestamp,
            "creator": creator,
            "edit_history": result["edit_history"],
            "interested": [guild.get_member(x) for x in result["interested"]]
        }

    def update_fyi(
            self,
            guild: discord.Guild,
            channel: discord.TextChannel,
            message_id,
            new_fyi_text,
            new_interested
    ):
        """
        Update this FYI based on the given channel and message ID.

        This message refers to the original (*not* (either of) the relay(s)).

        :param guild:
        :param channel:
        :param message_id:
        :param new_fyi_text:
        :param new_interested:
        :return:
        """
        # Retrieve the existing record to get at the edit history.
        fyi_prior_to_update = self.get_fyi(guild, channel, message_id)
        if fyi_prior_to_update is None:
            raise ValueError("Could not find an FYI to update with guild {}, channel {}, message ID {}")
        updated_edit_history = fyi_prior_to_update["edit_history"]
        if updated_edit_history[-1] != new_fyi_text:
            updated_edit_history.append(new_fyi_text)

        self.table.update_item(
            Key={
                "guild_id": guild.id,
                "config_channel_message": channel_message_template.format(channel.id, message_id)
            },
            UpdateExpression="SET edit_history = :edit_history, "
                             "interested = :interested",
            ExpressionAttributeValues={
                ":edit_history": updated_edit_history,
                ":interested": new_interested
            }
        )

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
        result = self.get_fyi(guild, channel, message_id)
        if result is None:
            raise ValueError(f"Could not find an FYI to delete with guild {guild}, "
                             f"channel {channel}, message ID {message_id}")

        # Check if this is the command or the relay.
        if "creator_id" not in result:
            result = self.get_fyi(guild, result["chat_channel"], result["command_message_id"])
            if result is None:
                raise ValueError(f"Could not find the original FYI attached to guild {guild}, "
                                 f"channel {channel}, message ID {message_id}")

        chat_channel = result["chat_channel"]
        command_message_id = result["command_message_id"]
        relay_channel = result["relay_channel"]
        relay_message_id = result["relay_message_id"]
        chat_relay_message_id = result["chat_relay_message_id"]

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
            if chat_relay_message_id is not None:
                batch.delete_item(
                    Key={
                        "guild_id": guild.id,
                        "config_channel_message": channel_message_template.format(chat_channel.id,
                                                                                  chat_relay_message_id)
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

