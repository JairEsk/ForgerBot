import sys
from src.bot import ForgerBot
from src.config import DISCORD_TOKEN
from src.database.connection import initialize_tables


def main() -> None:
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN is missing from the .env file.")
        sys.exit(1)

    initialize_tables()

    bot = ForgerBot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
