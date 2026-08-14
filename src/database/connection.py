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


def _get_existing_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing_columns = _get_existing_columns(connection, table)
    if column not in existing_columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def initialize_tables() -> None:
    with get_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS text_experience (
                user_id     TEXT,
                guild_id    TEXT,
                xp          INTEGER NOT NULL DEFAULT 0,
                level       INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS voice_experience (
                user_id         TEXT,
                guild_id        TEXT,
                xp              INTEGER NOT NULL DEFAULT 0,
                level           INTEGER NOT NULL DEFAULT 0,
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

        _add_column_if_missing(
            connection, "guild_settings",
            "levelup_channel_id", "TEXT DEFAULT NULL"
        )
