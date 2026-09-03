import discord


class HelpCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="help",
        description="Affiche la liste des commandes."
    )
    async def help(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=False)

        lines = [
            "**Coran**",
            "• `/aya` — afficher une aya précise",
            "• `/sourate` — afficher une sourate complète",
            "• `/randomaya` — afficher une aya aléatoire",
            "• `/randomsourate` — afficher une sourate aléatoire",
            "• `/search` — rechercher un passage du Coran à partir de mots ou d'une phrase",
            "• `/dailyaya` — afficher l'aya du jour",
            "• `/setdailyaya` — configurer l'envoi automatique de l'aya du jour dans ce salon",
            "• `/disabledailyaya` — désactiver l'envoi automatique de l'aya du jour dans ce salon",

            "",
            "**Hadith**",
            "• `/hadithcategories` — lister/rechercher des catégories de hadiths",
            "• `/randomhadith` — hadith aléatoire",
            "• `/listhadiths` — lister les hadiths (titre + ID) d'une catégorie",
            "• `/hadith` — afficher un hadith précis par ID (texte + explication)",
            "• `/dailyhadith` — afficher le hadith du jour",
            "• `/setdailyhadith` — configurer l'envoi automatique du hadith du jour dans ce salon",
            "• `/disabledailyhadith` — désactiver l'envoi automatique du hadith du jour dans ce salon",
        ]

        embed = discord.Embed(
            title="Commandes",
            description="\n".join(lines),
            color=0x5865F2,
        )
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(HelpCog(bot))
