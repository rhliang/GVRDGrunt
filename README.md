GVRDGrunt
=========

GVRDGrunt is a simple bot that performs boilerplate admin tasks for Vancouver/GVRD moderators.

Installation
------------

* Install Python 3.6 or later
    * On OS X, you may need to do the following https://github.com/Rapptz/discord.py/issues/423#issuecomment-272093801
* Set up a Virtualenv if you're using this in production
* `python -m pip install -r requirements.txt`
* Copy `gvrd_grunt_config_example.json` to `gvrd_grunt_config.json` and fill it out
* Initialize the guild information DB using the SQL in `schema` and put it at the location specified in the config file
* `python -m bot`
    * `--debug` for debug-level logging
    * `--config [JSON config file]` to use a different config file than `./gvrd_grunt_config.json`

In the configuration file, you must set the following:

* `token`: the bot's Discord token
* `sqlite_db`: absolute path to the SQLite database file
* `command_prefix`: the bot will only recognize messages that start with this prefix as commands (for GVRD we use ".")
* `log_file`: absolute path to the log file

The preferred deployment method for GVRDGrunt is via Docker.  The provided Dockerfile is configured to
look for the JSON configuration file inside the container at `/config/gvrd_grunt_config.json`, so make sure 
that file is accessible within the Docker container at that path.  In the config file, the paths
you set for the SQLite database and the log file will be *as they appear in the container*; you will probably 
want to use either a bind mount or a volume for those, so make sure you mount them at the correct places in 
your container.

If you're deploying the main GVRD bot
-------------------------------------

This isn't a public bot -- it's only meant to be for the GVRD guilds -- so you'll need me to be
in your guild, and for me to have Manage Server perms.  Contact me -- @Solderfumes#9910 on Discord.

Also note that if you're deploying the main GVRD bot, the command prefix is `.`, so any of the commands
described below must be prefaced with that.

GVRDGrunt provides the following services to guilds that it's deployed on.

Verification
------------

GVRDGrunt helps to automate the verification procedure used by the GVRD guilds.  Verification with the bot 
proceeds as follows (here I'll use the role names and channel names used in the Vancouver Raids guild for 
demonstration, but much of this is configurable).  First, when a screenshot from a member in the `Welcome` 
role is submitted to the `#verification` channel, the bot will add four reactions: one for each team, and 
one ❌.  The moderator now has four options:

* If no nick changes are required, a moderator can simply click on one of the three team reactions
to verify the user; if this happens, the user gets the `Welcome` role removed, a team role assigned, and whatever
standard verification roles the guild defines are also applied to the user.  The user is then pinged with a 
welcome message in `#chitchat`.
* The moderator may also use the `verify` command (or simply `v`) to accomplish the same task: 
    ```
    verify [user to verify] [team]
    ```
    
    If other roles are to be assigned on verification, they can be listed after those parameters:
    ```
    verify [user] [team] [role 1] [role 2] ... [role N]
    ```
* If a nick change is required, the moderator may use the `nickverify` command (or `n`, or `nv`):
    ```
    nickverify [user to verify] [PoGo IGN] [team]
    ```

    and optional roles can be specified in the same way.
* If the screenshot can't be verified for any reason, the moderator can click on the ❌ reaction.
The user will be pinged in the `#help` channel with a message explaining what happened.
    
The things that need to be set on deployment, and their placeholders in the above example, are:

* screenshot channel (`#verification`)
* help channel (`#help`)
* the Welcome role (`Welcome`)
* the welcome channel (`#chitchat`)
* the welcome message
* the denied message
* the roles your guild uses for the teams
* emoji that will be attached to the screenshots -- one for each team

### Configuring verification

GVRDGrunt must be configured for the guild before this can happen.  These commands must be run by someone with
`Administrator` privileges on the guild, except for `showsettings`.  Remember that the bot must have appropriate 
permissions on the channels it reads from/writes to!  Also, the bot needs `Manage Roles` and `Manage Nickname`,
and whatever role you create for it has to be higher than your guild's welcome and team roles on the guild
role hierarchy.

#### Required configuration

##### `register_guild`
This registers the guild with the bot's database and must be run before any other configuration can occur.

##### `showsettings`
Shows all of the configuration data.  You can use this at any time after the guild is registered to guide
you in your setup, or to check on your configuration.  This may be run by a user with `Manage Roles`.

