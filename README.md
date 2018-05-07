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

### Configuring verification

GVRDGrunt must be configured for the guild before this can happen.  These commands must be run by someone with
`Administrator` privileges on the guild, except for `showsettings`.  Remember that the bot must have appropriate 
permissions on the channels it reads from/writes to!

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
Configures the channel that the guild sends the welcome message in, as well as the message that is sent.  This message
should contain a single `{}` where the new member will be mentioned.  The bot must have read and write
privileges on the welcome channel.

##### `configure_denied_message [denied message template incl "{}" where the member will be mentioned]`
Configures the message that will be sent to the user when their screenshot is rejected.  Like the welcome message,
this message should contain a single `{}` where the new member will be mentioned.

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
added or removed), and assigns the reacting user a specified role.

### Configuration

This requires `Administrator` privileges except where otherwise specified.

##### `activate_role_reaction_subscription [role] [channel] [message ID] [emoji]`
Instructs the bot to watch the specified message (in the specified channel) for the adding/removing of the specified
emoji as a reaction; assign/remove the specified role from the reacting member.

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
