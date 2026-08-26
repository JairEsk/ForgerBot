import sqlite3
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from src.config import DATABASE_PATH
from src.services.experience_service import calculate_level


logger = logging.getLogger(__name__)
SCHEMA_VERSION = 1


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _get_existing_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,)
    ).fetchone()
    return row is not None


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing_columns = _get_existing_columns(connection, table)
    if column not in existing_columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migrate_legacy_experience_tables(connection: sqlite3.Connection) -> None:
    """Recover data from the original table names used before the split.

    The old tables are intentionally left untouched so this migration is
    recoverable. For duplicate users, the greatest cumulative value wins.
    """
    if _table_exists(connection, "users"):
        for row in connection.execute("SELECT user_id, guild_id, xp FROM users"):
            xp = max(int(row["xp"]), 0)
            connection.execute("""
                INSERT INTO text_experience (user_id, guild_id, xp, level)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    xp = MAX(text_experience.xp, excluded.xp)
            """, (row["user_id"], row["guild_id"], xp, calculate_level(xp)))

    if _table_exists(connection, "voice_sessions"):
        for row in connection.execute(
            "SELECT user_id, guild_id, total_minutes FROM voice_sessions"
        ):
            total_minutes = max(int(row["total_minutes"]), 0)
            connection.execute("""
                INSERT INTO voice_experience (user_id, guild_id, total_minutes)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    total_minutes = MAX(
                        voice_experience.total_minutes,
                        excluded.total_minutes
                    )
            """, (row["user_id"], row["guild_id"], total_minutes))


def _repair_cached_text_levels(connection: sqlite3.Connection) -> int:
    """Make every cached level match its cumulative XP."""
    repaired = 0
    rows = connection.execute("SELECT user_id, guild_id, xp, level FROM text_experience").fetchall()

    for row in rows:
        canonical_level = calculate_level(row["xp"])
        if row["level"] == canonical_level:
            continue

        connection.execute(
            "UPDATE text_experience SET level = ? WHERE user_id = ? AND guild_id = ?",
            (canonical_level, row["user_id"], row["guild_id"])
        )
        repaired += 1

    return repaired


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

        is_new_mode_column = "levelup_mode" not in _get_existing_columns(connection, "guild_settings")

        _add_column_if_missing(
            connection, "guild_settings",
            "levelup_mode", "TEXT NOT NULL DEFAULT 'current'"
        )

        # Existing guilds with a saved channel were implicitly in "custom" mode
        # before levelup_mode existed, so preserve that intent on first migration.
        if is_new_mode_column:
            connection.execute(
                "UPDATE guild_settings SET levelup_mode = 'custom' WHERE levelup_channel_id IS NOT NULL"
            )

        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if schema_version < SCHEMA_VERSION:
            _migrate_legacy_experience_tables(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

        repaired_levels = _repair_cached_text_levels(connection)
        text_records = connection.execute("SELECT COUNT(*) FROM text_experience").fetchone()[0]

    resolved_path = Path(DATABASE_PATH).resolve()
    if os.getenv("DATABASE_PATH") is None and DATABASE_PATH == "data.db":
        logger.warning(
            "DATABASE_PATH is not configured; SQLite data is stored at %s and may be ephemeral in a container.",
            resolved_path
        )
    print(
        f"SQLite database ready at {resolved_path} "
        f"(schema {SCHEMA_VERSION}, {text_records} text records, "
        f"{repaired_levels} repaired levels; text XP + voice time only)."
    )
