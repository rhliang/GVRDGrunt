import sqlite3
import discord

from bot.convert_using_guild import role_converter, emoji_converter


# create table no_command_subscription(
#     guild_id primary key,
#     subscription_channel_id,
#     instruction_message_text,
#     instruction_message_id,
#     wait_time,
#     show_subscriptions_emoji,
#     show_subscriptions_emoji_type,
# );
class NoCommandSubscriptionDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        # This database can be initialized with no_command_subscription_initialization.sql.
        self.conn = sqlite3.connect(self.path_to_db)

    def activate_no_command_subscription(self, guild: discord.Guild, subscription_channel: discord.TextChannel,
                                         instruction_message_text, instruction_message_id, wait_time: float,
                                         show_subscriptions_emoji):
        """
        Register this guild in the database.

        :param guild:
        :param subscription_channel:
        :param instruction_message_text:
        :param instruction_message_id:
        :param wait_time:
        :param show_subscriptions_emoji:
        :return:
        """
        emoji_type = "normal"
        emoji_stored_value = show_subscriptions_emoji
        if isinstance(show_subscriptions_emoji, discord.Emoji):
            emoji_type = "custom"
            emoji_stored_value = show_subscriptions_emoji.id

        with self.conn:
            self.conn.execute(
                """
                insert into no_command_subscription (
                    guild_id, 
                    subscription_channel_id, 
                    instruction_message_text,
                    instruction_message_id,
                    wait_time,
                    show_subscriptions_emoji,
                    show_subscriptions_emoji_type
                )
                values (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    guild.id,
                    subscription_channel.id,
                    instruction_message_text,
                    instruction_message_id,
                    wait_time,
                    emoji_stored_value,
                    emoji_type
                )
            )

    def disable_no_command_subscription(self, guild: discord.Guild):
        """
        Disable no-command subscription for this guild by removing its data from the database.

        Note that you will have to deregister the roles separately.

        :param guild:
        :return:
        """
        # self.deregister_all_roles(guild)
        with self.conn:
            self.conn.execute(
                "delete from no_command_subscription where guild_id = ?;",
                (guild.id,)
            )

    def change_instruction_message(self, guild: discord.Guild, new_instruction_message_text: str):
        """
        Change the stored instruction message text.

        :param guild:
        :param new_instruction_message_text:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                update no_command_subscription
                set instruction_message_text = ?
                where guild_id = ?;
                """,
                (new_instruction_message_text, guild.id)
            )

    def change_wait_time(self, guild: discord.Guild, new_wait_time: float):
        """
        Change the guild's wait time before deleting messages in the subscription channel.

        :param guild:
        :param new_wait_time:
        :return:
        """
        with self.conn:
            self.conn.execute(
                """
                update no_command_subscription
                set wait_time = ?
                where guild_id = ?;
                """,
                (new_wait_time, guild.id)
            )

    def change_show_subscriptions_emoji(self, guild: discord.Guild, new_show_subscriptions_emoji):
        """
        Change the show-subscriptions emoji.

        :param guild:
        :param new_show_subscriptions_emoji:
        :return:
        """
        emoji_type = "normal"
        emoji_stored_value = new_show_subscriptions_emoji
        if isinstance(new_show_subscriptions_emoji, discord.Emoji):
            emoji_type = "custom"
            emoji_stored_value = new_show_subscriptions_emoji.id

        with self.conn:
            self.conn.execute(
                """
                update no_command_subscription
                set show_subscriptions_emoji = ?, show_subscriptions_emoji_type = ?
                where guild_id = ?;
                """,
                (emoji_stored_value, emoji_type, guild.id)
            )

    def register_roles(self, guild: discord.Guild, roles_to_register):
        """
        Register the specified roles for no-command subscription.

        If any roles in the file are already registered, just ignore them.

        :param guild:
        :param roles_to_register: list of Discord roles
        :return:
        """
        with self.conn:
            for role in roles_to_register:
                self.conn.execute(
                    "insert or ignore into no_command_role (guild_id, role_id) values (?, ?)",
                    (guild.id, role.id)
                )

    def register_role(self, guild: discord.Guild, role: discord.Role, channel_list):
        """
        Register the specified role and the channels associated with it.

        :param guild:
        :param role:
        :param channel_list:
        :return:
        """
        with self.conn:
            for channel in channel_list:
                self.conn.execute(
                    "insert or ignore into no_command_role_channel (guild_id, role_id, channel_id) values (?, ?, ?)",
                    (guild.id, role.id, channel.id)
                )
        self.register_roles(guild, [role])

    def deregister_role(self, guild: discord.Guild, role: discord.Role):
        """
        Deregister the specified role and clear up the channels associated with it.

        :param role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from no_command_role_channel where guild_id = ? and role_id = ?",
                (guild.id, role.id)
            )
            self.conn.execute(
                "delete from no_command_role where guild_id = ? and role_id = ?",
                (guild.id, role.id)
            )

    def deregister_all_roles(self, guild: discord.Guild):
        """
        Deregister all roles.

        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from no_command_role_channel where guild_id = ?",
                (guild.id,)
            )
            self.conn.execute(
                "delete from no_command_role where guild_id = ?",
                (guild.id,)
            )

    def get_no_command_subscription_settings(self, guild: discord.Guild):
        """
        Return a dictionary with all no-command subscription settings for this guild.

        The dictionary will contain keys:
         - subscription_channel
         - instruction_message
         - wait_time
         - show_subscriptions_emoji
         - roles: a dictionary keyed by role IDs, with values being lists of associated channels (or [])

        :return:
        """
        with self.conn:
            sub_cursor = self.conn.execute(
                """
                select 
                    subscription_channel_id,
                    instruction_message_id,
                    instruction_message_text,
                    wait_time,
                    show_subscriptions_emoji
                from no_command_subscription
                where guild_id = ?;
                """,
                (guild.id,)
            )
            sub_tuple = sub_cursor.fetchone()
        if sub_tuple is None:
            return None

        result = dict(
            zip(
                [
                    "subscription_channel",
                    "instruction_message_id",
                    "instruction_message_text",
                    "wait_time",
                    "show_subscriptions_emoji"
                ],
                sub_tuple
            )
        )
        result["subscription_channel"] = guild.get_channel(result["subscription_channel"])

        # Convert the show-subscriptions emoji to the appropriate type if it's a custom emoji.
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select show_subscriptions_emoji_type
                from no_command_subscription 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            show_subscriptions_emoji_type = guild_info_cursor.fetchone()[0]
        if show_subscriptions_emoji_type == "custom":
            result["show_subscriptions_emoji"] = emoji_converter(guild, result["show_subscriptions_emoji"])

        # Now retrieve the roles that are registered for no-command subscription.
        result["roles"] = {}
        with self.conn:
            sub_cursor = self.conn.execute(
                "select role_id from no_command_role where guild_id = ?;",
                (guild.id,)
            )
            for role_tuple in sub_cursor:
                role = role_converter(guild, role_tuple[0])
                result["roles"][role] = []

            sub_cursor = self.conn.execute(
                "select role_id, channel_id from no_command_role_channel where guild_id = ?;",
                (guild.id,)
            )
            for role_channel_tuple in sub_cursor:
                role = role_converter(guild, role_channel_tuple[0])
                if role in result["roles"]:
                    channel = guild.get_channel(role_channel_tuple[1])
                    result["roles"][role].append(channel)

        return result
