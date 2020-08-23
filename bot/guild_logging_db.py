import discord
import boto3


class GuildLoggingDB(object):
    """
    Handles persistent storage of guild logging information.
    """
    def __init__(self, table_name="GuildLogging", *args, **kwargs):
        # The database can be initialized with guild_logging.json.
        self.db = boto3.resource("dynamodb", *args, **kwargs)
        self.table = self.db.Table(table_name)

    def get_logging_info(self, guild: discord.Guild):
        """
        Return the guild's logging information.

        :param guild:
        :return:
        """
        response = self.table.get_item(Key={"guild_id": guild.id})
        result = response.get("Item")
        if result is None:
            return
        result["log_channel"] = guild.get_channel(result["log_channel"])
        return result

    def configure_guild_logging(self, guild: discord.Guild, log_channel: discord.TextChannel):
        """
        Configure the guild's logging channel.

        :param guild:
        :param log_channel:
        :raises:
        :return:
        """
        self.table.put_item(
            Item={
                "guild_id": guild.id,
                "log_channel": log_channel.id
            }
        )

    def clear_guild_logging(self, guild: discord.Guild):
        """
        Remove this guild's logging information from the database.

        :param guild:
        :return:
        """
        self.table.delete_item(Key={"guild_id": guild.id})
