 -- This SQL script initializes the guild info database.

create table guild_info(
    guild_id primary key,
    log_channel,
    screenshot_channel,
    help_channel,
    denied_message,
    welcome_role,
    instinct_role,
    mystic_role,
    valor_role,
    welcome_message,
    welcome_channel
);

create table guild_standard_roles(
    role_id primary key,
    guild_id,
    mandatory
);