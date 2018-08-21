create table raid_fyi(
    guild_id primary key,
    fyi_emoji,
    fyi_emoji_type
);

create table raid_fyi_channel_mapping(
    guild_id,
    chat_channel_id primary key,
    fyi_channel_id
);
