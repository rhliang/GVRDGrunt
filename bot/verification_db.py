import sqlite3
import discord

from bot.convert_using_guild import role_converter, emoji_converter


class GuildInfoDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    screenshot_fields_needed = (
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

    all_fields = (
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

    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        self.conn = sqlite3.connect(self.path_to_db)  # database can be initialized with verification_initialization.sql

    def get_verification_info(self, guild):
        """
        Return the dictionary of information corresponding to the specified guild.

        :param guild:
        :return:
        """
        with self.conn:
            query = f"""\
            select {", ".join([x[0] for x in self.all_fields])}
            from verification_info 
            where guild_id = ?;
            """,
            (guild.id,)
            verification_info_cursor = self.conn.execute(
                f"""\
                select {", ".join([x[0] for x in self.all_fields])}
                from verification_info 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            verification_info_tuple = verification_info_cursor.fetchone()
        if verification_info_tuple is None:
            return None

        with self.conn:
            verification_info_cursor = self.conn.execute(
                f"""\
                select instinct_emoji_type, mystic_emoji_type, valor_emoji_type
                from verification_info 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            emoji_tuple = verification_info_cursor.fetchone()
        team_emoji_types = dict(zip(("instinct", "mystic", "valor"), emoji_tuple))

        standard_roles = []
        mandatory_roles = []
        with self.conn:
            guild_roles_cursor = self.conn.execute(
                """
                select role_id, mandatory
                from guild_standard_roles
                where guild_id = ?;
                """,
                (guild.id,)
            )
            for role_id, mandatory in guild_roles_cursor:
                role = role_converter(guild, role_id)
                if mandatory:
                    mandatory_roles.append(role)
                else:
                    standard_roles.append(role)

        converted_results = []
        for i, (field_name, field_type) in enumerate(self.all_fields):
            converted_result = verification_info_tuple[i]
            if converted_result is not None:
                if field_type == "channel":
                    converted_result = guild.get_channel(verification_info_tuple[i])
                elif field_type == "role":
                    converted_result = role_converter(guild, verification_info_tuple[i])
                elif field_type == "emoji_or_string":
                    # This is a team emoji; extract the team from the field name.
                    team = field_name.split("_")[0]
                    if team_emoji_types[team] == "custom":
                        converted_result = emoji_converter(guild, verification_info_tuple[i])
            converted_results.append(converted_result)

        final_results = dict(
            zip(
                [field_name for field_name, _ in self.all_fields],
                converted_results
            )
        )
        final_results["standard_roles"] = standard_roles
        final_results["mandatory_roles"] = mandatory_roles
        return final_results

    def register_guild(self, guild):
        """
        Create a new, empty record for the guild.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into verification_info (guild_id) values(?);
                """,
                (guild.id,)
            )

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
        with self.conn:
            self.conn.execute(
                f"""
                update verification_info
                set {type}_channel = ?
                where guild_id = ?;
                """,
                (
                    channel.id,
                    guild.id
                )
            )

    def set_denied_message(self, guild, denied_message):
        """
        Set the message sent when requesting a new screenshot.

        :param guild:
        :param denied_message:
        :return:
        """
        with self.conn:
            self.conn.execute(
                f"""
                update verification_info
                set denied_message = ?
                where guild_id = ?;
                """,
                (
                    denied_message,
                    guild.id
                )
            )

    def set_welcome_role(self, guild, welcome_role: discord.Role):
        """
        Set the guild's welcome role.

        :param guild:
        :param welcome_role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                update verification_info
                set welcome_role = ?
                where guild_id = ?;
                """,
                (
                    welcome_role.id,
                    guild.id
                )
            )

    def team_name_validator(self, team):
        """
        Raises discord.InvalidArgument if team is not one of "instinct", "mystic", or "valor", case-insensitive.

        :param team:
        :return:
        """
        if team.lower() not in ("instinct", "mystic", "valor"):
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
        with self.conn:
            self.conn.execute(
                f"""
                update verification_info
                set {team.lower()}_role = ?
                where guild_id = ?;
                """,
                (
                    role.id,
                    guild.id
                )
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
        emoji_type = "normal"
        emoji_stored_value = emoji
        if isinstance(emoji, discord.Emoji):
            emoji_type = "custom"
            emoji_stored_value = emoji.id
        with self.conn:
            self.conn.execute(
                f"""
                update verification_info
                set {team.lower()}_emoji = ?,
                {team.lower()}_emoji_type = ?
                where guild_id = ?;
                """,
                (
                    emoji_stored_value,
                    emoji_type,
                    guild.id
                )
            )

    def set_welcome(self, guild, welcome_message, welcome_channel: discord.TextChannel):
        """
        Set the guild's welcome message and welcome channel.

        :param guild:
        :param welcome_message:
        :param welcome_channel:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                update verification_info
                set welcome_message = ?,
                welcome_channel = ?
                where guild_id = ?;
                """,
                (
                    welcome_message,
                    welcome_channel.id,
                    guild.id
                )
            )

    def add_standard_role(self, guild, role: discord.Role, mandatory: bool):
        """
        Add a guild role to the list of standard roles given to a user on verification.

        If mandatory is True, it's marked as a mandatory verification role.

        :param guild:
        :param role:
        :param mandatory:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                insert into guild_standard_roles (guild_id, role_id, mandatory) values(?, ?, ?);
                """,
                (
                    guild.id,
                    role.id,
                    mandatory
                )
            )

    def clear_roles(self, guild):
        """
        Remove all guild roles from the database -- e.g. if a mistake was made entering them.

        :param guild:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from guild_standard_roles where guild_id = ?;",
                (guild.id,)
            )
