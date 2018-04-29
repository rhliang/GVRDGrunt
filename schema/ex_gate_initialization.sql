create table ex_gate(
    guild_id primary key,
    disclaimer_channel_id,
    disclaimer_message_id,
    approve_emoji,
    approve_emoji_type,
    ex_role_id,
    wait_time,
    approval_message_template
);

create table ex_gate_accepted_message(
    guild_id,
    accepted_message
);