begin transaction;

alter table role_reaction_subscription rename to role_reaction_subscription_old;

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

insert into role_reaction_subscription(
    guild_id,
    channel_id,
    subscription_message_id,
    subscribe_emoji,
    subscribe_emoji_type,
    unsubscribe_emoji,
    unsubscribe_emoji_type,
    role_id
) select
    guild_id,
    channel_id,
    subscription_message_id,
    toggle_emoji,
    toggle_emoji_type,
    "❎",
    "normal",
    role_id
from role_reaction_subscription_old;

drop table role_reaction_subscription_old;

commit;