##### `configure_channel [screenshot|help] [channel]`
This instructs the bot what channel to look for Welcome member screenshots in, and what channel to ping 
users in when their screenshot is rejected.  The bot must have read, write, `Add Reactions`, and `Manage Messages`
permissions on the screenshot channel, and read and write perms on help.

##### `configure_welcome_role [role]`
Tells the bot what the guild's Welcome role is.

##### `configure_team_emoji [instinct|mystic|valor] [emoji]`
These are the emoji that the bot will attach to screenshots for one-click verification.

##### `configure_team_role [instinct|mystic|valor] [role]`
The roles the guild uses for Instinct/Mystic/Valor.

##### `configure_guild_welcome [channel] [welcome message template incl "{}" where the member will be mentioned]`
Configures the channel that the guild sends the welcome message in, as well as the message that is sent.  
Presumably this message is more than one word, so it should go in quotes!  Also, this message
should contain a single `{}` where the new member will be mentioned.  The bot must have read and write
privileges on the welcome channel.

##### `configure_denied_message [denied message template incl "{}" where the member will be mentioned]`
Configures the message that will be sent to the user when their screenshot is rejected.  Like the welcome message,
this message should be in quotes if it's more than one word (how could it not be??) and should contain a 
single `{}` where the new member will be mentioned.

#### Optional configuration

The guild may also specify roles that will be assigned to users by default on verification, and roles that *must* 
be assigned on verification.  Configure them with these commands.

##### `add_mandatory_role [role]`
This role must be added to every new user regardless of what roles are specified during verification, e.g. 
the `ex-readme` role.

##### `add_standard_role [role]`
This role will be added to any new member unless roles are specified in the `verify` or `nickverify` commands, 
e.g. region roles.

##### `clear_roles`
Removes all standard and mandatory roles.

#### Verification

##### `verify [member to verify] [team] [role 1] ... [role N]`
Verify the member, assign them to a team, and assign them to the specified roles.  If no roles
are specified, the user will be assigned all standard roles and all mandatory roles.  If roles *are* specified,
the user will be assigned only to the specified roles and all mandatory roles.

The team should be specified as one of `instinct|mystic|valor|i|m|v|yellow|blue|red|y|b|r`.

You may also use `v` as a short form.

This command requires `Manage Roles` permissions.

##### `nickverify [member] [PoGo IGN] [team] [role 1] ... [role N]` 
Similar to `verify` except also sets the guild nick.  You may also use `n`, `nv` or `nickv` as a short form.

This command requires `Manage Roles` and `Manage Nicknames` permissions.

##### `reset [member]`
Clear the member's nick and remove all roles, and re-assign the welcome role.  This requires `Manage Roles`
and `Manage Nicknames`.

Logging
-------

This is optional, but enables the bot to send log messages to a channel in your guild.  If you do not configure
it, nothing will be affected but no such logging will occur.

### Configuring logging

##### `configure_log_channel [channel]`
Instructs the bot to log to the specified channel.  The bot must have read and write permissions on this channel.
The caller must have `Administrator` privileges.

##### `disable_logging`
Clears the guild's logging information from the database; logging will stop.  The caller must have `Administrator`
privileges.

##### `show_logging`
Show the guild's logging information.  The caller must have `Manage Roles` and `Manage Nicknames` permissions.

EX Gating
---------

This sounds fancy, but the functionality is pretty simple: when a user adds a reaction to a specified message,
they get assigned to a specified EX role.  They may also type a message in the channel and it will add them to the
role (and then autodelete the messages).  In either case, the bot will ping the user in that channel with an
affirmative message (or a message saying it didn't understand the user's message), and then delete it after a
specified wait time.

### Configuration

Configuration requires administrator privileges.

##### `activate_ex_gating [channel] [message ID] [emoji] [EX role] [wait time] [approval message template]`
Configures the EX gating to watch the specified channel, and the specified message in that channel.  
The bot will monitor for the specified emoji being added/removed from the message, and/or an accepted
message such as "yes", "y", or "mewtwo".  When this happens, the EX role will be applied to the user who
clicked the reaction/sent the message.

If it was via a message, the bot will reply to the user with an approval message (which should also contain a single
`{}` like the messages sent by the verification functionality).  After waiting for the specified amount of time,
the user's message and the bot's reply will both be deleted.

##### `show_ex_gating`
Shows the EX gating configuration.  (This only requires `Manage Roles` and `Manage Nicknames`.)

##### `add_ex_accepted_message [message]`
Adds a message to the list of things that the bot understands as an affirmative re: assigning the user the EX role.
That is, you teach the bot to understand, say, "yes", "y", and "mewtwo".  If the user types one of these things
in the EX gating channel, the bot will then grant the user the role.  If the user types something else,
the bot will reply that it only understands the messages that you taught it.

