from src.database.connection import get_connection


class ChannelRepository:

    def is_ignored(self, channel_id: str, guild_id: str) -> bool:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM ignored_channels WHERE channel_id = ? AND guild_id = ?",
                (channel_id, guild_id)
            ).fetchone()

        return row is not None

    def add(self, channel_id: str, guild_id: str) -> None:
        with get_connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO ignored_channels (channel_id, guild_id) VALUES (?, ?)",
                (channel_id, guild_id)
            )

    def remove(self, channel_id: str, guild_id: str) -> None:
        with get_connection() as connection:
            connection.execute(
                "DELETE FROM ignored_channels WHERE channel_id = ? AND guild_id = ?",
                (channel_id, guild_id)
            )

    def fetch_all(self, guild_id: str) -> list[str]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT channel_id FROM ignored_channels WHERE guild_id = ?",
                (guild_id,)
            ).fetchall()

        return [row["channel_id"] for row in rows]
