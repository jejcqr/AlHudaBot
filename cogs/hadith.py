import datetime

import discord
from discord import option
from discord.utils import basic_autocomplete
import pytz
from apscheduler.triggers.cron import CronTrigger

import hadeeth_api
from database import (
    set_hadith_daily_settings,
    delete_hadith_daily_settings,
    get_all_hadith_daily_settings,
    set_daily_hadith_for_date,
    get_daily_hadith_for_date,
)
from quran_utils import get_timezone_suggestions
from hadith_utils import (
    HadeethView,
    HadeethCategoryListView,
    hadeeth_category_autocomplete,
)

JOB_PREFIX = "hadith_daily_"


class HadithCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.schedule_all_jobs()
        if not self.bot.scheduler.running:
            self.bot.scheduler.start()
            print("Scheduler démarré.")
        hadeeth_api.load_categories()
        print("Catégories HadeethEnc pré-chargées.")

    def schedule_all_jobs(self):
        for job in self.bot.scheduler.get_jobs():
            if job.id and job.id.startswith(JOB_PREFIX):
                job.remove()

        settings = get_all_hadith_daily_settings()
        for guild_id, channel_id, hour, minute, tz_name in settings:
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC

            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            self.bot.scheduler.add_job(
                self.send_daily_hadith,
                trigger,
                id=f"{JOB_PREFIX}{guild_id}",
                replace_existing=True,
            )

    async def send_daily_hadith(self):
        settings = get_all_hadith_daily_settings()
        if not settings:
            return

        for guild_id, channel_id, hour, minute, tz_name in settings:
            try:
                try:
                    tz = pytz.timezone(tz_name)
                except Exception:
                    tz = pytz.UTC

                now_local = datetime.datetime.now(tz)
                today_str = now_local.date().isoformat()

                hid_saved, label_saved = get_daily_hadith_for_date(today_str)
                label = label_saved
                data = None

                if hid_saved is not None:
                    data = hadeeth_api.get_by_id(hid_saved)
                else:
                    data, label = hadeeth_api.get_random_global()
                    if data:
                        try:
                            h_id = int(data.get("id"))
                        except (TypeError, ValueError):
                            h_id = None
                        if h_id is not None:
                            set_daily_hadith_for_date(today_str, h_id, label)

                if not data:
                    print(f"Erreur: aucun hadith pour la date {today_str}")
                    continue

                title = "Hadith du jour"
                if label:
                    title += f" — {label}"

                view = HadeethView(data, title=title)
                h_id = data.get("id")
                view.message_footer = f"Hadith HadeethEnc ID {h_id}" if h_id else "Hadith HadeethEnc"

                embed = view.make_embed()

                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    continue

                await channel.send(embed=embed, view=view)
            except Exception as e:
                print(f"Erreur d'envoi hadith du jour pour guild {guild_id}: {e}")

    @discord.slash_command(
        name="hadithcategories",
        description="Liste ou cherche des catégories HadeethEnc (hadith)."
    )
    @option("query", description="Filtre texte (ex: prière, jeûne, mariage...)", required=False)
    async def hadithcategories(self, ctx: discord.ApplicationContext, query: str | None = None):
        await ctx.defer(ephemeral=True)

        cats = hadeeth_api.load_categories()
        if query:
            q = query.lower()
            cats = [c for c in cats if q in str(c.get("title", "")).lower()]

        if not cats:
            await ctx.respond("Aucune catégorie trouvée.", ephemeral=True)
            return

        cats = cats[:50]

        lines = []
        for c in cats:
            cid = c.get("id")
            title = c.get("title")
            count = c.get("hadeeths_count")
            lines.append(f"`{cid}` — {title} (hadiths: {count})")

        chunks = []
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > 1900:
                chunks.append(current)
                current = ""
            current += line + "\n"
        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title="Catégories HadeethEnc" + (f" (page {i+1})" if len(chunks) > 1 else ""),
                description=chunk,
                color=0x2ecc71,
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(
        name="randomhadith",
        description="Hadith aléatoire HadeethEnc, global ou dans une catégorie."
    )
    @option(
        "categorie",
        int,
        description="(Optionnel) Choisis une catégorie HadeethEnc",
        required=False,
        autocomplete=hadeeth_category_autocomplete,
    )
    async def randomhadith(self, ctx: discord.ApplicationContext, categorie: int | None = None):
        await ctx.defer()

        if categorie is None:
            data, label = hadeeth_api.get_random_global()
            if not data:
                embed = discord.Embed(
                    title="Erreur",
                    description="Impossible de récupérer un hadith aléatoire (HadeethEnc).",
                    color=0xe74c3c,
                )
                await ctx.respond(embed=embed)
                return

            title = "Hadith aléatoire"
            if label:
                title += f" — {label}"

            view = HadeethView(data, title=title)
            h_id = data.get("id")
            view.message_footer = f"Hadith HadeethEnc ID {h_id}" if h_id else "Hadith HadeethEnc"

            embed = view.make_embed()
            await ctx.respond(embed=embed, view=view)
            return

        category_id = categorie
        cats = hadeeth_api.load_categories()
        cat = next((c for c in cats if int(c.get("id")) == category_id), None) if cats else None
        if not cat:
            await ctx.respond(f"Aucune catégorie trouvée pour l'ID {category_id}.", ephemeral=True)
            return

        label = cat.get("title") or f"Catégorie {category_id}"
        random_item = hadeeth_api.get_random_from_category(category_id)
        if not random_item:
            embed = discord.Embed(
                title="Erreur",
                description=f"Impossible de récupérer un hadith pour la catégorie « {label} ». ",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        try:
            hid = int(random_item.get("id"))
        except Exception:
            hid = None

        if hid is None:
            embed = discord.Embed(
                title="Erreur",
                description="L'API a renvoyé un hadith sans ID exploitable.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        data = hadeeth_api.get_by_id(hid)
        if not data:
            embed = discord.Embed(
                title="Erreur",
                description=f"Impossible de récupérer les détails du hadith ID {hid}.",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        title = f"Hadith — {label}"
        view = HadeethView(data, title=title)
        view.message_footer = f"Hadith HadeethEnc ID {hid}"

        embed = view.make_embed()
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(
        name="listhadiths",
        description="Liste les hadiths (titre + ID) d'une catégorie HadeethEnc."
    )
    @option(
        "categorie",
        description="Choisis une catégorie HadeethEnc",
        required=True,
        autocomplete=hadeeth_category_autocomplete,
    )
    async def listhadiths(self, ctx: discord.ApplicationContext, categorie: int):
        await ctx.defer()

        category_id = categorie

        cats = hadeeth_api.load_categories()
        cat = next((c for c in cats if int(c.get("id")) == category_id), None)

        if not cat:
            await ctx.respond(f"Aucune catégorie trouvée pour l'ID `{category_id}`.", ephemeral=True)
            return

        label = cat.get("title", f"Catégorie {category_id}")

        items = hadeeth_api.get_all_in_category(category_id, per_page=20)
        if not items:
            embed = discord.Embed(
                title="Aucun hadith",
                description=f"Aucun hadith trouvé pour la catégorie « {label} ».",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        page_size = 10
        pages: list[list[dict]] = []
        for i in range(0, len(items), page_size):
            pages.append(items[i:i + page_size])

        view = HadeethCategoryListView(category_id=category_id, category_label=label, items_pages=pages)
        embed = view.make_embed()
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(
        name="hadith",
        description="Affiche un hadith (HadeethEnc) par ID (arabe + français + explication)."
    )
    @option("id", description="ID du hadith HadeethEnc (ex: 4247)", required=True)
    async def hadith(self, ctx: discord.ApplicationContext, id: int):
        await ctx.defer()

        data = hadeeth_api.get_by_id(id)
        if not data:
            embed = discord.Embed(
                title="Aucun résultat",
                description=f"Aucun hadith trouvé pour l'ID {id} (HadeethEnc).",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        cats = hadeeth_api.load_categories()
        categories_ids = data.get("categories") or []
        label = None
        if cats and categories_ids:
            try:
                cat_id = int(categories_ids[0])
                cat = next((c for c in cats if int(c.get("id")) == cat_id), None)
                if cat:
                    label = cat.get("title")
            except Exception:
                pass

        title = f"Hadith — {label}" if label else f"Hadith HadeethEnc #{id}"

        view = HadeethView(data, title=title)
        view.message_footer = f"Hadith HadeethEnc ID {id}"

        embed = view.make_embed()
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(
        name="dailyhadith",
        description="Affiche le hadith du jour (HadeethEnc)."
    )
    async def dailyhadith(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        tz_name = "UTC"
        if ctx.guild:
            settings = get_all_hadith_daily_settings()
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

        hid_saved, label_saved = get_daily_hadith_for_date(today_str)
        label = label_saved
        data = None

        if hid_saved is not None:
            data = hadeeth_api.get_by_id(hid_saved)
        else:
            data, label = hadeeth_api.get_random_global()
            if data:
                try:
                    h_id = int(data.get("id"))
                except (TypeError, ValueError):
                    h_id = None
                if h_id is not None:
                    set_daily_hadith_for_date(today_str, h_id, label)

        if not data:
            embed = discord.Embed(
                title="Erreur",
                description="Impossible de récupérer le hadith du jour (HadeethEnc).",
                color=0xe74c3c,
            )
            await ctx.respond(embed=embed)
            return

        title = "Hadith du jour"
        if label:
            title += f" — {label}"

        view = HadeethView(data, title=title)
        h_id = data.get("id")
        view.message_footer = f"Hadith HadeethEnc ID {h_id}" if h_id else "Hadith HadeethEnc"

        embed = view.make_embed()
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(
        name="setdailyhadith",
        description="Configure l'envoi automatique du hadith du jour (HadeethEnc) dans ce serveur."
    )
    @option("heure", description="Heure (0-23) dans le fuseau choisi, ex: 8", required=True)
    @option("minute", description="Minute (0-59), ex: 0", required=True)
    @option(
        "timezone",
        description="Fuseau horaire ex: Europe/Paris, America/Martinique",
        required=True,
        autocomplete=basic_autocomplete(get_timezone_suggestions)
    )
    async def setdailyhadith(self, ctx: discord.ApplicationContext, heure: int, minute: int, timezone: str):
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

        set_hadith_daily_settings(guild_id, channel_id, heure, minute, timezone)
        self.schedule_all_jobs()

        await ctx.respond(
            f"Hadith du jour configuré pour ce salon à {heure:02d}:{minute:02d} ({timezone}).",
            ephemeral=True,
        )

    @discord.slash_command(
        name="disabledailyhadith",
        description="Désactive l'envoi automatique du hadith du jour dans ce serveur."
    )
    async def disabledailyhadith(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.respond("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        guild_id = ctx.guild.id
        delete_hadith_daily_settings(guild_id)
        self.schedule_all_jobs()

        await ctx.respond(
            "L'envoi automatique du hadith du jour a été désactivé pour ce serveur.",
            ephemeral=True
        )


def setup(bot: discord.Bot):
    bot.add_cog(HadithCog(bot))
