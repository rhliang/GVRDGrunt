create table role_reaction_subscription(
    guild_id,
    subscription_message_id primary key,
    toggle_emoji,
    toggle_emoji_type,
    role_id
);
