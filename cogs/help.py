import discord
from discord import app_commands
from discord.ext import commands


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Zeigt alle Befehle und ihre Erklärung an")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Befehle",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="/createaccount <name> <profilbild>",
            value="Erstellt einen neuen Account mit Namen und Profilbild.",
            inline=False
        )

        embed.add_field(
            name="/selectaccount <name>",
            value="Wählt einen deiner Accounts aus. Dieser Account wird für neue Posts verwendet.",
            inline=False
        )

        embed.add_field(
            name="/createpost <titel> <body> [bild]",
            value=(
                "Erstellt einen Post mit deinem ausgewählten Account.\n"
            ),
            inline=False
        )

        embed.add_field(
            name="/accounts",
            value="Zeigt alle Accounts auf dem Server inklusive Inhaber und gesamten Likes.",
            inline=False
        )

        embed.add_field(
            name="/myaccounts",
            value="Zeigt nur deine eigenen Accounts inklusive gesamter Likes.",
            inline=False
        )

        embed.add_field(
            name="/deleteaccount <name>",
            value="Löscht einen deiner Accounts samt aller Posts und Likes.",
            inline=False
        )

        embed.add_field(
            name="/help",
            value="Zeigt diese Befehlsübersicht.",
            inline=False
        )

        embed.set_footer(text="Social Media Bot Hilfe")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))