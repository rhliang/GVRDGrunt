 -- This SQL script initializes the guild info database.

create table role_reminder(
    guild_id primary key,
    reminder_channel_id,
    reminder_message_id,
    wait_time,
    reminded_role_id
);

create table guild_verified_role(
    role_id primary key,
    guild_id
);

create table guild_suggested_role(
    role_id primary key,
    guild_id
);