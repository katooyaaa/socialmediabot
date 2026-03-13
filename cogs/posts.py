import discord
from discord import app_commands
from discord.ext import commands


class PostsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="createpost", description="Erstellt einen Post mit deinem ausgewählten Account")
    @app_commands.describe(
        titel="Titel des Posts",
        body="Textinhalt des Posts",
        bild="Optionales Bild für den Post"
    )
    async def post(
        self,
        interaction: discord.Interaction,
        titel: str,
        body: str,
        bild: discord.Attachment | None = None
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "Dieser Command funktioniert nur auf einem Server.",
                ephemeral=True
            )
            return

        account = await self.bot.db.get_selected_account(
            interaction.guild.id,
            interaction.user.id
        )

        if not account:
            await interaction.response.send_message(
                "Du hast noch keinen Account ausgewählt. Nutze zuerst `/selectaccount name`.",
                ephemeral=True
            )
            return

        if bild and (not bild.content_type or not bild.content_type.startswith("image/")):
            await interaction.response.send_message(
                "Die optionale Datei muss ein Bild sein.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            description=f"**{account['name']}**\n\n**{titel}**\n{body}",
            color=discord.Color.from_rgb(245, 245, 245)
        )
        embed.set_thumbnail(url=account["avatar_url"])
        embed.set_footer(text=f"Erstellt von {interaction.user.display_name}")

        file_to_send = None
        image_url_for_db = None

        if bild:
            file_to_send = await bild.to_file()
            embed.set_image(url=f"attachment://{file_to_send.filename}")
            image_url_for_db = bild.url

        if file_to_send:
            await interaction.response.send_message(embed=embed, file=file_to_send)
        else:
            await interaction.response.send_message(embed=embed)

        msg = await interaction.original_response()
        await msg.add_reaction("❤️")

        await self.bot.db.create_post(
            guild_id=interaction.guild.id,
            account_id=account["id"],
            author_user_id=interaction.user.id,
            channel_id=interaction.channel.id,
            message_id=msg.id,
            title=titel,
            image_url=image_url_for_db
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PostsCog(bot))