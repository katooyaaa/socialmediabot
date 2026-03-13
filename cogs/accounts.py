import discord
from discord import app_commands
from discord.ext import commands


class AccountsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="createaccount", description="Erstellt einen neuen Social-Account")
    @app_commands.describe(
        name="Name des Accounts",
        profilbild="Profilbild des Accounts"
    )
    async def createaccount(
        self,
        interaction: discord.Interaction,
        name: str,
        profilbild: discord.Attachment
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "Dieser Command funktioniert nur auf einem Server.",
                ephemeral=True
            )
            return

        existing = await self.bot.db.get_account_by_name(interaction.guild.id, name)
        if existing:
            await interaction.response.send_message(
                f"Der Account `{name}` existiert bereits.",
                ephemeral=True
            )
            return

        if not profilbild.content_type or not profilbild.content_type.startswith("image/"):
            await interaction.response.send_message(
                "Die Datei muss ein Bild sein.",
                ephemeral=True
            )
            return

        account = await self.bot.db.create_account(
            guild_id=interaction.guild.id,
            owner_id=interaction.user.id,
            name=name,
            avatar_url=profilbild.url
        )

        embed = discord.Embed(
            title="Account erstellt",
            description=f"Account **{account['name']}** wurde erfolgreich erstellt.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=account["avatar_url"])
        embed.add_field(name="Inhaber", value=interaction.user.mention, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="selectaccount", description="Wählt einen Account für deine Posts aus")
    @app_commands.describe(name="Name des Accounts")
    async def selectaccount(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "Dieser Command funktioniert nur auf einem Server.",
                ephemeral=True
            )
            return

        account = await self.bot.db.get_account_by_name(interaction.guild.id, name)
        if not account:
            await interaction.response.send_message(
                f"Kein Account mit dem Namen `{name}` gefunden.",
                ephemeral=True
            )
            return

        if account["owner_id"] != interaction.user.id:
            await interaction.response.send_message(
                "Du kannst nur deine eigenen Accounts auswählen.",
                ephemeral=True
            )
            return

        await self.bot.db.select_account(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            account_id=account["id"]
        )

        await interaction.response.send_message(
            f"Du hast jetzt **{account['name']}** ausgewählt.",
            ephemeral=True
        )

    @app_commands.command(name="deleteaccount", description="Löscht einen deiner Accounts")
    @app_commands.describe(name="Name des Accounts")
    async def deleteaccount(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "Dieser Command funktioniert nur auf einem Server.",
                ephemeral=True
            )
            return

        account = await self.bot.db.delete_account(
            guild_id=interaction.guild.id,
            owner_id=interaction.user.id,
            name=name
        )

        if not account:
            await interaction.response.send_message(
                f"Kein eigener Account mit dem Namen `{name}` gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Account gelöscht",
            description=f"Der Account **{account['name']}** wurde gelöscht.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="accounts", description="Zeigt alle Accounts mit Inhaber und gesamten Likes")
    async def accounts(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "Dieser Command funktioniert nur auf einem Server.",
                ephemeral=True
            )
            return

        accounts = await self.bot.db.get_all_accounts_with_likes(interaction.guild.id)

        embed = discord.Embed(
            title="Alle Accounts",
            color=discord.Color.blurple()
        )

        if not accounts:
            embed.description = "Es existieren noch keine Accounts."
            await interaction.response.send_message(embed=embed)
            return

        for account in accounts:
            owner = interaction.guild.get_member(account["owner_id"])
            owner_text = owner.mention if owner else f"`{account['owner_id']}`"

            embed.add_field(
                name=account["name"],
                value=(
                    f"**Inhaber:** {owner_text}\n"
                    f"**Gesamte Likes:** {account['likes']}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="myaccounts", description="Zeigt nur deine Accounts mit gesamten Likes")
    async def myaccounts(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "Dieser Command funktioniert nur auf einem Server.",
                ephemeral=True
            )
            return

        accounts = await self.bot.db.get_accounts_by_owner_with_likes(
            interaction.guild.id,
            interaction.user.id
        )

        embed = discord.Embed(
            title=f"Accounts von {interaction.user.display_name}",
            color=discord.Color.gold()
        )

        if not accounts:
            embed.description = "Du hast noch keine Accounts erstellt."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        for account in accounts:
            embed.add_field(
                name=account["name"],
                value=f"**Gesamte Likes:** {account['likes']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AccountsCog(bot))