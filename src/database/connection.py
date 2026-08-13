import sqlite3
from contextlib import contextmanager
from src.config import DATABASE_PATH


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_tables() -> None:
    with get_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     TEXT,
                guild_id    TEXT,
                xp          INTEGER NOT NULL DEFAULT 0,
                level       INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS voice_sessions (
                user_id         TEXT,
                guild_id        TEXT,
                total_minutes   INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS ignored_channels (
                channel_id  TEXT,
                guild_id    TEXT,
                PRIMARY KEY (channel_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id        TEXT PRIMARY KEY,
                cooldown        INTEGER NOT NULL DEFAULT 60,
                levelup_message TEXT    NOT NULL DEFAULT '🎉 {user} just reached level **{level}**!'
            );
        """)
