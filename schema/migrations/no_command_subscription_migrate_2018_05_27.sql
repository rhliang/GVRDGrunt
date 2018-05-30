begin transaction;

alter table no_command_subscription
    add show_subscriptions_emoji;

alter table no_command_subscription
    add show_subscriptions_emoji_type;

update no_command_subscription
set show_subscriptions_emoji = '📜',
    show_subscriptions_emoji_type = 'normal';

commit;
