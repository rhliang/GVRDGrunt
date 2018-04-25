GVRDGrunt
=========

GVRDGrunt is a simple bot that performs boilerplate admin tasks for Vancouver/GVRD moderators.

Installation
------------

* Install Python 3.6 or later
    * On OS X, you may need to do the following https://github.com/Rapptz/discord.py/issues/423#issuecomment-272093801
* Set up a Virtualenv if you're using this in production
* `python -m pip install -r requirements.txt`
* Copy `settings_default.py` to `settings.py` and fill it out
* Initialize the guild information DB using the SQL in `db_initialization.sql`
* `python -m bot`
    * `--debug` for debug-level logging