##### `disable_ex_gating`
Disable the EX gating for this guild.

Role Reaction Subscription
--------------------------

This is based on the EX gating but simplified.  The bot watches certain messages for certain reactions (either
added or removed), and assigns/removes a specified role from the reacting user.

### Configuration

This requires `Administrator` privileges except where otherwise specified.

##### `activate_role_reaction_subscription [role] [channel] [message ID] [subscribe emoji] [unsubscribe emoji]`
Instructs the bot to watch the specified message (in the specified channel) for the adding/removing of the specified
emojis as a reaction; assign/remove the specified role from the reacting member.

You may also use `start_react_sub` as a short form.

##### `show_role_reaction_subscription [role]`
Display the configuration for the specified role.  Requires only `Manage Roles` and `Manage Nicknames`.

##### `show_all_role_reaction_subscriptions`
Display the configuration for all roles for which reaction-based subscription is enabled.  Requires only 
`Manage Roles` and `Manage Nicknames`.

You may also use `show_react_sub` as a short form.

##### `disable_role_reaction_subscription [role]`
Disable reaction-based role subscription for the specified role.

You may also use `stop_react_sub` as a short form.

No-Command Role Subscription
----------------------------

This feature allows the bot to monitor a designated channel for member messages.  The member only has to type the name 
of the role that they wish to subscribe to, and the bot will subscribe/unsubscribe the member from the role.
This is case-insensitive *unless* the name is ambiguous without case sensitivity (since Discord role names *are*
case-sensitive).  The member can also type in multiple role names (provided all of them are single-word names) to
subscribe/unsubscribe to all of them at once.  It will also (grudgingly) accept role pings -- although we suggest
that the instructions discourage this practice!  Members can receive a DM with a list of their subscriptions by 
clicking on a (configurable) reaction under the instruction message.

### Configuration

These commands require `Manage Roles` privileges except where otherwise specified.

##### `activate_no_command_subscription [subscription channel] [instruction message text] [wait time] [list emoji]`
Activates no-command role subscription.  First, the bot sends a message to the specified channel with the
given text (usually instructions on how to use the channel).  The bot will then monitor the channel for member 
messages.  When a message is received, the bot handles it and replies affirmatively or negatively, then removes
both messages after the specified wait time.  It also adds the list emoji as a reaction that members can press
to get a list of their subscriptions.

This command requires `Administrator` privileges.

##### `change_no_command_subscription_instructions [new instructions]`
Changes the instruction message to have the specified text.

This also requires `Administrator` privileges.

##### `change_no_command_subscription_wait [new wait time]`
Changes the wait time before messages are deleted.

This also requires `Administrator` privileges.

##### `change_show_subscription_emoji [new show subscription emoji]`
Changes the emoji used for the "show subscription button" reaction.  It will add this to the instruction
message if it hasn't already added it.

##### `disable_no_command_subscription`
Disable no-command subscription for this guild.  Note that this does *not* remove database entries for this guild's
registered roles; that means that if you disable it and re-enable it later, all of the same roles will be 
registered for no-command subscription.

##### `register_roles_csv` (with a CSV file attachment)
Register all the roles specified in the file attachment for no-command subscription.  The CSV file must be a single
column with header `role_name`, and all entries must be simply the role names, *case-sensitive*.  All roles
will be registered for no-command subscription (unless they were already registered, in which case they remain
registered).  Note that you cannot specify which channels any of these roles are associated with; for that
you must register the roles manually.

##### `register_role [role] [optional channel 1] ... [optional channel N]`
Register the specified role for no-command subscription.  You can also specify any channels which this role
grants access to.

##### `deregister_role [role]`
De-register the specified role for no-command subscription; members will no longer be able to use this feature
to subscribe to this role.

##### `deregister_all_roles`
De-register all roles for no-command subscription.

##### `show_no_command_settings`
Print a summary of the no-command subscription settings.

Role Set Operations
-------------------

This allows computation of more complex operations on roles; for example, finding members that are in the 
intersection of two roles, union of two roles, complement of a role, etc.  Expressions can handle unions with
`or`, intersections with `and`, negations with `not`, and parentheses for grouping.  These commands require
`Manage Roles` permissions.

