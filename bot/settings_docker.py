# Make sure you mount your Discord token JSON file at /config in the Docker container.
discord_token_file = "/config/token.json"

# Make sure you mount the directory containing the SQLite database at /db.
sqlite_db = "/db/guild_info.db"
# Is this being used in production?  If it's in Docker, we assume yes.
production = True
