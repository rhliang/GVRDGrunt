create table raid_rsvp_configuration(
    guild_id primary key,
    join_emoji,
    join_emoji_type
);

create table raid_rsvp(
    guild_id,
    creator_id,
    chat_channel_id,
    command_msg_id primary key,
    rsvp_channel_id,
    rsvp_msg_id
);
