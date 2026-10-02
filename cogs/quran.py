import datetime
from typing import List

import discord
from discord import option
from discord.utils import basic_autocomplete
import pytz
from apscheduler.triggers.cron import CronTrigger

from database import (
    get_quran_ayah,
    get_quran_surah_verse_count,
    get_random_quran_ayah,
    search_quran_by_text,
    get_quran_surah,
    get_daily_quran_ayah_for_date,
    get_random_quran_surah,
    set_quran_daily_verse_settings,
    delete_quran_daily_verse_settings,
    get_all_quran_daily_verse_settings,
)
from quran_utils import (
    make_quran_embed,
    QuranSurahView,
    QuranSearchPaginator,
    get_timezone_suggestions,
)

JOB_PREFIX = "quran_daily_"


class QuranCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.schedule_all_jobs()
        if not self.bot.scheduler.running:
            self.bot.scheduler.start()
            print("Scheduler démarré.")

    def schedule_all_jobs(self):
        for job in self.bot.scheduler.get_jobs():
            if job.id and job.id.startswith(JOB_PREFIX):
                job.remove()

        settings = get_all_quran_daily_verse_settings()
        for guild_id, channel_id, hour, minute, tz_name in settings:
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC

            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            self.bot.scheduler.add_job(
                self.send_daily_quran_verses,
                trigger,
                id=f"{JOB_PREFIX}{guild_id}",
                replace_existing=True,
            )

    async def send_daily_quran_verses(self):
        settings = get_all_quran_daily_verse_settings()
        if not settings:
            return

        for guild_id, channel_id, hour, minute, tz_name in settings:
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC

            now_local = datetime.datetime.now(tz)
            today_str = now_local.date().isoformat()

            data = get_daily_quran_ayah_for_date(today_str)
            if not data:
                continue

            ref = f"Sourate {data['sura']}, verset {data['aya']}"
            description = (
                f"**Arabe :**\n{data['arabe'].strip()}\n\n"
                f"**Français (Hamidullah) :**\n{data['francais'].strip()}"
            )

            embed = make_quran_embed(title=f"Aya du jour — {ref}", description=description)

            channel = self.bot.get_channel(channel_id)
            if channel is None:
                continue
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Erreur d'envoi aya du jour pour guild {guild_id}: {e}")

    @discord.slash_command(
        name="aya",
        description="Affiche une aya du Coran (arabe + français Hamidullah)."
    )
    @option("sourate", description="Numéro de la sourate (1–114).", required=True)
    @option("verset", description="Numéro de l'aya dans la sourate.", required=True)
    async def aya(self, ctx: discord.ApplicationContext, sourate: int, verset: int):
        await ctx.defer()

        if sourate < 1 or sourate > 114:
            embed = discord.Embed(
                title="Erreur",
                description="La sourate doit être comprise entre 1 et 114.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        max_verses = get_quran_surah_verse_count(sourate)
        if max_verses == 0:
            embed = discord.Embed(
                title="Erreur",
                description=f"Aucune donnée trouvée pour la sourate {sourate}.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        if verset < 1 or verset > max_verses:
            embed = discord.Embed(
                title="Erreur",
                description=f"La sourate {sourate} contient {max_verses} versets. "
                            f"Le verset {verset} est invalide.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        data = get_quran_ayah(sourate, verset)
        if not data:
            embed = discord.Embed(
                title="Erreur",
                description=f"Impossible de trouver sourate {sourate}, verset {verset}.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        arabe = data["arabe"].strip()
        francais = data["francais"].strip()
        ref = f"Sourate {sourate}, verset {verset}"
        description = f"**Arabe :**\n{arabe}\n\n**Français (Hamidullah) :**\n{francais}"

        embed = make_quran_embed(title=ref, description=description)
        await ctx.respond(embed=embed)

    @discord.slash_command(
        name="randomaya",
        description="Affiche une aya aléatoire du Coran (arabe + français)."
    )
    async def randomaya(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        data = get_random_quran_ayah()
        if not data:
            embed = discord.Embed(
                title="Erreur",
                description="Impossible de récupérer une aya aléatoire du Coran.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        ref = f"Sourate {data['sura']}, verset {data['aya']}"
        description = (
            f"**Arabe :**\n{data['arabe'].strip()}\n\n"
            f"**Français (Hamidullah) :**\n{data['francais'].strip()}"
        )

        embed = make_quran_embed(title=f"Aya aléatoire — {ref}", description=description)
        await ctx.respond(embed=embed)

    @discord.slash_command(
        name="dailyaya",
        description="Affiche l'aya du jour (Coran)."
    )
    async def dailyaya(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        tz_name = "UTC"
        if ctx.guild:
            settings = get_all_quran_daily_verse_settings()
            for guild_id, channel_id, hour, minute, tz in settings:
                if guild_id == ctx.guild.id:
                    tz_name = tz
                    break

        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC

        now_local = datetime.datetime.now(tz)
        today_str = now_local.date().isoformat()

        data = get_daily_quran_ayah_for_date(today_str)
        if not data:
            embed = discord.Embed(
                title="Erreur",
                description="Impossible de récupérer l'aya du jour du Coran.",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return

        ref = f"Sourate {data['sura']}, verset {data['aya']}"
        description = (
            f"**Arabe :**\n{data['arabe'].strip()}\n\n"
            f"**Français (Hamidullah) :**\n{data['francais'].strip()}"
        )

        embed = make_quran_embed(title=f"Aya du jour — {ref}", description=description)
        await ctx.respond(embed=embed)

    @discord.slash_command(
        name="setdailyaya",
        default_member_permissions=discord.Permissions(manage_guild=True),
        contexts={discord.InteractionContextType.guild},
        description="Configure l'envoi automatique de l'aya du jour (Coran) dans ce serveur."
    )
    @option("heure", description="Heure (0-23) dans le fuseau choisi, ex: 8", required=True)
    @option("minute", description="Minute (0-59), ex: 0", required=True)
    @option(
        "timezone",
        description="Fuseau horaire ex: Europe/Paris, America/Martinique",
        required=True,
        autocomplete=basic_autocomplete(get_timezone_suggestions)
    )
    async def setdailyaya(self, ctx: discord.ApplicationContext, heure: int, minute: int, timezone: str):
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.respond("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        try:
            pytz.timezone(timezone)
        except Exception:
            await ctx.respond(f"Fuseau horaire invalide : `{timezone}`", ephemeral=True)
            return

        if not (0 <= heure <= 23 and 0 <= minute <= 59):
            await ctx.respond("Heure/minute invalides (0-23 pour heure, 0-59 pour minute).", ephemeral=True)
            return

        guild_id = ctx.guild.id
        channel_id = ctx.channel.id

        set_quran_daily_verse_settings(guild_id, channel_id, heure, minute, timezone)
        self.schedule_all_jobs()

        await ctx.respond(
            f"Aya du jour (Coran) configuré pour ce salon à {heure:02d}:{minute:02d} ({timezone}).",
            ephemeral=True
        )

    @discord.slash_command(
        name="disabledailyaya",
        default_member_permissions=discord.Permissions(manage_guild=True),
        contexts={discord.InteractionContextType.guild},
        description="Désactive l'envoi automatique de l'aya du jour dans ce serveur."
    )
    async def disabledailyaya(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.respond("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        guild_id = ctx.guild.id
        delete_quran_daily_verse_settings(guild_id)
        self.schedule_all_jobs()

        await ctx.respond(
            "L'envoi automatique de l'aya du jour a été désactivé pour ce serveur.",
            ephemeral=True
        )

    @discord.slash_command(
        name="search",
        description="Cherche un texte dans le Coran (traduction Hamidullah) et affiche les références."
    )
    @option("texte", description="Une partie du verset, ex: miséricordieux, guide-nous, etc.", required=True)
    @option("hardlimit", description="Nombre max de résultats à charger (1-501, défaut 100)", required=False)
    async def search(self, ctx: discord.ApplicationContext, texte: str, hardlimit: int | None = None):
        await ctx.defer()

        texte = texte.strip()
        if not texte:
            embed = discord.Embed(
                title="Erreur",
                description="Merci de fournir un texte à rechercher.",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return

        hard_limit = 100 if hardlimit is None else max(1, min(hardlimit, 501))

        results, total = search_quran_by_text(texte, hard_limit=hard_limit)

        if not results:
            embed = discord.Embed(
                title="Aucun résultat",
                description=f"Aucun verset trouvé contenant \"{texte}\".",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return

        lines: List[str] = []
        for r in results:
            ref = f"{r['sura']}:{r['aya']}"
            snippet = r["francais"].strip()
            lines.append(f"**{ref}**\n{snippet}\n")

        pages: List[str] = []
        current_lines: List[str] = []
        count_in_page = 0
        max_per_page = 5

        for line in lines:
            block = line + "\n"
            if count_in_page >= max_per_page:
                pages.append("".join(current_lines).rstrip())
                current_lines = [block]
                count_in_page = 1
            else:
                current_lines.append(block)
                count_in_page += 1

        if current_lines:
            pages.append("".join(current_lines).rstrip())

        title = f"Résultats pour \"{texte}\""

        embed = make_quran_embed(
            title=title + (f" (page 1/{len(pages)})" if len(pages) > 1 else ""),
            description=pages[0]
        )

        if total > len(results):
            embed.set_footer(text=f"{len(results)} premiers résultats sur {total} • Coran (Hamidullah)")
        else:
            embed.set_footer(text=f"{total} résultat(s) • Coran (Hamidullah)")

        if len(pages) > 1:
            view = QuranSearchPaginator(pages, title)
            view.message = await ctx.respond(embed=embed, view=view)
        else:
            await ctx.respond(embed=embed)

    @discord.slash_command(
        name="sourate",
        description="Affiche une sourate entière (arabe + français)."
    )
    @option("sourate", description="Numéro de la sourate (1–114).", required=True)
    async def sourate(self, ctx: discord.ApplicationContext, sourate: int):
        await ctx.defer()

        if sourate < 1 or sourate > 114:
            embed = discord.Embed(
                title="Erreur",
                description="La sourate doit être comprise entre 1 et 114.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        verses = get_quran_surah(sourate)
        if not verses:
            embed = discord.Embed(
                title="Erreur",
                description=f"Aucune donnée trouvée pour la sourate {sourate}.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        view = QuranSurahView(sourate=sourate, verses=verses, per_page=5)
        embed = view.make_embed()
        view.message = await ctx.respond(embed=embed, view=view)

    @discord.slash_command(
        name="randomsourate",
        description="Affiche une sourate aléatoire (arabe + français)."
    )
    async def randomsourate(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        sura = get_random_quran_surah()
        if sura is None:
            embed = discord.Embed(
                title="Erreur",
                description="Impossible de sélectionner une sourate aléatoire.",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return

        verses = get_quran_surah(sura)
        if not verses:
            embed = discord.Embed(
                title="Erreur",
                description=f"Aucune donnée trouvée pour la sourate {sura}.",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return

        view = QuranSurahView(sourate=sura, verses=verses, per_page=5)
        embed = view.make_embed()
        view.message = await ctx.respond(embed=embed, view=view)


def setup(bot: discord.Bot):
    bot.add_cog(QuranCog(bot))
