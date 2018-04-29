 -- This SQL script initializes the guild info database.

create table verification_info(
    guild_id primary key,
    screenshot_channel,
    help_channel,
    denied_message,
    welcome_role,
    instinct_role,
    mystic_role,
    valor_role,
    instinct_emoji,
    instinct_emoji_type,
    mystic_emoji,
    mystic_emoji_type,
    valor_emoji,
    valor_emoji_type,
    welcome_message,
    welcome_channel
);

create table guild_standard_roles(
    role_id primary key,
    guild_id,
    mandatory
);