##### `.members [role expression]`
Evaluate the role expression.  Role names that contain non-alphanumeric characters must be enclosed in single quotes.
Use the role names, not role mentions.  Normally the role expression should be put in double-quotes; however, 
in a lot of situations you can simply type the expression after the command and it will work.  The bot will return
the list of members in chunks of 2000 characters; after every message, if there's more to come, it will prompt
you for whether you wish to continue.

##### `.members_mention [role expression]`
Similar to `.members` but lists users by mention.  This makes it easier to operate on their roles, for example.

##### `.members_joined_between_dates [role expression] [start datetime (YYYY-MM-DDTHH24-MM-SS)] [end datetime]`
Evaluate the role expression, additionally filtering to only include members who joined between
the specified datetimes.  Role names that contain non-alphanumeric characters must be enclosed in single quotes.
Use the role names, not role mentions.  Unlike `.members`, the role expression *must* be in double-quotes if 
it's more than one word.  Both the start and end datetimes are formatted in the same way.

##### `.members_joined_between_dates_mention [role expression] [start datetime (YYYY-MM-DDTHH24-MM-SS)] [end datetime]`
Similar to `.members_joined_between_dates` but lists users by mention.

Purge channels and categories
-----------------------------

This allows users with `Manage Messages` permissions to purge channels and entire categories.  The bot must also
have `Manage Messages` permissions on the channels it's trying to purge.

##### `.purgechannel [optional number of messages to purge]`
Basically a clone of DynoBot's `?purge` command, but callable by non-administrators.  This also unpins messages 
before deleting them, although because ghost pins are not viewable whether this actually *happens* is untested.

##### `.purgecategory [category]`
Purges the entire category.  This also unpins messages, though again this is unverified.

Remind users to subscribe to suggested roles
--------------------------------------------

A guild may remind verified members to subscribe to some suggested roles.  The calling user must have `Manage Roles`
permissions.

##### `.show_role_reminder_config` (or `.show_role_reminder_settings`)
Display the guild's role reminder settings.

##### `.activate_role_reminders [reminder channel] [reminder message] [wait time] [reminded role]`
Activates role reminder functionality for this guild.  Users that joined greater than the specified number
of hours ago will be reminded with the specified message (this should be a string with a single "{}" where 
user mentions will be inserted).  After the reminder, they will be assigned the specified `remindedrole` to 
denote them as having been reminded.

##### `.add_verified_role [verified role]`
This denotes the specified role as one belonging to only verified members.

##### `.add_suggested_role [suggested role]`
This denotes the specified role as one of the guild's suggested roles (i.e. the guild is not useful without
one of these roles).

##### `.deactivate_role_reminders`
Remove configuration from the database for this guild and deactivate role reminder functionality.

##### `.remove_verified_role [role]`
Remove this from consideration as a "verified member" role.

##### `.clear_verified_roles`
Clear *all* "verified member" roles.

##### `.remove_suggested_role [role]`
Remove this from the list of the guild's suggested roles.

##### `.clear_suggested_roles`
Clear the guild's entire list of suggested roles.

##### `.rolereminder`
Ping users to remind them of the roles, and mark them as having been reminded.

Raid FYIs
---------

This allows members to announce raids (ideally -- this may easily be abused) with a command in a chat channel.
The FYI will be posted in a specified FYI channel.  All commands except `.fyi` and `.show_fyi_configuration`
require `Administrator` privileges.

##### `.configure_fyi [FYI emoji]` (or `activate_fyi` or `enable_fyi`)
Configures the raid FYI functionality for this guild.  All this does is specify what emoji will be added to the
`.fyi` command message to signify that the message has been "announced" in the FYI channel.

##### `.disable_fyi` (or `deactivate_fyi`)
Disables FYI functionality for this guild by removing the configuration information from the database.  Note
that this does not remove the channel mappings, so if you disable and reenable the functionality, all the same
mappings will still be in place.

##### `.map_chat_to_fyi [chat channel] [FYI channel]` (or `mapchattofyi`)
Configures FYI functionality for the specified chat channel; FYIs will be posted to the specified FYI channel.

##### `.deregister_fyi_mapping [chat channel]`
De-registers the FYI mapping for the specified chat channel; FYIs posted to this channel will be ignored.

##### `.deregister_all_fyi_mappings`
De-registers all FYI mappings for this guild.

##### `.show_fyi_configuration`
Show all FYI functionality configuration for this guild.  This does not require `Administrator` privileges, only 
`Manage Nicknames`.

##### `.fyi [fyi text]`
This command is the actual FYI command.  Everything after `.fyi` will be posted to the corresponding FYI channel.
Any user may use this command.
