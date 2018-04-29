begin transaction;

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

insert into verification_info
    (
        guild_id,
        screenshot_channel,
        help_channel,
        denied_message,
        welcome_role,
        instinct_role,
        mystic_role,
        valor_role,
        welcome_message,
        welcome_channel
    )
select
    guild_id,
    screenshot_channel,
    help_channel,
    denied_message,
    welcome_role,
    instinct_role,
    mystic_role,
    valor_role,
    welcome_message,
    welcome_channel
from guild_info;

drop table guild_info;

commit;