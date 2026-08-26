import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from src.database import connection as database_connection
from src.database.user_repository import UserRepository
from src.database.voice_repository import VoiceRepository
from src.services.experience_service import ExperienceService


class TemporaryDatabaseTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temporary_directory.name) / "test.db")
        self.original_database_path = database_connection.DATABASE_PATH
        database_connection.DATABASE_PATH = self.database_path

    def tearDown(self) -> None:
        database_connection.DATABASE_PATH = self.original_database_path
        self.temporary_directory.cleanup()


class ExperienceServiceTests(unittest.TestCase):

    def setUp(self) -> None:
        self.service = ExperienceService()

    def test_level_is_derived_from_cumulative_xp_boundaries(self) -> None:
        expected_levels = {
            0: 0,
            99: 0,
            100: 1,
            399: 1,
            400: 2,
            899: 2,
            900: 3,
        }

        for xp, expected_level in expected_levels.items():
            with self.subTest(xp=xp):
                self.assertEqual(self.service.calculate_level(xp), expected_level)

    def test_large_grant_crosses_multiple_levels_once(self) -> None:
        result = self.service.compute_grant(current_xp=0, amount=1600)

        self.assertEqual(result.previous_level, 0)
        self.assertEqual(result.level, 4)
        self.assertTrue(result.leveled_up)


class RepositoryConsistencyTests(TemporaryDatabaseTestCase):

    def setUp(self) -> None:
        super().setUp()
        database_connection.initialize_tables()
        self.repository = UserRepository()
        self.service = ExperienceService()

    def test_repeated_grants_only_report_real_level_crossings(self) -> None:
        results = [
            self.repository.grant_xp("user", "guild", 25, self.service)
            for _ in range(16)
        ]

        announced_levels = [result.level for result in results if result.leveled_up]
        self.assertEqual(announced_levels, [1, 2])
        self.assertEqual(self.repository.fetch("user", "guild").xp, 400)
        self.assertEqual(self.repository.fetch("user", "guild").level, 2)

    def test_concurrent_grants_do_not_lose_xp_or_repeat_levels(self) -> None:
        def grant(_: int):
            return self.repository.grant_xp("user", "guild", 25, self.service)

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(grant, range(100)))

        record = self.repository.fetch("user", "guild")
        announced_levels = sorted(result.level for result in results if result.leveled_up)

        self.assertEqual(record.xp, 2500)
        self.assertEqual(record.level, 5)
        self.assertEqual(announced_levels, [1, 2, 3, 4, 5])

    def test_startup_repairs_level_that_drifted_from_xp(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO text_experience (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                ("user", "guild", 900, 1)
            )
            connection.commit()

        database_connection.initialize_tables()

        with closing(sqlite3.connect(self.database_path)) as connection:
            stored_level = connection.execute(
                "SELECT level FROM text_experience WHERE user_id = ? AND guild_id = ?",
                ("user", "guild")
            ).fetchone()[0]

        self.assertEqual(stored_level, 3)


class LegacyMigrationTests(TemporaryDatabaseTestCase):

    def test_original_text_and_voice_tables_are_recovered(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript("""
                CREATE TABLE users (
                    user_id TEXT,
                    guild_id TEXT,
                    xp INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    PRIMARY KEY (user_id, guild_id)
                );
                CREATE TABLE voice_sessions (
                    user_id TEXT,
                    guild_id TEXT,
                    total_minutes INTEGER NOT NULL,
                    PRIMARY KEY (user_id, guild_id)
                );
                INSERT INTO users VALUES ('user', 'guild', 900, 1);
                INSERT INTO voice_sessions VALUES ('user', 'guild', 125);
            """)
            connection.commit()

        database_connection.initialize_tables()

        self.assertEqual(UserRepository().fetch("user", "guild").xp, 900)
        self.assertEqual(UserRepository().fetch("user", "guild").level, 3)
        self.assertEqual(VoiceRepository().fetch("user", "guild").total_minutes, 125)

    def test_fresh_voice_schema_has_no_second_xp_or_level(self) -> None:
        database_connection.initialize_tables()

        with closing(sqlite3.connect(self.database_path)) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(voice_experience)")
            }

        self.assertEqual(columns, {"user_id", "guild_id", "total_minutes"})


if __name__ == "__main__":
    unittest.main()
