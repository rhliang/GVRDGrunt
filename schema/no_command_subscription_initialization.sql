create table no_command_subscription(
    guild_id primary key,
    subscription_channel_id,
    instruction_message_text,
    instruction_message_id,
    wait_time
);

create table no_command_role(
    guild_id,
    role_id primary key
);

create table no_command_role_channel(
    guild_id,
    role_id,
    channel_id,
    primary key (role_id, channel_id)
);
