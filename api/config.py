import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")


class Settings:
    ALGORITHM = "HS256"
    SECRET_KEY: str = os.getenv("SECRET_KEY")

settings = Settings()
