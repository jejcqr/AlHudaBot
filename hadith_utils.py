import discord

import hadeeth_api


class HadeethView(discord.ui.View):
    """
    View paginée pour un hadith HadeethEnc.
    - pages 1..N : texte (arabe + français) découpé
    - pages N+1..M : explication découpée
    """
    MAX_CHARS = 4096

    def __init__(self, data: dict, title: str, timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.data = data
        self.title = title
        self.message_footer = ""

        self.pages: list[tuple[str, str]] = []  # (label, contenu)
        self.current = 0

        self._build_pages()

    @staticmethod
    def _split_long_text(text: str, limit: int) -> list[str]:
        text = text.strip()
        if not text:
            return []

        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        def flush_current():
            nonlocal current, current_len
            if current:
                chunks.append("".join(current).rstrip())
                current = []
                current_len = 0

        for line in text.splitlines(keepends=True):
            line = line.replace("\r\n", "\n")
            while line:
                remaining = limit - current_len
                if remaining <= 0:
                    flush_current()
                    remaining = limit

                if len(line) <= remaining:
                    current.append(line)
                    current_len += len(line)
                    line = ""
                    break

                window = line[:remaining]

                separators = [" ", "\t", ",", ";", ":", ".", "،", "؛", "؟", "!", "…"]
                cut_at = -1
                for sep in separators:
                    pos = window.rfind(sep)
                    if pos > cut_at:
                        cut_at = pos

                if cut_at <= 0:
                    cut_at = remaining

                part = line[:cut_at]
                line = line[cut_at:].lstrip()

                current.append(part)
                current_len += len(part)

                if current_len >= limit:
                    flush_current()

        flush_current()
        return chunks

    def _build_pages(self):
        arabic = (self.data.get("hadeeth_ar") or "").strip()
        french = (self.data.get("hadeeth") or "").strip()
        explanation = (self.data.get("explanation") or "").strip()
        attribution = self.data.get("attribution") or ""
        grade = self.data.get("grade") or ""

        self.pages = []

        parts = []
        if arabic:
            parts.append("**Arabe :**\n" + arabic)
        if french:
            parts.append("**Français :**\n" + french)

        meta_line = ""
        if attribution or grade:
            meta_line = " • ".join([p for p in [attribution, grade] if p])

        # 1) Essayer en un seul bloc texte (Arabe + Français + meta)
        full_text_parts = parts.copy()
        if meta_line:
            full_text_parts.append(f"*{meta_line}*")
        full_text = "\n\n".join(full_text_parts) if full_text_parts else ""

        if full_text and len(full_text) <= self.MAX_CHARS:
            self.pages.append(("Texte", full_text))
        else:
            # 2) Sinon, séparer Arabe et Français
            if arabic:
                arabic_block = "**Arabe :**\n" + arabic
                arabic_pages = self._split_long_text(arabic_block, self.MAX_CHARS)
                for idx, page in enumerate(arabic_pages, start=1):
                    label = "Arabe" if len(arabic_pages) == 1 else f"Arabe ({idx})"
                    self.pages.append((label, page))

            if french:
                french_block = "**Français :**\n" + french
                french_pages = self._split_long_text(french_block, self.MAX_CHARS)
                for idx, page in enumerate(french_pages, start=1):
                    label = "Français" if len(french_pages) == 1 else f"Français ({idx})"
                    self.pages.append((label, page))

            if meta_line:
                meta = f"*{meta_line}*"
                if self.pages:
                    last_label, last_content = self.pages[-1]
                    combined = last_content + "\n\n" + meta
                    if len(combined) <= self.MAX_CHARS:
                        self.pages[-1] = (last_label, combined)
                    else:
                        self.pages.append(("Informations", meta))

        # 3) Explication toujours après le texte
        if explanation:
            expl_pages = self._split_long_text(explanation, self.MAX_CHARS)
            for idx, page in enumerate(expl_pages, start=1):
                label = "Explication" if len(expl_pages) == 1 else f"Explication ({idx})"
                self.pages.append((label, page))

        if not self.pages:
            self.pages = [("Texte", "Contenu introuvable.")]

    def make_embed(self) -> discord.Embed:
        total = len(self.pages)
        label, content = self.pages[self.current]

        embed = discord.Embed(
            title=f"{self.title} — {label} ({self.current + 1}/{total})",
            description=content,
            color=0x1abc9c,
        )
        if self.message_footer:
            embed.set_footer(text=self.message_footer)
        return embed

    async def update_message(self, interaction: discord.Interaction):
        total = len(self.pages)
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current >= total - 1

        embed = self.make_embed()
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


class HadeethCategoryListView(discord.ui.View):
    def __init__(self, category_id: int, category_label: str, items_pages: list[list[dict]], timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.category_id = category_id
        self.category_label = category_label
        self.items_pages = items_pages
        self.current = 0

    def make_embed(self) -> discord.Embed:
        total_pages = max(1, len(self.items_pages))
        page_items = self.items_pages[self.current]

        lines: list[str] = []
        for it in page_items:
            h_id = it.get("id")
            title = (it.get("title") or "").strip()
            if len(title) > 150:
                title = title[:147] + "..."
            lines.append(f"**ID {h_id}** — {title}")

        desc = "\n".join(lines) if lines else "Aucun hadith dans cette catégorie."

        embed = discord.Embed(
            title=f"Hadiths — {self.category_label} (page {self.current + 1}/{total_pages})",
            description=desc,
            color=0x1abc9c,
        )
        embed.set_footer(text=f"Catégorie HadeethEnc ID {self.category_id} • Utilise /hadith id:XXXX pour le détail.")
        return embed

    async def update_message(self, interaction: discord.Interaction):
        total_pages = max(1, len(self.items_pages))
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
        total_pages = max(1, len(self.items_pages))
        if self.current < total_pages - 1:
            self.current += 1
        await self.update_message(interaction)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


async def hadeeth_category_autocomplete(ctx: discord.AutocompleteContext):
    user_input = (ctx.value or "").lower()
    cats = hadeeth_api.load_categories()

    if user_input:
        cats = [c for c in cats if user_input in str(c.get("title", "")).lower()]

    cats = cats[:25]

    return [
        discord.OptionChoice(
            name=c.get("title", f"Cat {c.get('id')}")[:100],
            value=int(c.get("id"))
        )
        for c in cats
        if c.get("id") is not None
    ]
