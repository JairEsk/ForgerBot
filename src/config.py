import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data.db")
PREFIX = os.getenv("PREFIX", "!")
WEB_PORT = int(os.getenv("WEB_PORT", 6767))
