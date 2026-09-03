import os

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN n'est pas défini.")

if os.getenv("DB_PASSWORD") is None:
    raise RuntimeError("DB_PASSWORD n'est pas défini.")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "alhudauser"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "alhuda"),
}

HADEETHENC_BASE = "https://hadeethenc.com/api/v1"
HADEETHENC_LANG = "fr"
