create table role_reaction_subscription(
    guild_id,
    channel_id,
    subscription_message_id primary key,
    subscribe_emoji,
    subscribe_emoji_type,
    unsubscribe_emoji,
    unsubscribe_emoji_type,
    role_id
);
