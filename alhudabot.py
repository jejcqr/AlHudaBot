import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TOKEN

# =========================
# Config Discord
# =========================

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)
bot.scheduler = AsyncIOScheduler(timezone="UTC")

EXTENSIONS = [
    "cogs.quran",
    "cogs.hadith",
    "cogs.help",
    "cogs.admin",
]

for extension in EXTENSIONS:
    bot.load_extension(extension)


# =========================
# Events Discord
# =========================

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    await bot.sync_commands()
    print("Commandes slash synchronisées.")


# =========================
# Lancement du bot
# =========================

bot.run(TOKEN)
