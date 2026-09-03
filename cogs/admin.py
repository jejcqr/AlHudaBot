import discord
from discord import option


class AdminCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="reload",
        description="(Owner) Recharge un module du bot sans redémarrer le process."
    )
    @option(
        "extension",
        description="Ex: cogs.quran, cogs.hadith, cogs.help",
        required=True
    )
    async def reload(self, ctx: discord.ApplicationContext, extension: str):
        if not await self.bot.is_owner(ctx.author):
            await ctx.respond("Commande réservée au propriétaire du bot.", ephemeral=True)
            return

        try:
            self.bot.reload_extension(extension)
        except Exception as e:
            await ctx.respond(f"Erreur lors du rechargement de `{extension}` : `{e}`", ephemeral=True)
            return

        await ctx.respond(f"Extension `{extension}` rechargée.", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(AdminCog(bot))
