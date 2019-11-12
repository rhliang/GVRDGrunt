import boto3
import discord

# The schema of the database:
# (guild[guild id]):
# - can_configure_bot (a set of role IDs)


class GuildPermsNotConfigured(Exception):
    pass


class RoleAlreadyHasPermissions(Exception):
    pass


class RoleDoesNotHavePermissions(Exception):
    pass


class BotPermsDB(object):
    """
    A class representing the database we use to store our information.
    """
    def __init__(self, *args, **kwargs):
        # The database can be initialized with raid_fyi_initialization.json
        self.db = boto3.resource("dynamodb", *args, **kwargs)
        self.table = self.db.Table("BotPerms")

    def get_bot_perms(self, guild: discord.Guild):
        """
        Return this guild's bot permission configuration.

        :param guild:
        :return:
        """
        # Get the base guild configuration.
        response = self.table.get_item(
            Key={
                "guild_id": guild.id
            }
        )
        result = response.get("Item")
        if result is None:
            raise GuildPermsNotConfigured("No configuration was found for this guild.")

        result["can_configure_bot"] = [guild.get_role(x) for x in result["can_configure_bot"]]
        return result

    def add_bot_permissions_to_role(self, guild: discord.Guild, role: discord.Role):
        """
        Add the specified role to the list of roles that can run bot configuration commands.

        :param guild:
        :param role:
        :return:
        """
        result = self.get_bot_perms(guild)
        if result is None:  # initialize the database with this guild's information
            self.table.put_item(
                Item={
                    "guild_id": guild.id,
                    "can_configure_bot": [role.id]
                }
            )

        elif role.id in result["can_configure_bot"]:  # do nothing
            raise RoleAlreadyHasPermissions("This role already has bot permissions in this guild.")

        else:
            self.table.update_item(
                Key={
                    "guild_id": guild.id
                },
                UpdateExpression="SET can_configure_bot = :can_configure_bot",
                ExpressionAttributeValues={
                    ":can_configure_bot": [x.id for x in result["can_configure_bot"]] + [role.id]
                }
            )

    def remove_bot_permissions_from_role(self, guild: discord.Guild, role: discord.Role):
        """
        Remove the specified role from the list of roles that can run bot configuration commands.

        :param guild:
        :param role:
        :return:
        """
        result = self.get_bot_perms(guild)
        if result is None:  # do nothing
            raise GuildPermsNotConfigured("No configuration was found for this guild.")

        elif role.id not in result["can_configure_bot"]:  # do nothing
            raise RoleDoesNotHavePermissions("This role does not have bot permissions in this guild.")

        else:
            self.table.update_item(
                Key={
                    "guild_id": guild.id
                },
                UpdateExpression="SET can_configure_bot = :can_configure_bot",
                ExpressionAttributeValues={
                    ":can_configure_bot": [x.id for x in result["can_configure_bot"] if x != role.id]
                }
            )

    def reset_bot_permissions(self, guild: discord.Guild):
        """
        Clear all bot permissions from roles.

        :param guild:
        :return:
        """
        self.table.delete_item(
            Key={
                "guild_id": guild.id
            }
        )
