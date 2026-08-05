from dotenv import load_dotenv
import os


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
ADMIN_SECRET = os.getenv("ADMIN_SECRET")


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден в файле .env"
    )


if not ADMIN_ID_RAW:
    raise RuntimeError(
        "ADMIN_ID не найден в файле .env"
    )


if not ADMIN_SECRET:
    raise RuntimeError(
        "ADMIN_SECRET не найден в файле .env"
    )


try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError(
        "ADMIN_ID в .env должен быть числом"
    )