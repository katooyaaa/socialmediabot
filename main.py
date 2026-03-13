import os
import logging
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

from services.database import Database
import webserver

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

handler = logging.FileHandler(
    filename="discord.log",
    encoding="utf-8",
    mode="w"
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True


class SocialBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="s!",
            intents=intents,
            help_command=None
        )
        self.db = Database(DATABASE_URL)
        self.synced_once = False

    async def setup_hook(self):
        try:
            print("Verbinde mit der Datenbank...")
            await self.db.connect()
            await self.db.create_tables()
            print("Datenbank-Tabellen gecheckt!")

            print("Lade Cogs...")
            await self.load_extension("cogs.accounts")
            await self.load_extension("cogs.posts")
            await self.load_extension("cogs.help")
            print("Cogs geladen!")

            for cmd in self.tree.get_commands():
                print(f"LOKALER COMMAND: /{cmd.name}")
                print("PARAMETER:", [p.name for p in cmd.parameters])

        except Exception:
            import traceback
            print("FEHLER in setup_hook():")
            traceback.print_exc()
            raise

bot = SocialBot()

@bot.event
async def on_ready():
    print(f"Eingeloggt als {bot.user} (ID: {bot.user.id})")

    if not bot.synced_once:
        synced_total = 0

        for guild in bot.guilds:
            try:
                synced = await bot.tree.sync(guild=guild)
                print(f"{len(synced)} Commands für Guild '{guild.name}' ({guild.id}) synchronisiert.")
                synced_total += len(synced)
            except Exception as e:
                print(f"Fehler beim Sync für Guild '{guild.name}' ({guild.id}): {e}")

        print(f"Guild-Sync abgeschlossen. Insgesamt synchronisierte Commands: {synced_total}")
        bot.synced_once = True


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    if str(payload.emoji) != "❤️":
        return

    await bot.db.like_post(
        message_id=payload.message_id,
        user_id=payload.user_id
    )


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if str(payload.emoji) != "❤️":
        return

    await bot.db.unlike_post(
        message_id=payload.message_id,
        user_id=payload.user_id
    )


async def main():
    print("Starte den Bot-Prozess...")

    if not TOKEN:
        print("FEHLER: Kein DISCORD_TOKEN gefunden!")
        return

    if not DATABASE_URL:
        print("FEHLER: Kein DATABASE_URL gefunden!")
        return

    print("Starte Webserver...")
    webserver.keep_alive()

    try:
        print("Versuche Login bei Discord...")
        await bot.start(TOKEN, reconnect=True)
    except KeyboardInterrupt:
        print("Bot wird beendet...")
    except Exception as e:
        print(f"Fehler beim Starten des Bots: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())