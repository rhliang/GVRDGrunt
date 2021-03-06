import sqlite3
import discord

from bot.convert_using_guild import emoji_converter, role_converter


# create table role_reaction_subscription(
#     guild_id,
#     channel_id,
#     subscription_message_id primary key,
#     subscribe_emoji,
#     subscribe_emoji_type,
#     unsubscribe_emoji,
#     unsubscribe_emoji_type,
#     role_id
# );
class RoleReactionSubscriptionDB(object):
    """
    A class representing the SQLite database we use to store our information.
    """
    def __init__(self, path_to_db):
        self.path_to_db = path_to_db
        # The database can be initialized with role_reaction_subscription_initialization.sql
        self.conn = sqlite3.connect(self.path_to_db)

    def convert_subscription_info_to_dict(self, guild: discord.Guild, subscription_info_tuple):
        """
        Helper that converts the result from a database query into a dictionary.

        :param guild:
        :param subscription_info_tuple: a tuple containing
            (channel ID that message is in, subscription message ID,
            subscribe emoji -- either str or ID, unsubscribe emoji -- also either str or ID,
            role ID),
        :return:
        """
        if subscription_info_tuple is None:
            return None

        result = dict(
            zip(
                [
                    "channel",
                    "subscription_message_id",
                    "subscribe_emoji",
                    "unsubscribe_emoji",
                    "role",
                ],
                subscription_info_tuple
            )
        )

        # Convert the subscribe/unsubscribe emoji to the appropriate type if it's a custom emoji.
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select subscribe_emoji_type, unsubscribe_emoji_type
                from role_reaction_subscription 
                where guild_id = ?
                and subscription_message_id = ?;
                """,
                (guild.id, result["subscription_message_id"])
            )
            subscribe_emoji_type, unsubscribe_emoji_type = guild_info_cursor.fetchone()
        if subscribe_emoji_type == "custom":
            result["subscribe_emoji"] = emoji_converter(guild, result["subscribe_emoji"])
        if unsubscribe_emoji_type == "custom":
            result["unsubscribe_emoji"] = emoji_converter(guild, result["unsubscribe_emoji"])
        # Other conversions.
        result["role"] = role_converter(guild, result["role"])
        result["channel"] = guild.get_channel(result["channel"])
        return result

    def get_subscription_info(self, guild: discord.Guild, role: discord.Role):
        """
        Return some raw guild information required for the role subscription.

        :param guild:
        :param role:
        :return:
        """
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select 
                    channel_id,
                    subscription_message_id, 
                    subscribe_emoji,
                    unsubscribe_emoji, 
                    role_id
                from role_reaction_subscription 
                where guild_id = ?
                and role_id = ?;
                """,
                (guild.id, role.id)
            )
            guild_info_tuple = guild_info_cursor.fetchone()
        return self.convert_subscription_info_to_dict(guild, guild_info_tuple)

    def get_subscription_info_by_message_id(self, guild: discord.Guild, message_id):
        """
        Return some raw guild information required for the role subscription when searching by message ID.

        :param guild:
        :param message_id:
        :return:
        """
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select 
                    channel_id,
                    subscription_message_id, 
                    subscribe_emoji,
                    unsubscribe_emoji,
                    role_id
                from role_reaction_subscription 
                where guild_id = ?
                and subscription_message_id = ?;
                """,
                (guild.id, str(message_id))
            )
            guild_info_tuple = guild_info_cursor.fetchone()
        return self.convert_subscription_info_to_dict(guild, guild_info_tuple)

    def get_guild_subscription_info(self, guild: discord.Guild):
        """
        Return information on all roles for whom subscription is enabled.

        :param guild:
        :return:
        """
        subscription_info_list = []
        with self.conn:
            guild_info_cursor = self.conn.execute(
                """
                select 
                    channel_id,
                    subscription_message_id, 
                    subscribe_emoji,
                    unsubscribe_emoji, 
                    role_id
                from role_reaction_subscription 
                where guild_id = ?;
                """,
                (guild.id,)
            )
            for subscription_tuple in guild_info_cursor:
                subscription_info_list.append(self.convert_subscription_info_to_dict(guild, subscription_tuple))
        return subscription_info_list

    def configure_role_reaction_subscription(
            self,
            guild: discord.Guild,
            channel: discord.TextChannel,
            subscription_message_id,
            subscribe_emoji,
            unsubscribe_emoji,
            role: discord.Role
    ):
        """
        Configure the guild's EX gating.

        :param guild:
        :param channel:
        :param subscription_message_id:
        :param subscribe_emoji:
        :param unsubscribe_emoji:
        :param role:
        :raises:
        :return:
        """
        subscribe_emoji_type = "normal"
        subscribe_emoji_stored_value = subscribe_emoji
        if isinstance(subscribe_emoji, discord.Emoji):
            subscribe_emoji_type = "custom"
            subscribe_emoji_stored_value = subscribe_emoji.id

        unsubscribe_emoji_type = "normal"
        unsubscribe_emoji_stored_value = unsubscribe_emoji
        if isinstance(unsubscribe_emoji, discord.Emoji):
            unsubscribe_emoji_type = "custom"
            unsubscribe_emoji_stored_value = unsubscribe_emoji.id

        with self.conn:
            self.conn.execute(
                """
                insert into role_reaction_subscription 
                (
                    guild_id, 
                    channel_id,
                    subscription_message_id, 
                    subscribe_emoji, 
                    subscribe_emoji_type, 
                    unsubscribe_emoji, 
                    unsubscribe_emoji_type, 
                    role_id
                )
                values (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    guild.id,
                    channel.id,
                    subscription_message_id,
                    subscribe_emoji_stored_value,
                    subscribe_emoji_type,
                    unsubscribe_emoji_stored_value,
                    unsubscribe_emoji_type,
                    role.id
                )
            )

    def remove_subscription_data(self, guild: discord.Guild, role: discord.Role):
        """
        Remove the specified guild and role's subscription configuration from the database.

        :param guild:
        :param role:
        :return:
        """
        with self.conn:
            self.conn.execute(
                "delete from role_reaction_subscription where guild_id = ? and role_id = ?;",
                (guild.id, role.id)
            )
