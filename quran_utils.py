from math import ceil
from typing import List

import discord
import pytz


def make_quran_embed(title: str, description: str, color: int = 0x1abc9c) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Coran — Texte arabe + traduction Hamidullah")
    return embed


async def get_timezone_suggestions(ctx: discord.AutocompleteContext):
    user_input = (ctx.value or "").lower()
    all_timezones = pytz.all_timezones

    if not user_input:
        suggestions = [
            "America/Martinique",
            "Europe/Paris",
            "UTC",
            "America/New_York",
            "America/Toronto",
            "America/Sao_Paulo",
            "Africa/Abidjan",
            "Africa/Dakar",
        ]
    else:
        suggestions = [tz for tz in all_timezones if user_input in tz.lower()]

    return suggestions[:25]


class QuranSurahView(discord.ui.View):
    def __init__(self, sourate: int, verses: list[dict], per_page: int = 5):
        super().__init__(timeout=None)
        self.sourate = sourate
        self.verses = verses
        self.per_page = per_page
        self.current = 0

    def make_embed(self) -> discord.Embed:
        total_pages = max(1, ceil(len(self.verses) / self.per_page))
        start = self.current * self.per_page
        end = start + self.per_page
        page_verses = self.verses[start:end]

        lines = []
        for v in page_verses:
            aya = v["aya"]
            arabe = v["arabe"].strip()
            francais = v["francais"].strip()
            lines.append(f"{aya}. {arabe}\n{francais}\n")

        desc = "\n".join(lines).rstrip()
        title = f"Sourate {self.sourate} (page {self.current + 1}/{total_pages})"
        return make_quran_embed(title=title, description=desc)

    async def update_message(self, interaction: discord.Interaction):
        total_pages = max(1, ceil(len(self.verses) / self.per_page))
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current >= total_pages - 1

        embed = self.make_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Précédent", style=discord.ButtonStyle.primary)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current > 0:
            self.current -= 1
        await self.update_message(interaction)

    @discord.ui.button(label="Suivant", style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        total_pages = max(1, ceil(len(self.verses) / self.per_page))
        if self.current < total_pages - 1:
            self.current += 1
        await self.update_message(interaction)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


class QuranSearchPaginator(discord.ui.View):
    def __init__(self, pages: List[str], title: str, timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.title = title
        self.current = 0

    async def update_message(self, interaction: discord.Interaction):
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current >= len(self.pages) - 1

        embed = make_quran_embed(
            title=self.title + f" (page {self.current + 1}/{len(self.pages)})",
            description=self.pages[self.current]
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Précédent", style=discord.ButtonStyle.primary)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current > 0:
            self.current -= 1
        await self.update_message(interaction)

    @discord.ui.button(label="Suivant", style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current < len(self.pages) - 1:
            self.current += 1
        await self.update_message(interaction)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
