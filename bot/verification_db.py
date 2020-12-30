import discord
import boto3

from bot.convert_using_guild import role_converter, emoji_converter
from bot.utils import emoji_to_db


class VerificationDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    SCREENSHOT_FIELDS_NEEDED = (
        "screenshot_channel",
        "help_channel",
        "denied_message",
        "welcome_role",
        "instinct_emoji",
        "instinct_emoji_type",
        "mystic_emoji",
        "mystic_emoji_type",
        "valor_emoji",
        "valor_emoji_type"
    )

    ALL_FIELDS = (
        ("screenshot_channel", "channel"),
        ("help_channel", "channel"),
        ("denied_message", "string"),
        ("welcome_role", "role"),
        ("instinct_role", "role"),
        ("mystic_role", "role"),
        ("valor_role", "role"),
        ("instinct_emoji", "emoji_or_string"),
        ("mystic_emoji", "emoji_or_string"),
        ("valor_emoji", "emoji_or_string"),
        ("welcome_message", "string"),
        ("welcome_channel", "channel")
    )

    TEAMS = ("instinct", "mystic", "valor")

    def __init__(self, table_name="GuildVerification", *args, **kwargs):
        # The database can be initialized with verification_initialization.json.
        self.db = boto3.resource("dynamodb", *args, **kwargs)
        self.table = self.db.Table(table_name)

    def get_verification_info(self, guild):
        """
        Return the dictionary of information corresponding to the specified guild.

        :param guild:
        :return:
        """
        response = self.table.get_item(Key={"guild_id": guild.id})
        result = response.get("Item")
        if result is None:
            return

        final_results = {}
        for field_name, field_type in self.ALL_FIELDS:
            raw_field = result[field_name]
            converted_result = raw_field
            if raw_field is not None:
                if field_type == "channel":
                    converted_result = guild.get_channel(raw_field)
                elif field_type == "role":
                    converted_result = role_converter(guild, raw_field)
                elif field_type == "emoji_or_string":
                    # This is a team emoji; extract the team from the field name.
                    team = field_name.split("_")[0]
                    if result[f"{team}_emoji_type"] == "custom":
                        converted_result = emoji_converter(guild, raw_field)
            final_results[field_name] = converted_result

        final_results["standard_roles"] = [role_converter(guild, role_id) for role_id in result["standard_roles"]]
        final_results["mandatory_roles"] = [role_converter(guild, role_id) for role_id in result["mandatory_roles"]]

        return final_results

    def register_guild(self, guild):
        """
        Create a new, empty record for the guild.

        :param guild:
        :return:
        """
        blank_record = dict(zip([field_name for field_name, _ in self.ALL_FIELDS], [None for _, _ in self.ALL_FIELDS]))
        blank_record["guild_id"] = guild.id
        for team in self.TEAMS:
            blank_record[f"{team}_emoji_type"] = None
        self.table.put_item(Item=blank_record, ConditionExpression="attribute_not_exists(guild_id)")

    def set_channel(self, guild, channel: discord.TextChannel, type):
        """
        Set the screenshot or help channel for the guild.

        :param guild:
        :param channel:
        :param type: one of "screenshot", or "help"
        :return:
        """
        if type not in ("screenshot", "help"):
            raise discord.InvalidArgument('channel type must be one of "screenshot", or "help"')
        self.table.update_item(
            Key={"guild_id": guild.id},
            UpdateExpression=f"SET {type}_channel = :channel",
            ExpressionAttributeValues={":channel": channel.id}
        )

    def set_denied_message(self, guild, denied_message):
        """
        Set the message sent when requesting a new screenshot.

        :param guild:
        :param denied_message:
        :return:
        """
        self.table.update_item(
            Key={"guild_id": guild.id},
            UpdateExpression="SET denied_message = :denied_message",
            ExpressionAttributeValues={":denied_message": denied_message}
        )

    def set_welcome_role(self, guild, welcome_role: discord.Role):
        """
        Set the guild's welcome role.

        :param guild:
        :param welcome_role:
        :return:
        """
        self.table.update_item(
            Key={"guild_id": guild.id},
            UpdateExpression="SET welcome_role = :welcome_role_id",
            ExpressionAttributeValues={":welcome_role_id": welcome_role.id}
        )

    def team_name_validator(self, team):
        """
        Raises discord.InvalidArgument if team is not one of "instinct", "mystic", or "valor", case-insensitive.

        :param team:
        :return:
        """
        if team.lower() not in self.TEAMS:
            raise discord.InvalidArgument('team must be one of "instinct", "mystic", or "valor" (case-insensitive)')

    def set_team_role(self, guild, team, role: discord.Role):
        """
        Set the guild's team role.

        :param guild:
        :param team:
        :param role:
        :return:
        """
        self.team_name_validator(team)
        self.table.update_item(
            Key={"guild_id": guild.id},
            UpdateExpression=f"SET {team.lower()}_role = :team_role_id",
            ExpressionAttributeValues={":team_role_id": role.id}
        )

    def set_team_emoji(self, guild, team, emoji):
        """
        Set the guild's team emoji (i.e. that will be used as reactions on verification screenshots).

        :param guild:
        :param team:
        :param emoji: either a string (i.e. a normal emoji) or a discord.Emoji object
        :return:
        """
        self.team_name_validator(team)
        emoji_type, emoji_stored_value = emoji_to_db(emoji)
        self.table.update_item(
            Key={"guild_id": guild.id},
            UpdateExpression=f"SET {team.lower()}_emoji = :team_emoji_stored_value, "
                             f"{team.lower()}_emoji_type = :team_emoji_type",
            ExpressionAttributeValues={
                ":team_emoji_stored_value": emoji_stored_value,
                ":team_emoji_type": emoji_type
            }
        )

    def set_welcome(self, guild, welcome_message, welcome_channel: discord.TextChannel):
        """
        Set the guild's welcome message and welcome channel.

        :param guild:
        :param welcome_message:
        :param welcome_channel:
        :return:
        """
        self.table.update_item(
            Key={"guild_id": guild.id},
            UpdateExpression="SET welcome_message = :welcome_message, "
                             "welcome_channel = :welcome_channel_id",
            ExpressionAttributeValues={
                ":welcome_message": welcome_message,
                ":welcome_channel_id": welcome_channel.id
            }
        )

    def add_standard_role(self, guild, role: discord.Role, mandatory: bool):
        """
        Add a guild role to the list of standard roles given to a user on verification.

        If mandatory is True, it's marked as a mandatory verification role.

        Assume that the guild has an existing record in the database.

        :param guild:
        :param role:
        :param mandatory:
        :return:
        """
        existing_info = self.get_verification_info(guild)
        if not mandatory:
            if role in existing_info["standard_roles"]:
                raise ValueError("Role is already in this guild's standard roles")
            new_standard_roles = existing_info["standard_roles"] + [role]
            new_mandatory_roles = existing_info["mandatory_roles"]

        else:
            if role in existing_info["mandatory_roles"]:
                raise ValueError("Role is already in this guild's mandatory roles")
            # Remove this from the standard roles if it's there, and add it to the mandatory roles.
            new_standard_roles = [x for x in existing_info["standard_roles"] if x.id != role.id]
            new_mandatory_roles = existing_info["mandatory_roles"] + [role]

        self.table.update_item(
            Key={"guild_id": guild.id},
            UpdateExpression="SET standard_roles = :new_standard_role_ids, "
                             "mandatory_roles = :new_mandatory_role_ids",
            ExpressionAttributeValues={
                ":new_standard_role_ids": [x.id for x in new_standard_roles],
                ":new_mandatory_role_ids": [x.id for x in new_mandatory_roles]
            }
        )

    def clear_roles(self, guild):
        """
        Remove all guild roles from the database -- e.g. if a mistake was made entering them.

        :param guild:
        :return:
        """
        self.table.update_item(
            Key={"guild_id": guild.id},
            UpdateExpression="SET standard_roles = :standard_roles, mandatory_roles = :mandatory_roles",
            ExpressionAttributeValues={
                ":standard_roles": [],
                ":mandatory_roles": []
            }
        )
